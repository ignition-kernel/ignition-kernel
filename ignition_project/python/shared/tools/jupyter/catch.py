logger = shared.tools.jupyter.logging.Logger()

from java.lang import Exception as JavaException
import java.nio.channels.ClosedSelectorException as JavaNioChannelsClosedSelectorException
from org.apache.commons.lang3.exception import ExceptionUtils
from org.apache.commons.lang3 import SystemUtils


from shared.tools.jupyter.zmq import ZMQException, ZError



__all__ = [
	'python_full_stack', 'java_full_stack',
	'JavaException', 'JavaNioChannelsClosedSelectorException',
	'ZMQException', 'ZError',

]

# error utility

def python_full_stack():
    import traceback, sys
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    if exc is not None:  # i.e. an exception is present
        del stack[-1]       # remove call of full_stack, the printed exception
                            # will contain the caught exception caller instead
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
         stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr

def java_full_stack(error):
	return ExceptionUtils.getStackTrace(error)