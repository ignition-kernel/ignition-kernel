"""


"""
logger = shared.tools.jupyter.logging.Logger()



def message_handler(kernel, message):
	logger.debug('[Dispatch] [%s]' % (message.header.msg_type,))
	
	if message.header.msg_type == 'shutdown_request':
		
		if message.content.restart:
			kernel.new_execution_session()
		else:
			kernel.tear_down()
	
		with kernel.iopub_broadcast('shutdown_reply', message) as reply:
			reply.content.restart = message.content.restart