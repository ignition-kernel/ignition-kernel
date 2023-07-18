logger = shared.tools.jupyter.logging.Logger()



from shared.tools.jupyter.logging import log_message_event

from time import sleep


@log_message_event
def execute_request(kernel, message):
	"""
	
	https://jupyter-protocol.readthedocs.io/en/latest/messaging.html#execution-results
	"""
	
	execute_silently = message.content.silent
	store_history = message.content.store_history
	
	cell_id = message.metadata.cellId
	
	# blank code and silent by convention means the client wants to know the current execution count
	if execute_silently and not message.content.code:
		with kernel.iopub_message('execute_input', message) as reply:
			reply.content.execution_count = kernel.session.execution_count + 1
			reply.content.code = ''
		with kernel.iopub_message('execute_reply', message) as reply:
			reply.ids = message.ids
			reply.content = {
				'execution_count': kernel.session.execution_count,
				'status': 'ok',
				
				'user_expressions' :{},
				'payload' : [],
			}
		return
	
	if execute_silently:
		logger.trace('Silent execution requested for: %r' % (message.content.code,))
	
	if not execute_silently:
		with kernel.iopub_broadcast('execute_input', message) as reply:
			reply.content = {
				# preempt the execution to declare we're working on the next _before_ we run it
				# so that the clients can react to "in progress" input cells while waiting
				'execution_count': kernel.session.execution_count + (1 if store_history else 0),
				'code': message.content.code,
			}
			reply.metadata = message.metadata #.cellId = cell_id

	kernel.session.execute(message.content.code, store_history=store_history)
	
	# do not broadcast
	if execute_silently:
		return
	
	# If the execution had STDOUT side effects, broadcast it!
	if kernel.session[-1].stdout:
		with kernel.iopub_broadcast('stream', message) as reply:
			reply.content = {
		        'name': 'stdout',
			    'text': kernel.session[-1].stdout,
			}
	
	# reply with the error to STDERR, if there is one
	if kernel.session[-1].error:
		exception = kernel.session[-1].error
		with kernel.iopub_broadcast('stream', message) as reply:
			reply.content.name = 'stderr'
			reply.content.text = kernel.session[-1].formatted_traceback
	
		with kernel.iopub_broadcast('error', message) as reply:
			reply.content = {
				'dependencies_met': True,
    			'engine': kernel.session.id,
    			'started': kernel.now,
			}
	
	# reply with the last display object, if any
	if kernel.session[-1]._:
		with kernel.iopub_broadcast('execute_result', message) as reply:
			reply.content = {
		        'execution_count': kernel.session.execution_count,
			    'data': {'text/plain':
			    	str(shared.tools.pretty.prettify(kernel.session[-1]._))
			    },
			    'metadata': {},
			}
	
	with kernel.shell_message('execute_reply', message) as reply:
		# reply with the results - error if any, otherwise OK
		if kernel.session[-1].error:
			if isinstance(kernel.session[-1].exception, KeyboardInterrupt):
				reply.content = {
					'execution_count': kernel.session.execution_count,
					'status': 'abort', # TODO: so this doesn't actually stop "RUN ALL CELLS" =/
					'ename'    :kernel.session[-1].exception_type.__name__,
					'evalue'   : kernel.session[-1].exception.message,
					'traceback': kernel.session[-1].formatted_traceback.splitlines(),
				}
			else:
				reply.content = {
					'execution_count': kernel.session.execution_count,
					'status': 'error',
					'ename'    :kernel.session[-1].exception_type.__name__,
					'evalue'   : kernel.session[-1].exception.message,
					'traceback': kernel.session[-1].formatted_traceback.splitlines(),
				}
		else:
			reply.content = {
				'execution_count': kernel.session.execution_count,
				'status': 'ok',
				
            	"started": kernel.now,
				
				'user_expressions' :{},  # TODO: support user_expressions
				'payload' : [],          # TODO: support payloads, like for pagers
			}


EXECUTION_DISPATCH = {
	'execute_request': execute_request,
}

