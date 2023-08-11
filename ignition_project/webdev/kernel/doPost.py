def doPost(request, session):

	from shared.tools.jupyter.catch import JavaException, java_full_stack
	
	try:
		result = shared.tools.jupyter.handlers.web.kernel.doPost(request)
		return {'json': result}
	except (Exception, JavaException) as error:
		response = request["servletResponse"]
		response.setStatus(404)
		raise error

#	log = shared.tools.logging.Logger()
#	
#	from shared.tools.jupyter.core import KernelContext, spawn_kernel
#	
#	payload = request["remainingPath"]
#	request
#	log.trace(payload)
#	
#	try:
#		kernel_id = payload['kernel_id']
#		kernel = KernelContext[kernel_id]
#		log.warn('Kernel already running: [%(kernel_id)s]' % kernel)
#	except KeyError:
#		kernel = spawn_kernel(**payload)
#		log.warn('Launched [%(kernel_id)s]' % kernel)
#		log.info('Kernel info: %r' % (kernel.connection_info,))
#
#	for key, value in payload.items():
#		if not kernel[key] == value:
#			log.warn('Kernel [%s] config mismatch on %s: %r vs %r' % (kernel.kernel_id, key, value, kernel[key]))
#	
#	
#	return {'json': kernel.connection_info}