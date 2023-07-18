def doPost(request, session):
	log = shared.tools.logging.Logger()
	
	from shared.tools.jupyter.core import KernelContext, spawn_kernel
	
	payload = request["data"] or {}
	
	log.trace(payload)
	
	try:
		kernel_id = payload['kernel_id']
		kernel = KernelContext[kernel_id]
		log.warn('Kernel already running: [%(kernel_id)s]' % kernel)
	except KeyError:
		kernel = spawn_kernel(**payload)
		log.warn('Launched [%(kernel_id)s]' % kernel)
		log.info('Kernel info: %r' % (kernel.connection_info,))

	for key, value in payload.items():
		if not kernel[key] == value:
			log.warn('Kernel [%s] config mismatch on %s: %r vs %r' % (kernel.kernel_id, key, value, kernel[key]))
	
	
	return {'json': kernel.connection_info}