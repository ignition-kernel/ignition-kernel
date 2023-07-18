"""
	Basically just a place to put different priming contexts.
	
	Personally, I prefer my metatools stuff :) - ARG

	Note that there is a difference between locals and globals, but it's not quite obvious.
		If an execution context sets something as local, it will _not_ be available when compiled
		into a function's body since the function body overrides the locals. (Globals don't become
		local to a function without `global`, after all.)
	As a result, anything executed as though module-level or from the interactive prompt is treated
	as global. Any local changes clobber global scope in the execution context.	
	
"""

logger = shared.tools.jupyter.logging.Logger()

from shared.tools.jupyter.execution.results import ResultHistory



def metatools_startup(execution_context):
	"""
	Prime the kernel with metatools and some helpers.
	"""
	ec_locals  = execution_context.python_state_locals
	ec_globals = execution_context.python_state_globals
	
	# expected available imports
	ec_globals['shared'] = shared
	ec_globals['system'] = system
	
	# helpful interactive bits
	ec_locals['kernel'] = execution_context.kernel
	ec_locals['context'] = shared.tools.meta.getIgnitionContext()
	ec_locals['p'] = shared.tools.pretty.p
	ec_locals['pdir'] = shared.tools.pretty.pdir

	# IPython-y things
	ec_locals['In'] = ResultHistory(execution_context, 'code')
	ec_locals['Out'] = ResultHistory(execution_context, 'display_object')

