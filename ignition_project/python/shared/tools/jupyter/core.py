"""
	Coordinate and launch the kernel
"""
logger = shared.tools.jupyter.logging.Logger()

from shared.tools.thread import async, Thread, findThreads, getThreadFrame
from shared.tools.logging import Logger
from shared.tools.jupyter.logging import DEFAULT_LOGGING_LEVEL


from random import choice
from uuid import uuid4
from datetime import datetime, timedelta
import string
import json
from time import sleep
import re
import itertools



from shared.tools.jupyter.messages import KernelMessagingMixin
from shared.tools.jupyter.comm import KernelCommMixin
from shared.tools.jupyter.catch import *
from shared.tools.jupyter.zmq import *
from shared.tools.jupyter.wire import WireMessage
from shared.tools.jupyter.execution.context import ExecutionContext
from shared.tools.jupyter.status import declare_busy, declare_idle, declare_starting


def random_id(length=4):
	return ''.join(choice(string.hexdigits[:16]) for x in range(length))


#kernel = shared.tools.jupyter.core.spawn_kernel()
def re_match_groupdict(pattern, value, flags=0):
	match = re.match(pattern, value, flags)
	if match:
		return match.groupdict()
	else:
		return {}

def re_match_extract(pattern, value, name):
	return re_match_groupdict(pattern, value).get(name)


def getFirstObjectFromThreadFrame(thread_handle, object_name):
	"""Create the frame stack, then walk backwards back up from root to find the first time object shows up"""
	frame = getThreadFrame(thread_handle)
	frames = [frame]
	while frame.f_back:
		frames.append(frame.f_back)
		frame = frame.f_back
	for frame in reversed(frames):
		try:
			return frame.f_locals[object_name]
		except KeyError:
			pass
	else:
		raise NameError('The object %s is not local to %r' % (object_name, thread_handle,))


class CardiacArrest(RuntimeError): pass



class MetaKernelContext(type):
	"""High level master control over all kernels.
	
	From here any particular active kernel can be retrieved.
	All kernels may be scrammed here, though errors may need to be manually identified
	and followed up upon.	
	"""
	_META_LOGGER = Logger('Jupyter Meta Control', logging_level=DEFAULT_LOGGING_LEVEL)
	_THREAD_PREFIX_PATTERN = 'Jupyter-Kernel-(?P<kernel_id>[0-9a-fA-F-]+)'
	_THREAD_SUFFIX_PATTERN = '-(?P<kernel_role>[a-zA-Z0-9_-]+)'
	_OVERWATCH_THREAD_PATTERN = _THREAD_PREFIX_PATTERN + '-Overwatch'
	_LAUNCHER_THREAD_PATTERN = _THREAD_PREFIX_PATTERN + '-Launcher'	
	
	def __getitem__(cls, kernel_id):
		"""Grab the kernel state from the holding thread"""
		try:
			from shared.tools.thread import getFromThreadScope, findThreads
			thread_handle = findThreads('Jupyter-Kernel-%s-Overwatch' % kernel_id)[0]
			return getFirstObjectFromThreadFrame(thread_handle, 'kernel')
#			return getFromThreadScope(thread_handle, 'kernel')
		except:
			raise KeyError("Kernel id %s not found." % (kernel_id,))
			
	@property
	def _meta_all_threads(cls):
		for thread_handle in findThreads(cls._THREAD_PREFIX_PATTERN + cls._THREAD_SUFFIX_PATTERN):
			if thread_handle.getState() == Thread.State.TERMINATED:
				continue
			yield thread_handle
	
	@property
	def _meta_all_overwatch_threads(cls):
		for thread_handle in cls._meta_all_threads:
			if re.match(cls._OVERWATCH_THREAD_PATTERN, thread_handle.getName()):
				yield thread_handle
				
	def __contains__(cls, kernel_id):
		assert kernel_id
		return any(kernel_id == re_match_extract(
						cls._OVERWATCH_THREAD_PATTERN, 
						thread_handle.getName(),
						'kernel_id',
					)
				   for thread_handle 
				   in cls._meta_all_overwatch_threads
				)

	def __iter__(cls):
		for thread_handle in cls._meta_all_overwatch_threads:
			try:
				yield getFirstObjectFromThreadFrame(thread_handle, 'kernel')
#				yield getFromThreadScope(thread_handle, 'kernel')
			except:
				cls._META_LOGGER.debug("No kernel found in %r. Killing thread." % thread_handle)
				thread_handle.interrupt()
				pass

	def SCRAM_ALL(cls):
		cls._META_LOGGER.warn(">>> Scramming ALL Kernels <<<")
		
		# halt and crash any launching kernels
		for thread_handle in cls._meta_all_threads:
			if re.match(cls._LAUNCHER_THREAD_PATTERN, thread_handle.getName()):
				thread_handle.interrupt()
		
		# iterate all kernels running
		kernels = list(cls)
		for kernel in kernels:
			try:
				kernel.SCRAM()
			except:
				cls._META_LOGGER.error(">>> Kernel %(kernel_id)s did not scram!" % kernel)
			
		cls._META_LOGGER.warn(">>> Lingering a moment before verifying...")
		sleep(2.0)
		for kernel in kernels:
			try:
				assert kernel.overwatch_thread.getState() == Thread.State.TERMINATED
			except AssertionError:
				cls._META_LOGGER.error(">>> %r did not terminate!" % thread_handle)
		cls._META_LOGGER.warn(">>> SCRAM complete. Check logs for errors in case of gracelessness.")


class KernelContext(
	KernelMessagingMixin,
	KernelCommMixin,
	):
	# for convenient class-level operations
	__metaclass__ = MetaKernelContext

	_PREP_METHODS = ('init', 'launch', 'tear_down')
	
	__slots__ = (
		'kernel_name',                 # generic description of kernel type
		'kernel_id',                   # lookup key for reference in Ignition
		'signature_scheme', 'key',     # id/key used by Jupyter (likely same as kernel_id)
		'transport', 'ip', 'zcontext', 'zpoller',
		
		'session', 'username',
		'jupyter_session',
		
		'default_logging_level',
		'live_reload',
		
		'min_port_range', 'max_port_range',
		'loop_delay', 'lingering_delay',
		'interrupted',
		
		'traps', # bucket for signals to trap debug loggers and such
		
		# kernel auto-cleanup when orphaned
		'last_heartbeat', 'cardiac_arrest_timeout',
		
		# holding attributes for core functionality across the five main threads
		'overwatch_thread', # 'lifeline_thread',
		'shell_port',    'iopub_port',       'stdin_port',    'control_port',   'heartbeat_port',
		'shell_socket',  'iopub_socket',     'stdin_socket',  'control_socket', 'heartbeat_socket',
		                 'iopub_sub_socket', # this is the socket associated with a recv thread, though
		
		# reload requests that the thread replace it's event loop function
		# this helps with hot reloading and development/debug of the kernel itself
		'shell_handler',  'iopub_handler',  'stdin_handler',  'control_handler', 'heartbeat_handler',
		
		# custom message management
		'comms', 'comm_targets',
		
		# convenience functions for auto-resolving so stuff can't get mixed up
		'loggers',
	) + tuple('%s_%s' % (a,b) for a,b in itertools.product(('pre', 'post'), _PREP_METHODS))
	
	# allow init_kwargs to use different names (since the kernel standard may not fit my convention)
	# (... and I can't be arsed to rewrite now...)
	_SLOT_ALIAS_BRIDGE = {
		'heartbeat_port': 'hb_port',
		'kernel_id': 'ignition_kernel_id',
	}
	
	ACTIVE_HANDLER_RELOAD = False
	
	ZMQ_DONTWAIT = ZMQ.DONTWAIT
	
	ZMQ_ROLE_SOCKET_TYPES = {
		'shell'    : SocketType.ROUTER,
		'iopub'    : SocketType.PUB,
		'stdin'    : SocketType.ROUTER,
		'control'  : SocketType.ROUTER,
		'heartbeat': SocketType.REP,
	}
	
	_DEFAULTS = {
			'kernel_name': 'ignition_kernel',
			'transport': 'tcp',
			'ip': '*', # '127.0.0.1',
			
			'username': 'kernel',
			
			'signature_scheme': 'hmac-sha256',
			
			'min_port_range': 30000,
			'max_port_range': 32000,
			
			'loop_delay': 0.05,      # seconds
			'lingering_delay': 0.35, # seconds
			
			'default_logging_level': DEFAULT_LOGGING_LEVEL,
			'live_reload': False,
			'interrupted': False,
			
			# set to None 
			'cardiac_arrest_timeout': timedelta(minutes=15),
			
			# prime for first load
#			'shell_handler':     'shared.tools.jupyter.handlers.shell.message_handler',
#			'iopub_handler':     'shared.tools.jupyter.handlers.iopub.message_handler',
#			'stdin_handler':     'shared.tools.jupyter.handlers.stdin.message_handler',
#			'control_handler':   'shared.tools.jupyter.handlers.control.message_handler',
#			'heartbeat_handler': 'shared.tools.jupyter.handlers.heartbeat.payload_handler',
			'shell_handler':     shared.tools.jupyter.handlers.shell.message_handler,
			'iopub_handler':     shared.tools.jupyter.handlers.iopub.message_handler,
			'stdin_handler':     shared.tools.jupyter.handlers.stdin.message_handler,
			'control_handler':   shared.tools.jupyter.handlers.control.message_handler,
			'heartbeat_handler': shared.tools.jupyter.handlers.heartbeat.payload_handler,
		
		}
	
	# default overrides for certain
	for a,b in itertools.product(('pre', 'post'), _PREP_METHODS):
		_DEFAULTS['%s_%s' % (a,b)] = lambda kernel: None
	
	
	def __init__(self, **init_kwargs):
		for slot in self.__slots__:
			try:
				setattr(self, slot, init_kwargs.get(slot, 
									init_kwargs.get(self._SLOT_ALIAS_BRIDGE.get(slot, slot),
									self._DEFAULTS.get(slot, None))))
			except Exception as error:
				logger.error('Slot failed to get settings: %(slot)r')
				raise error
		
		self.last_heartbeat = datetime.now()
		
		self.traps = {}
			
		self._pre_init()
		
		if self.kernel_id is None:
			self.kernel_id = random_id()
			
		self.overwatch_thread = Thread.currentThread()
		self.overwatch_thread.setName("Jupyter-Kernel-%(kernel_id)s-Overwatch" % self)
					
		if self.key is None:
			self.key = str(uuid4())
		assert self.key not in KernelContext, "Kernel %(kernel_id)s already started!" % self
		
		if self.username is None:
			self.username = SystemUtils.USER_NAME
		
		# ready for comms
		self.comms = {}
		self.comm_targets = {}
		
		self.setup_loggers()
		
		self._post_init()

	@property
	def session_id(self):
		"""Needed so we can send messages even if there isn't an active session _yet_ (or between them)"""
		if self.session:
			return self.session.id
		else:
			return '' # no session!

	def __repr__(self):
		return 'KernelContext[%(kernel_id)r]' % self


	def __enter__(self):
		self.launch()
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		self.tear_down()
	
	
	def check_pulse(self):
		if self.cardiac_arrest_timeout:
			if self.last_heartbeat < (datetime.now() - self.cardiac_arrest_timeout):
				raise CardiacArrest


	def SCRAM(self):
		self.logger.warn(">>> Scramming Kernel %(kernel_id)s <<<" % self)
		try:
			self.tear_down()
		finally:
			self.overwatch_thread.interrupt()
			sleep(self.lingering_delay)
			self.logger.debug('Closure: %-34s ==> %r' % (
				str(self.overwatch_thread.getName()), self.overwatch_thread.getState() ))


	def tear_down(self):
		try:
			self._pre_tear_down()
			
			self.logger.info('Tearing down kernel %(kernel_id)s...' % self)
			
			if self.session:
				self.session.destroy()
			
			if self.zcontext.isEmpty() and self.zcontext.isClosed():
				self.logger.warn('ZContext for already emptied and closed')
				return
			
			try:
				self.logger.info('Closing poller...')
				self.zpoller.destroy()
				
				self.logger.info('Destroying sockets...')
				for socket in self.zcontext.getSockets():
					self.zcontext.destroySocket(socket)
				
				for attr in [attr for attr in self.__slots__ if attr.endswith('_port') or attr.endswith('_socket')]:
					setattr(self, attr, None)
			
			finally:
				self.logger.debug('Destroying zcontext...')
				self.zcontext.destroy()
			
				self.logger.info('Done. Good-bye!')
		finally:
			self._post_tear_down()


	def launch(self):
		self._pre_launch()
		
		if self.ACTIVE_HANDLER_RELOAD:
			self.reload_handlers()
	
		assert not self.is_launched, "ZContext already launched! HCF >_<"
		self.zcontext = ZContext()
		
		for role in self._canonical_roles:
			# create sockets
			socket = self.zcontext.createSocket(self.ZMQ_ROLE_SOCKET_TYPES[role])
			
			self[role + '_socket'] = socket
			
			# if not explicitly requested by kernel startup,
			# then bind each to a random port (a connection file may have been
			# provided that declared what ports to use, so use those if set)
			if self[role + '_port'] is None:
			   self[role + '_port'] = self.bind_random_port(self[role + '_socket'])
			else:
			   self.bind_selected_port(self[role + '_socket'], self[role + '_port'])
			self.logger.trace('%-16s on port %d' % (role, self[role + '_port']))
		
		declare_starting(self)
		
		# five main sockets and the loopback sub for iopub sub
		self.zpoller = ZPoller(self.zcontext)
		
		for socket in self.sockets:
			self.zpoller.register(socket, ZPoller.POLLIN) # self[role + '_handler']
		
		self.setup_loggers()
		
		self.new_execution_session()
		
		sleep(0.25)
		
		self._post_launch()
		
		declare_idle(self)


	def new_execution_session(self):
		self.session = ExecutionContext(self)
		try:
			self.heartbeat_socket.send('restart')
		except:
			pass # maybe not set up yet


	# runtime user overrides
	# (unbound, so we grab it, then fire it)
	def _pre_launch(self):
		self.pre_launch(self)
	
	def _post_launch(self):
		self.post_launch(self)
	
	def _pre_init(self):
		self.pre_init(self)
	
	def _post_init(self):
		self.post_init(self)
	
	def _pre_tear_down(self):
		self.pre_tear_down(self)
	
	def _post_tear_down(self):
		self.post_tear_down(self)
	
	
	@property
	def _canonical_roles(self):
		return 'heartbeat shell control stdin iopub'.split()
	
	
	@property
	def sockets(self):
		return [self[role + '_socket'] for role in self._canonical_roles]
	
	
	def poll(self, msTimeout=10):
		try:
			self.zpoller.poll(msTimeout)		
			for role, socket in zip(self._canonical_roles, self.sockets):
				if self.zpoller.isReadable(socket):
					# heartbeat is first, and is the only raw payload that isn't a message
					if role == 'heartbeat':
						#self.logger.info('Heartbeat    C: ')
						payload = socket.recv()
						self[role + '_handler'](self, payload)
					else:
						zMessage = ZMsg.recvMsg(socket, ZMQ.DONTWAIT)
						if zMessage is not None:
							zMessage.dump()
							message = WireMessage(zMessage, 
									  key=self.key, 
									  signature_scheme=self.signature_scheme
								)
							try:
								declare_busy(self, message)
								if self.ACTIVE_HANDLER_RELOAD:
									reload_function(self[role + '_handler'])(self, message)
								else:
									self[role + '_handler'](self, message)
								zMessage.destroy()
							finally:
								declare_idle(self, message)
		except KeyboardInterrupt:
			self.logger.error('Kernel interrupted')
			self.interrupted = True
		except Exception as python_interruption_sideeffect:
			self.logger.error('Python Handler error %(python_interruption_sideeffect)r')
			self.logger.error(python_full_stack())
			self.interrupted = True
		except ZError as zmq_error:
			self.logger.error('ZMQ error %(zmq_error)r')
			# self.logger.error(zmq_error)
			self.interrupted = True	
		except ZMQException as zmq_error:
			self.logger.error('ZMQ Handler error %(zmq_error)r')
			# self.logger.error(zmq_error)
			self.interrupted = True
		except JavaNioChannelsClosedSelectorException as channel_closed_error:
			pass
			self.interrupted = True
		except JavaException as java_interruption_sideeffect:
			if 'java.nio.channels.ClosedChannelException' in repr(java_interruption_sideeffect):
				pass # gawd just stop throwing this when murdered!
			else:
				self.logger.error('Java Handler error %(java_interruption_sideeffect)r')
				self.logger.error(java_full_stack(java_interruption_sideeffect))
			self.interrupted = True
	
	
	def reload_handlers(self):
		for role in self._canonical_roles:
			self[role + '_handler'] = reload_function(self[role + '_handler'])
	
	
	@property
	def now(self):
		# TODO: should include UTC tz object
		return datetime.utcnow().isoformat()[:23] + 'Z'
	
	
	@property
	def is_launched(self):
		return not (self.zcontext is None or self.zcontext.isClosed())
	
	@property
	def is_interrupted(self):
		self.check_pulse()
		return self.interrupted
	
	
	def bind_random_port(self, socket):
		return socket.bindToRandomPort(
				'%(transport)s://%(ip)s' % self, 
				self.min_port_range,
				self.max_port_range,
			)

	def bind_selected_port(self, socket, port):
		socket.bind(('%%(transport)s://%%(ip)s:%d' % port) % self)


	def __getitem__(self, item):
		try:
			return getattr(self, item)
		except AttributeError:
			raise KeyError('%r is not accessible from Kernel Context' % (item,))

	def __setitem__(self, item, value):
		try:
			setattr(self, item, value)
		except AttributeError:
			raise KeyError('%r is not accessible from Kernel Context' % (item,))


	@property
	def logger(self):
		return self.loggers.get(Thread.currentThread(), self.loggers[None])

	def setup_loggers(self):
		self.loggers = {
				self.overwatch_thread: Logger('Jupyter-Kernel', prefix='[%(kernel_id)s <hub>] ' % self, suffix='',logging_level=self.default_logging_level),
			}
		# ensure that None is the default (in case threads are still uninitialized)
		self.loggers[None] = Logger('Jupyter-Kernel', prefix='[%(kernel_id)s >>_<<] ' % self, suffix='',logging_level=self.default_logging_level)


	@property
	def connection_file(self):
		return json.dumps(self.connection_info, indent=2,)
	
	@property
	def connection_info(self):
		return {
			'transport': self.transport,
			'ip': self.ip,
			
			'ignition_kernel_id': self.ignition_kernel_id,
			
			'signature_scheme': self.signature_scheme,
			'key': self.key,
			
			'shell_port':   self.shell_port,
			'iopub_port':   self.iopub_port,
			'stdin_port':   self.stdin_port,
			'control_port': self.control_port,
			'hb_port':      self.hb_port,
		}
	
	
	# PROPERTIES OF SHAME
	# Wherein I couldn't be arsed to refactor and just let there be two names for something.
	@property
	def hb_port(self):
		return self.heartbeat_port
	
	@hb_port.setter
	def hb_port(self, new_port):
		self.heartbeat_port = hb_port

	@property
	def ignition_kernel_id(self):
		return self.kernel_id
	
	@ignition_kernel_id.setter
	def ignition_kernel_id(self, new_kernel_id):
		self.kernel_id = new_kernel_id


#def get_kernel_context(kernel_id):
#	"""Grab the kernel state from the holding thread"""
#	from shared.tools.thread import getFromThreadScope, findThreads
#	thread_handle = findThreads('Jupyter-Kernel-%s-Launcher' % kernel_id)[0]
#	return getFromThreadScope(thread_handle, 'kernel')
#
#def list_kernels():
#	found_kernels = []
#	for thread_handle in findThreads('Jupyter-Kernel-.+-Overwatch'):
#		found_kernels.append(thread_handle.getName()[15:-10])
#	return found_kernels



def spawn_kernel(**kernel_init_kwargs):
	if not kernel_init_kwargs:
		kernel_init_kwargs['kernel_id']= random_id()
	thread_handle = kernel_event_loop(**kernel_init_kwargs)
	sleep(0.45)
	try:
		return getFirstObjectFromThreadFrame(thread_handle, 'kernel')
	except KeyError:
		raise RuntimeError("Kernel likely failed to start. Check logs.")
		return None
#kernel = shared.tools.jupyter.core.spawn_kernel()



@async(name="Jupyter-Kernel-XXXX-Overwatch")
def kernel_event_loop(**kernel_init_kwargs):
	with KernelContext(**kernel_init_kwargs) as kernel:
		kernel.logger.info('Overwatch holding thread started.')
		try:
			while not kernel.is_interrupted:
				kernel.poll(10)

#				sleep(kernel.lingering_delay)
		except KeyboardInterrupt:
			kernel.logger.info('Overwatch interrupted. Halting.')
		except CardiacArrest:
			kernel.logger.warn("Kernel lost Jupyter's kernel manager's heartbeat. Exiting.")



def reload_function(function):
	"""Return the most recent live version of function. 
	Can be the original function or the import path string to get it.
	
	Imports may be cached, and direct references may not update during execution.
	This grabs the reference straight from the horse's mouth.
	
	TODO: may need project scope access to work (i.e. from webdev)
	"""
	# resolve the thing to refresh
	if isinstance(function, (str, unicode)):
		module_path, _, function_name = function.rpartition('.')
	else:
		module_path = function.func_code.co_filename[1:-1].partition(':')[2]
		function_name = function.func_code.co_name
	# get system context
	context = shared.tools.meta.getIgnitionContext()
	script_manager = context.getScriptManager()
	current_scripting_state = script_manager.createLocalsMap()
	# resolve the function again
	import_parts = module_path.split('.')
	thing = current_scripting_state[import_parts[0]]
	for next_module in import_parts[1:]:
		try:
			thing = thing.getDict()[next_module]
		except AttributeError:
			thing = getattr(thing, next_module)
	return getattr(thing, function_name)





## script playground context
#from shared.tools.pretty import p,pdir,install;install()
#try:
#	print 'Kernel %r state: %r' % (kernel_id, kernel_context['threads']['hub'].getState())
#except NameError:
#	from shared.tools.jupyter.core import spawn_kernel, get_kernel_context
#	from time import sleep
#	kernel_id = spawn_kernel()
#	sleep(0.25)
#	kernel_context = get_kernel_context(kernel_id)
#	scram = lambda kernel_context=kernel_context: kernel_context['threads']['hub'].interrupt()