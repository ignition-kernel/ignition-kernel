"""


"""
logger = shared.tools.jupyter.logging.Logger()



def payload_handler(kernel, bytes_payload):
	logger.trace('Ping recieved << %r' % (bytes_payload,))
	kernel.heartbeat_socket.send(bytes_payload)
	logger.trace('Ping returned >> %r' % (bytes_payload,))
