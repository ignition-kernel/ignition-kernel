"""
	Esoteric types
	
	Poorly named module, but this is the catch-all for the weird
	types that aren't used much or don't behave like the others.
"""

__all__ = [
	'NoneHandler',
	'SliceHandler',
	'FileHandler',

	'EsotericHandlers',
]   



class NoneHandler(object):

	def write_none(self, nil):
		pass

	def read_none(self):
		return None



class SliceHandler(object):

	def write_slice(self, s):
		self.write_object(s.start)
		self.write_object(s.stop)
		self.write_object(s.step)

	def read_slice(self):
		return slice(
			start=self.read_object(), 
			stop=self.read_object(), 
			step=self.read_object()
		)



class FileHandler(object):
	# note that this saves the _state_ of the file HANDLE, not the contents!

	def write_file(self, f):
		self.write_object(f.name)
		self.write_object(f.mode)
		try:
			position = f.tell()
		except:
			position = None
		self.write_object(position)

	def read_file(self):
		f = open(self.read_object(), mode=self.read_object())
		position = self.read_object()
		if position:
			f.seek(position)




class EsotericHandlers(
		NoneHandler,
		SliceHandler,
		FileHandler,
	): pass
