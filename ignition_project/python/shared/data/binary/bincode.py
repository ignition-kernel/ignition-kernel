"""
	Binary encode stuff
	
	Unlike Pickle, this can be run on an append-only stream,
	allowing for incremental updates and additions.
	
	The format is simple: an unsigned int to denote the type, 
	and then the type's handler encodes or decodes the rest.
	Delegating responsibility to each type simplifies the interface
	and lets more specialized handlers work.
"""

# isolation
__all__ = [
	'Bincode',
]



# Combine for better
import __builtin__

from shared.data.binary.handlers.numeric import NumericHandlers
from shared.data.binary.handlers.string import StringHandlers
from shared.data.binary.handlers.collection import CollectionHandlers
from shared.data.binary.handlers.esoteric import EsotericHandlers

from shared.data.binary.handlers.helper import GenericHandler



class BuiltinTypeHandlers(
		CollectionHandlers,
		StringHandlers,
		EsotericHandlers,
		NumericHandlers,
	): pass



class ConsolidatedHandler(BuiltinTypeHandlers, GenericHandler):

	BUILTIN_TYPE_LIST = (
		# the _starting point_
		__builtin__.None,
		
		# boolean
		__builtin__.bool,
		
		# numbers
		__builtin__.int,
		__builtin__.long,
		__builtin__.float,
		__builtin__.complex,
		
		# strings
		# __builtin__.basestring, # not implementable
		__builtin__.str,
		__builtin__.unicode,
		__builtin__.bytearray,
		
		# basic ordered iterables
		__builtin__.tuple,
		__builtin__.list,
		
		# basic unordered iterables
		__builtin__.set,
		__builtin__.frozenset,
		__builtin__.dict,
		
		# special sequences
		__builtin__.slice,
		# __builtin__.enumerate, # not implementable - can't recreate from given attr
		# __builtin__.xrange, # not implementable - can't recreate from given attr
		
		# special reserved
		__builtin__.file,
		# __builtin__.buffer, # not implementable - can't recreate from given attr
		# __builtin__.memoryview, # not implementable - can't recreate from given attr
	)

	BUILTIN_TYPE_LOOKUP = dict( (t,ix) for ix,t in enumerate(BUILTIN_TYPE_LIST))
	BUILTIN_TYPE_LOOKUP[type(None)] = 0

	BUILTIN_TYPE_WRITERS = ('write_none',) + tuple(
							'write_%s' % builtin_type.__name__ 
							   for builtin_type 
							   in BUILTIN_TYPE_LIST[1:] )
	BUILTIN_TYPE_READERS = ('read_none',) + tuple(
							'read_%s' % builtin_type.__name__ 
							   for builtin_type 
							   in BUILTIN_TYPE_LIST[1:] )


	def get_type(self, type_ix):
		try:
			return self.BUILTIN_TYPE_LIST[type_ix]
		except IndexError:
			raise NotImplementedError('Runtime type resolution not written yet (needs lookups)')


	def get_type_ix(self, obj):
		obj_type = type(obj)
		try:
			return self.BUILTIN_TYPE_LOOKUP[obj_type]
		except KeyError:
			raise NotImplementedError('Runtime type index resolution not written yet (needs lookups)')


	def write_object(self, obj):
		# make sure we have both the type index AND the encoder function!
		try:
			type_ix = self.get_type_ix(obj)
			writer = getattr(self, self.BUILTIN_TYPE_WRITERS[type_ix])
		except (NotImplementedError, IndexError):
			self.write_object_using_type(obj)
			return
		# use the writer
		self.write_type_ix(type_ix)
		writer(obj)


	def write_object_using_type(self, obj):
		# NOTE: this will look a bit different:
		#    - object's type_ix
		#    - state's type_ix
		#    - state data
		# If we see a non-builtin type, that means we expect _another_ type 
		# immediately after to resolve. Eventually, we'll get to a base type.
		# Turtles all the way down.
		# The class is expected to ingest this state to recreate state.
		
		# dump and load are all-in-one
		dumper = getattr(obj, '__dump__', None)
		if dumper and dumper.__self__:
			try:
				state = obj.__dump__()
			except NotImplementedError:
				pass # dump method not implemented
			
			try:
				self.write_object(state)
			except NameError:
				pass # state not defined!
		
		# otherwise try to get the pickle methods for init (and optionally apply state after)
		initializer = getattr(obj, '__getnewargs_ex__', getattr(obj, '__getnewargs__', None))
		if initializer:
			init_details = initializer()
			self.write_object(init_details)
		
		# NOTE: iff the __getstate__ AND __setstate__ dunders are included,
		# then include the state. This will be applied after init.
		try:
			if obj.__setstate__ and obj.__getstate__:
				self.write_object(obj.__getstate__())
		except AttributeError:
			pass


	def read_object(self):
		type_ix = self.read_type_ix()
		try:
			reader = getattr(self, self.BUILTIN_TYPE_READERS[type_ix])
		except IndexError:
			# ask the type to create/return the object for us
			# first read in the state object
			obj_type = self.get_type(type_ix)
			return self.read_object_given_type(obj_type)
		return reader()


	def read_object_given_type(self, obj_type):
		try:
			state = self.read_object()
			
			# load and dump are all-in-one and don't have follow-up
			loader = getattr(obj_type, '__load__', None)
			if loader and loader.__self__: # if unbounded, not a class method for loading
				try:
					obj = obj_type.__load__(state)
					return obj
				except NotImplementedError:
					pass
			
			# otherwise try for the other initializing methods
			# _ex means "args and kwargs"
			initializer = getattr(obj_type, '__getnewargs_ex__', None)
			if initializer:
				args, kwargs = state
				obj = obj_type(*args, **kwargs)
			else:
				# just args
				initializer = getattr(obj_type, '__getnewargs__', None)
				if initializer:
					args = state
					obj = obj_type(*args)
			
			# state may also be given AS WELL AS init stuff
			try:
				if obj.__setstate__ and obj.__getstate__:
					if not initializer: # create a default instance
						obj = obj_type()
					obj.__setstate__(self.read_object())
			except AttributeError:
				pass            
			return obj
		except NameError as error:
			print error
			raise RuntimeError('Could not load init/state for type %r' % obj_type)



class Bincoder(ConsolidatedHandler):
	"""Encode and decode objects in a binary format into an existing stream.
	
	Generally, simply use .write_object(obj) to encode an object onto a stream.
	Use .read_object() to get the next object in the stream.
	
	Works on file objects, StringIO, and ByteIO objects 
	(and likely anything that implements per-byte .read_object() and .write_object())
	"""

	def __init__(self):
		self.stream = None


class BytesIOBincoder(Bincoder):
	
	def __init__(self):
		self.stream = BytesIO()
		
	def read(self):
		self.stream.seek(0)
		return self.stream.read()

	def write(self, obj):
		self.write_object(obj)


class StreamBincoder(Bincoder):
	
	def __init__(self, stream):
		self.stream = stream


TEST_CASES = {
	'none': [   None],
	'bool': [   True, False],
	'int':  [   0, 1, 2, -1, 
				(1<<31)-1, -(1<<31), ],
	'long': [   0, 1, 2, -1, 
				(1<<31)-1, -(1<<31),
				(1<<31), -(1<<32),
				(1<<100), -(1<<100), ],
	'long_compressed': [   0, 1, 2, -1, 
				(1<<31)-1, -(1<<31),
				(1<<31), -(1<<32),
				(1<<100), -(1<<100), ],
	'float': [  0, 1, 2, -1,
				0.0, 1.0, 2.0, -1.0,
				1.234, -1.234,
				1234567890123456789.123456789,
				-1234567890123456789.123456789, ],
	'complex': [complex(0, 0), 
				complex(1.234, 0), complex(0, 1.234), complex(1.2, 1.2), 
				complex(-2.3, 0), complex(0, -34.5), complex(-2.3,-34.5), ],
	'str': [    '', 'asdf', 'asdf\n\t,QWER' ],
	'unicode': [u'', u'asdf', u'asdf\n\t,QWER',
				u'Sîne klâwen durh die wolken sint geslagen',],
	'bytearray': [bytearray(), bytearray('asdf')],
	'tuple': [  tuple(), (1,), (1,2,), (1,2,3,4,5,),
				(((1,2,3),(4,'qwer',6),),(None,tuple())),
				tuple(range(10000)), ],
	'list': [   list(), [1], [1,2], [1,2,3,4,5],
				[[[1,2,3],[4,'qwer',6]],[None,[]]],
				list(range(10000)), ],
	'set': [    set(), set([1]), set([1,2]), set([1,2,3,4,5]),
				set('aaaaabcd'),
				set((((1,2,3),(4,'qwer',6),),(None,tuple()))),
				set(range(10000)), ],
	'frozenset': [  frozenset(), frozenset([1]), frozenset([1,2]), frozenset([1,2,3,4,5]),
				frozenset('aaaaabcd'),
				frozenset((((1,2,3),(4,'qwer',6),),(None,tuple()))),
				frozenset([frozenset([frozenset([1,2,3]),frozenset([4,'qwer',6])]),frozenset([None,frozenset()])]),
				frozenset(range(10000)), ],
	'dict': [   dict(), {},
				{'a': 1}, {'a': 1, 2: 'b'},
				{'a': {'a': {'a': {'a': 1}}}}, ],
	'slice': [  slice(None, None, None),
				slice(None, None, None), slice(None, None, None), slice(None, None, None),
				slice(1, None, None), slice(None, 1, None), slice(None, None, 1),
				slice(1, 2, None), slice(None, 1, 2), slice(None, 1, 1),
				slice(1,2,3), slice('a', 'b'), slice(start=0, stop=1000, step=34.3), ],
#   'file': NotImplementedError('not bothering here... manual tests showed it was reasonable,'
#                               'and frankly it should not come up...')
}



def _run_tests():
	
	from io import BytesIO
	from StringIO import StringIO
	
	from java.lang import Exception as JavaException
	
	
	def test(value, name):
		stream = BytesIO()
	
		bincoder = StreamBincoder(stream)
		
		writer = getattr(bincoder, 'write_%s' % name)
		reader  = getattr(bincoder, 'read_%s' % name)
		
		# write value to stream
		writer(value)
		
		# reset!
		stream.seek(0)
		# ... so we can read from the stream
		result = reader()
	
		# print repr(value)
		# print repr(result)
		
		# check values!
		assert value == result, '%r =/=> %r' % (value, result)
	
	for name, values in TEST_CASES.items():
		for value in values:
			# print '==========================================='
			# print 'testing: ', name, value
			try:
				test(value, name)
			except (Exception, JavaException) as error:
				print 'FAILED:', name
				print '       ', repr(error)
	
