"""
	Binary representation of strings
	
	While in Jython 2.7 strings are already (immutable) byte arrays,
	some casting is still needed. Moreover, unicode string lenghts
	are _not_ necessarily the same as their byte lenghts, as many
	specialized characters have multiple bytes per codepoint.
"""

__all__ = [
	'StringHandler',
	'UnicodeHandler',
	'BytearrayHandler',
	
	'StringHandlers',
]   


from shared.data.binary.handlers.stream import StreamHandler
from shared.data.binary.handlers.helper import LengthHandler


DEFAULT_ENCODING = 'utf-8'



class StringHandler(LengthHandler, StreamHandler):
	
	STRING_ENCODING = DEFAULT_ENCODING

	def write_str(self, string_value):
		self.write_length(string_value)
		self.write_to_stream(string_value.encode(self.STRING_ENCODING))

	def read_str(self):
		length = self.read_length()
		return self.read_from_stream(length).encode(self.STRING_ENCODING)



class UnicodeHandler(LengthHandler, StreamHandler):

	UNICODE_ENCODING = DEFAULT_ENCODING

	def write_unicode(self, unicode_string_value):
		# convert to bytes first to ensure length is right
		encoded = unicode_string_value.encode(self.UNICODE_ENCODING)
		self.write_length(encoded)
		self.write_to_stream(encoded)

	def read_unicode(self):
		length = self.read_length()
		return unicode(self.read_from_stream(length), self.UNICODE_ENCODING)



class BytearrayHandler(LengthHandler, StreamHandler):

	def write_bytearray(self, byte_array_value):
		self.write_length(byte_array_value)
		self.write_to_stream(str(byte_array_value)) # str is a concatenated byte array =/

	def read_bytearray(self):
		length = self.read_length()
		byte_str = self.read_from_stream(length)
		return bytearray(byte_str)



# include in opposite order of their dependence to prevent MRO confusion
class StringHandlers(
		BytearrayHandler,
		UnicodeHandler, 
		StringHandler, 
	): pass
