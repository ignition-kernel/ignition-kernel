
try:
	from itertools import izip as zip
except ImportError:
	pass

import re

try:
	from com.inductiveautomation.ignition.common import BasicDataset
except ImportError:
	from abc import ABCMeta
	
	class BasicDataset(object):
		__metaclass__ = ABCMeta
		pass
	

class RecordType(object):
	"""Inspired by recipe in Python2 standard library.
	https://docs.python.org/2/library/collections.html#collections.namedtuple

	But doesn't follow the same design for easier overloading.
	"""
	__slots__ = ('_tuple')
	_fields = tuple()
	_sanitizedFields = tuple()
	_lookup = {}

	#_reprString = 'Record(%s)' % (', '.join("'%s'=%%r" % f for f in _fields),)

	def __init__(self, values):
		self._tuple = self._cast(values)
		assert len(self._tuple) == len(self._fields), 'Expected %d args, but got %d' % (len(self._fields), len(self._tuple))
			
	def _asdict(self):
		return dict(zip(self._fields, self))
	
	@classmethod
	def getGetter(cls, field):
		ix = cls._lookup[field]
		return lambda myself, ix=ix: myself._tuple[ix]
	
	@classmethod
	def keys(cls):
		return cls._fields

	@property
	def values(self):
		"""Returns the tuple.
		>>> R = genRecordType('abc')
		>>> R((1,2,3)).values
		(1, 2, 3)
		"""
		return self._tuple

	def _replace(self, **keyValues):
		result = self._cast(map(keyValues.pop, self._fields, self))
		if keyValues: # make sure all got consumed by the map
			raise ValueError('Got unexpected field names: %r' % keyValues.keys())
		self._tuple = result

	def __getitem__(self, key):
		try: # EAFP
			return self._tuple[key]
		except (TypeError,IndexError):
			return self._tuple[self._lookup[key]]

	def __iter__(self):
		"""Redirect to the tuple stored when iterating."""
		return iter(self._tuple)

	def __repr__(self):
		'Format the representation string for better printing'
		return repr(self._asdict())
		#return self._reprString % self._tuple
	
	def __getnewargs__(self):
		'Return self as a plain tuple.  Used by copy and pickle.'
		return tuple(self)

	def __getstate__(self):
		'Exclude the OrderedDict from pickling'
		pass
		

def genRecordType(header):
	"""Returns something like a namedtuple. 
	Designed to have lightweight instances while having many convenient ways
	to access the data.
	"""
	if isinstance(header, BasicDataset):
		rawFields = tuple(h for h in header.getColumnNames())
	else:
		rawFields = tuple(h for h in header)    

	numericFieldPrefix = 'C'
	unsafePattern = re.compile('[^a-zA-Z0-9_]')
	sanitizedFields = [unsafePattern.sub('_', rf) for rf in rawFields]
	for i,field in enumerate(sanitizedFields):
		if field[0].isdigit():
			sanitizedFields[i] = '%s%s' % (numericFieldPrefix, field)

	dupeCheck = set()
	for i,(sf,f) in enumerate(zip(sanitizedFields, rawFields)):
		if sf in dupeCheck:
			n = 1
			while '%s_%d' % (sf,n) in dupeCheck:
				n += 1
			sanitizedFields[i] = '%s_%d' % (sf,n)

		dupeCheck.add(sanitizedFields[i])

	sanitizedFields = tuple(sanitizedFields)

	class Record(RecordType):
		"""Generated to match the data stored."""
		_fields = tuple(rf for rf in rawFields)
		_sanitizedFields = tuple(srf for srf in sanitizedFields)
		_lookup = dict(kv for kv 
					   in zip(rawFields + sanitizedFields, list(range(len(_fields)))*2) )

		_reprString = 'Record(%s)' % (', '.join("%s=%%r" % f for f in sanitizedFields),)

	# monkey patch for higher speed access   
	for ix, key in enumerate(sanitizedFields):
		setattr(Record, key, property(lambda self, ix=ix: self._tuple[ix]))
		
	if len(Record._fields) == 1:
		setattr(Record, '_cast', lambda self,v: (v,))
	else:
		setattr(Record, '_cast', lambda self,v: tuple(v))
		
	return Record