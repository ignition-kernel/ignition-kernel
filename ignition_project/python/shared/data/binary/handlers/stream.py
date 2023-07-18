



class StreamHandler(object):

	def write_to_stream(self, encoded_bytes):
		self.stream.write(encoded_bytes)

	def read_from_stream(self, num_bytes=None):
		read_bytes = self.stream.read(num_bytes)
		
		if num_bytes:
			if len(read_bytes) == 0:
				raise EOFError
			elif len(read_bytes) != num_bytes:
				raise BytesWarning('Stream did not return the expected number of bytes: %d read, %d expected' % (len(read_bytes), num_bytes))
		return read_bytes



class StreamContextManagementHandler(StreamHandler):
	"""Context manager for streaming, open and closed with "with"."""
	
	def _open_stream(self):
		raise NotImplementedError('Each stream type needs to set their own opener')

	def _close_stream(self):
		self.stream.close()

	def __enter__(self):
		assert self.stream is None
		self._open_stream()
		return self
	
	def __exit__(self, exc_type, exc_value, traceback):
		self._close_stream()
		self.stream = None

	# ensure that context is managed if closed
	def write_to_stream(self, obj):
		super(StreamContextManagementHandler, self).write_to_stream(obj)

	def read_from_stream(self, num_bytes=None):
		return super(StreamContextManagementHandler, self).read_from_stream(num_bytes)



class FileStreamHandler(StreamContextManagementHandler):
	"""Context manager for streaming to/from files."""

	def __init__(self, filepath):
		self.filepath = filepath
		self.mode = None
		self.stream = None

	def _open_stream(self):
		self.stream = open(self.filepath, self.mode)

	def file_mode(self, mode):
		self.mode = mode
		return self

	def write_to_stream(self, obj):
		super(FileStreamHandler, self).write_to_stream(obj)

	def read_from_stream(self, num_bytes=None):
		return super(FileStreamHandler, self).read_from_stream(num_bytes)
