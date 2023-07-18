def doGet(request, session):
	log = shared.tools.logging.Logger()
	
	from shared.tools.jupyter.core import KernelContext
	
	if request["remainingPath"]:
		kernel_id = request["remainingPath"][1:]
		try:
			return {'json': KernelContext[kernel_id].connection_file}
		except KeyError:
			response = request["servletResponse"]
			response.setStatus(404)
			return
	else:
		return {'json': [kernel.kernel_id for kernel in KernelContext]}