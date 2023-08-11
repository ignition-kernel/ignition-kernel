def doGet(request, session):
	
	from shared.tools.jupyter.catch import JavaException, java_full_stack
	
	try:
		result = shared.tools.jupyter.handlers.web.kernel.doGet(request)
		return {'json': result}
	except (Exception, JavaException) as error:
		response = request["servletResponse"]
		response.setStatus(404)
		raise error
		
#		import sys
#		exception_type, exception, exception_traceback = sys.exc_info()
#		
#		if isinstance(exception, Exception):
#			import traceback
#			stacktrace = ''.join(
#				traceback.format_exception(exception_type, exception, exception_traceback)
#			)
#		elif isinstance(exception, JavaException):
#			stacktrace = java_full_stack(exception)
#		else:
#			stacktrace = repr(exception)
#		return {'response': stacktrace}

#	log = shared.tools.logging.Logger()
#	
#	from shared.tools.jupyter.core import KernelContext
#	
#	if request["remainingPath"]:
#		kernel_id = request["remainingPath"][1:]
#		try:
#			return {'json': KernelContext[kernel_id].connection_file}
#		except KeyError:
#			response = request["servletResponse"]
#			response.setStatus(404)
#			return
#	else:
#		return {'json': [kernel.kernel_id for kernel in KernelContext]}