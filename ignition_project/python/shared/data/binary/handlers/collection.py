"""
	Binary representations of collections
	
	Unlike the other types, these are all expected to be recursively
	encoded/decoded. The GenericHandler is there just to make sure
	that it's clear inner items will be encoded as they come, 
	resolved as they're seen.
"""

__all__ = [
	'IterableHandler',

	'TupleHandler',
	'ListHandler',
	'SetHandler',
	'FrozensetHandler',
	'DictHandler',

	'CollectionHandlers',
]   



from shared.data.binary.handlers.helper import GenericHandler, LengthHandler



class IterableHandler(GenericHandler, LengthHandler):

	def write_iterable(self, iterable):
		# try to drain as we run
		try:
			self.write_length(iterable)
		# if no len (like an iter() or generator)
		except TypeError:
			# we can only encode materialized things, so for convenience we'll do that now
			self.write_iterable(tuple(iterable))
			return

		# if len worked then write as we iterate (avoiding buffering objects)
		for item in iterable:
			self.write_object(item)

	def read_iterable(self):
		length = self.read_length()
		for _ in range(length):
			yield self.read_object()



class TupleHandler(IterableHandler):

	def write_tuple(self, tup):
		self.write_iterable(tup)

	def read_tuple(self):
		return tuple(self.read_iterable())



class ListHandler(IterableHandler):

	def write_list(self, lst):
		self.write_iterable(lst)

	def read_list(self):
		return list(self.read_iterable())



class SetHandler(IterableHandler):

	def write_set(self, s):
		self.write_iterable(s)

	def read_set(self):
		return set(self.read_iterable())



class FrozensetHandler(IterableHandler):

	def write_frozenset(self, fs):
		self.write_iterable(fs)

	def read_frozenset(self):
		return frozenset(self.read_iterable())



class DictHandler(LengthHandler):

	def write_dict(self, d):
		self.write_length(d)
		for key, value in d.items():
			self.write_object(key)
			self.write_object(value)

	def read_dict(self):
		length = self.read_length()
		return dict((self.read_object(), self.read_object()) for _ in range(length))



class CollectionHandlers(
		DictHandler,
		FrozensetHandler,
		SetHandler,
		ListHandler,
		TupleHandler, 
	): pass
