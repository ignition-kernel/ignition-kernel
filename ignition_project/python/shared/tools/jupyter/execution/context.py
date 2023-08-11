"""
	Run Python, one command at a time.
	
	
"""
logger = shared.tools.jupyter.logging.Logger()


from shared.tools.jupyter.execution.results import ExecutionResults, ResultHistory
from shared.tools.jupyter.execution.priming import metatools_startup
from shared.tools.jupyter.execution.run import Executor


from uuid import uuid4
from org.python.core import Py



class ExecutionContext(object):
	"""A Python execution context."""
	__slots__ = [
		'id', 'kernel', 
		'execution_count', 
		'history',
		'python_state_locals', 'python_state_globals',
	]
	
	def __init__(self, kernel, locals_dict=None, globals_dict=None,):
		self.kernel = kernel
		self.id = str(uuid4())
		
		self.execution_count = 0
		
		self.python_state_locals = locals_dict or {}
		self.python_state_globals = globals_dict or {}
		
		self.history = {}
		
		metatools_startup(self)
	
	
	@property
	def _context_sys(self):
		"""
		Gets sys without using the import mechanics. Sorta.
		
		Technically we don't need to go this far, but I wanted it to be clear that 
		we're actively intercepting execution details.		
		"""
		# This is very likely _not_ true, but frankly I don't want this to be multithreaded.
		# It's not meant to be multithreaded in execution and no effort will be made to keep it safe.
		return Py.getThreadState().systemState
	
	@property
	def _context(self):
		return {
			'captured_sys': self._context_sys, 
			'global_context': self.python_state_globals,
			'local_context': self.python_state_locals,
			# show where the next execution goes
			'execution_location': '<Jupyter In[%d]>' % (self.execution_count + 1,),
		}
	
	def destroy(self):
		self.python_state_locals.clear()
		self.python_state_globals.clear()
	
	def __bool__(self):
		return False # NOP


	def execute(self, code, store_history=True):
		with Executor(**self._context) as executor:
			executor.execute(code)
		
		if store_history:
			self.execution_count += 1		
			self.history[self.execution_count] = ExecutionResults(executor)
	
	def dump_output(self):
		for i in range(1, self.execution_count):
			if self.history[i].stdout:
				entry = ('OUT[%d] ' % i)
				print entry  + '\n'.join((' '*len(entry)) + line 
										 for line 
										 in self.history[i].stdout.splitlines()
										)[len(entry):]
	
	def __getitem__(self, history_ix):
		if history_ix < 0:
			history_ix = self.execution_count + history_ix + 1
		return self.history[history_ix]
	
	def __repr__(self):
		return '<ExecutionContext [%d]>' % (self.execution_count,)




##
##try:
##	print 'Context ready: %r' % ec
##except NameError:
#if True:
#	ec_local = {}
#	ec_global = {}
#	
#	ec = ExecutionContext(None, locals_dict=ec_local, globals_dict=ec_global)
#
#
#
#ec.execute('x = 5')
#ec.execute('print x')
#ec.execute('111 + x')
#ec.execute('x += 234')
#ec.execute('print x + 555')
#ec.execute('x')
##print ec[-1].code, '|', ec[-1].stdout, '|', ec[-1]._
#
#