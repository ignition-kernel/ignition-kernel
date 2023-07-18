






import sys, importlib
import os
from datetime import datetime
import time

from java.lang.System import currentTimeMillis



def module_origin(class_name):
	"""Get the module/filename of where the instantiation begain.  Requires walking backwards, since we don't care about the parent class module, of course."""
	frame = sys._getframe()
	frame = frame.f_back
	while frame.f_code.co_name == '__new__' and frame.f_locals[frame.f_code.co_varnames[1]] == class_name:
		frame = frame.f_back
	return frame.f_code.co_filename[8:-1]



def resolve_import_path(path):
	
	# do the obvious, easy thing first
	# helpful to avoid manually deriving
	try:
		thing = importlib.import_module(path)
		return thing
	except ImportError:
		pass
	
	# if we need to search for the thing, then this will do it
	
	# --------------
	# WARNING: NOTE:
	#    Manually getting things may cause re-execution of modules.
	#    Running the `class` and `def` statements will yield _NEW_
	#    objects that will NOT be part of the same inheritance tree!

	modules = path.split('.')
	# first entry in path is junk for interactive console
	
	if not modules[0]:
		frame = sys._getframe()
		while frame.f_back:
			frame = frame.f_back
		
		thing = frame.f_globals.get(modules[1])
		if thing is None:
			thing = frame.f_locals.get(modules[1])
		modules = modules[2:]
	else:
		thing = globals().get(modules[0])
	
	try:
		# NOTE: this seems to potentially re-execute loading modules!
		#       make sure your classes can handle if there's more than one declaration
		for ix, part in enumerate(modules[1:]):
			thing = getattr(thing, part)
		
	except AttributeError:
		# the class was likely generated during runtime, and any sane usage would mean during
		# *this* runtime, so we'll walk down the execution stack checking if we created
		# the thing in the expected place at some point
		# (thus we could, for example, generate a test class in a function and if we search
		#  in the same execution context, we can reference it like it always existed there)
		# in the end this is just a handy heuristic - it merely has to be useful
		origin = '.'.join(modules[:-1])
		frame = sys._getframe()
		while frame:
			if origin.startswith(frame.f_code.co_filename[8:-1]) and modules[-1] in frame.f_locals:
				thing = frame.f_locals[modules[-1]]
				break
			frame = frame.f_back
	
	assert thing, 'Class path %r did not resolve to something reachable from globals()' % (path,)
	
	return thing




class MetaBasePersistenceMixin(type):

	def __new__(metacls, class_name, class_bases, class_configuration):
		class_configuration['__module__'] = module_origin(class_name)
		
		class_configuration['__seed__'] = None
		return super(MetaBasePersistenceMixin, metacls).__new__(metacls, class_name, class_bases, class_configuration)

	
	@property
	def __classpath__(cls):
		return cls.__module__ + '.' + cls.__name__


	def __init__(new_class, class_name, class_bases, class_configuration):
		super(MetaBasePersistenceMixin, new_class).__init__(class_name, class_bases, class_configuration)
		# ensure lookups are sync'd
		new_class.init_cache()		

	def init_cache(cls, seed=None):
		# ensure the lookups are seeded in lockstep
		seed = seed or currentTimeMillis()
		assert isinstance(seed, (int, long))
		cls.__seed__ = seed
		

	def dump(cls, folder_path, seed=None):
		try:
			# sanity check
			cls._verify_bincoder_targets(folder_path, seed)     
		except AssertionError:
			cls._init_bincoders(folder_path, seed)

	def load(cls, folder_path, seed=None):
		assert seed, "Loading overwrites and replaces lookups, so a direct reference seed is needed."
		cls._init_bincoders(folder_path, seed)
		cls.init_cache(seed)
	
	def _init_bincoders(cls, folder_path, seed=None):
		pass
	
	def _verify_bincoder_targets(cls, folder_path, seed=None):
		pass

	
	@staticmethod
	def _seed_to_str(seed):
		"""Convert a millis to a string that can be used for a filepath."""
		assert isinstance(seed, long), 'A seed (in UTC epoch millis) is needed to target the persisted location. It will be translated to a (reasonable) timestamp. (Got %r)' % (seed,)
		timestamp = datetime.utcfromtimestamp(seed//1000).replace(microsecond=seed%1000*1000)
		# 1678507702480 becomes 2023-03-11_04-08-22.480000Z
		seed_str = timestamp.isoformat('_').replace(':', '-') + 'Z'
		# note that the format is used for consistency more than beauty, hence the microseconds
		return seed_str
	
	@staticmethod
	def _str_to_seed(seed_str):
		assert seed_str.endswith('000Z'), 'Seed is in UTC epoch millis, so it is expected to end in 000Z (since microseconds will be zero)'
		timestamp = datetime.strptime(seed_str, '%Y-%m-%d_%H-%M-%S.%fZ')
		seed = int(time.mktime(timestamp.utctimetuple()) * 1000 + timestamp.microsecond / 1000)
		return seed

	def _target_folder(cls, folder_path, seed, prep_directory=True):
		target_folder = os.path.join(folder_path, cls._seed_to_str(seed), cls.__name__)
		if prep_directory and not os.path.exists(target_folder):
			os.makedirs(target_folder)	
		return target_folder


