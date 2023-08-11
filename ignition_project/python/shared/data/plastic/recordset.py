from shared.data.plastic.record import RecordType, genRecordType

import functools, math

try:
	from itertools import izip as zip
except ImportError:
	pass
from itertools import islice

from weakref import WeakSet

try:
	from com.inductiveautomation.ignition.common import BasicDataset
	from com.inductiveautomation.ignition.common.script.builtin.DatasetUtilities import PyDataSet
except ImportError:
	from abc import ABCMeta
	
	class BasicDataset(object):
		__metaclass__ = ABCMeta
		pass
	
	class PyDataSet(object):
		__metaclass__ = ABCMeta
		pass


class RecordSetColumn(object):
	__slots__ = ('_source', '_index')
	
	def __init__(self, recordSet, columnIndex):
		self._source = recordSet
		self._index = columnIndex

	def __iter__(self):
		"""Redirect to the tuple stored when iterating."""
		return ((record._tuple[self._index]
				  for record 
				  in group)
				for group in self._source._groups)
	
	def __getitem__(self, selector):
		"""Returns a group or a slice of groups, where the selected column's value in the record is returned.
		"""
		if isinstance(selector, slice):
			if selector.step:
				raise NotImplementedError("Columns should not be sliced by steps. Window the RecordSet and group records instead.")
			
			return ((record._tuple[self._index]
					  for record
					  in group )
					for group 
					in islice(self._source._groups, selector.start, selector.stop) )
		else:
			return (record._tuple[self._index]
					  for record
					  in self._source._groups[selector] )

	def __repr__(self):
		'Format the representation string for better printing'
		return 'RecordSetColumn("%s" at %d)' % (self._source._RecordType._fields[self._index], self._index)

		

class RecordSet(object):
	"""Holds groups of records. The gindex is the label for each of the tuples of Records.
	
	Based on collections.MutableSequence
	"""
	# Track all the RecordSets that get made. We can use this to automagically trim the cache.
	# References need to be weak to ensure garbage collection can continue like normal.
	_instances = WeakSet()

	__slots__ = ('__weakref__', '_RecordType', '_groups', '_columns')


	def __new__(cls, initialData=None,  recordType=None, initialLabel=None, validate=False, *args, **kwargs):
		"""See https://stackoverflow.com/a/12102666/1943640 for an example of this."""
		instance = super(RecordSet, cls).__new__(cls, *args, **kwargs)
		cls._instances.add(instance)
		return instance

	@classmethod
	def _truncateAll(cls):
		instances = list(cls._instances)
		for instance in instances:
			instance.truncate()

	def truncate(self):
		"""Clear out data that is not unused.
		   Cooperate with the scanners pointing to this RecordSet
			 by asking for a tuple declaring what records or groups
			 it needs.
		   Only groups are truncated, and only from the beginning.
		   Once completed, each listening scanner is notified
			 so its cursors can be corrected accordingly.
		"""
		raise NotImplementedError

		safeGroupIx = -1
		for scanner in listeningScanners:
			pass

		for scanner in listeningScanners:
			scanner.updateCursorsForRemoval(safeGroupIx)


	# INIT
	def _initializeDataSet(self, dataset, validate=False):
		"""Convert the DataSet type into a RecordSet
		"""
		self._RecordType = genRecordType(dataset.getColumnNames())
		columnIxs = range(len(self._RecordType._fields))
		records = []
		for rix in range(dataset.getRowCount()):
			row = tuple(dataset.getValueAt(rix, cix) for cix in columnIxs)
			records.append(self._RecordType(row))
		self._groups = [tuple(records)]
	
	def _initializePyDataSet(self, pydataset, validate=False):
		"""Convert the DataSet type into a RecordSet
		"""
		self._RecordType = genRecordType(pydataset.getColumnNames())
		columnIxs = range(len(self._RecordType._fields))
		records = []
		for row in pydataset:
			records.append(self._RecordType(row))
		self._groups = [tuple(records)]
	
	def _initializeEmpty(self, RecordType):
		"""Simply define what kind of RecordSet this will be, but start with no data.
		"""
		self._RecordType = RecordType
		self._groups = []
	
	def _initializeRaw(self, RecordType, data):
		"""Make a list with a single tuple entry, that was the list of new records.
		   Using a generator as the tuple argument is about 4-10x slower.
		"""
		self._RecordType = RecordType
		self._groups = [tuple([RecordType(record) 
							   for record 
							   in data])]
	
	def _initializeRecords(self, records, validate=False):
		"""Initialize RecordSet from the records provided.
		Optionally validate the list to ensure they're all the same kind of record.
		"""
		assert len(records) > 0, """If only records are provided, an example entry must be included: `len(records) == 0`"""
		self._RecordType = type(records[0])
		if validate:
			assert all(isinstance(r, RecordType) for r in records), 'All entries were not the same RecordType'
		self._groups = [tuple(records)]

	def _initializeCopy(self, recordSet):
		self._RecordType = recordSet._RecordType
		self._groups = [group for group in recordSet._groups]
		# Note that it'll regenerate indexes even on copy...
		
	
	def __init__(self, initialData=None,  recordType=None, initialLabel=None, validate=False, *args, **kwargs):#, indexingFunction=None):        
		"""When creating a new RecordSet, the key is to provide an unambiguous RecordType,
			 or at least enough information to define one.
		"""
		# Initialize mixins
		super(RecordSet, self).__init__(*args, **kwargs)
		
		# We can initialize with a record type, a record, or an iterable of records
		# First check if it's a DataSet object. If so, convert it.
		if isinstance(initialData, BasicDataset):
			self._initializeDataSet(initialData)
		elif isinstance(initialData, PyDataSet):
			self._initializePyDataSet(initialData)
		elif recordType:
			# create a RecordType, if needed
			if not (isinstance(recordType, type) and issubclass(recordType, RecordType)):
				recordType = genRecordType(recordType)
			if initialData:
				self._initializeRaw(recordType, initialData)
			else:
				self._initializeEmpty(recordType)
		elif initialData:
			if isinstance(initialData, RecordSet):
				self._initializeCopy(initialData)
			else:
				self._initializeRecords(initialData, validate)
		else:
			raise ValueError("""Insufficient information to initialize the RecordSet."""
							 """ A RecordType must be implied by the constructor arguments.""")
				
		# monkey patch for higher speed access
		self._columns = tuple(RecordSetColumn(self, ix) 
							  for ix 
							  in range(len(self._RecordType._fields)))
			
			
	def clear(self):
		self._groups = []
		
		
	def column(self,column):
		return self._columns[self._RecordType._lookup[column]]

	
	def coerceRecordType(self, record):
		return self._RecordType(record)

	# Sized
	def __len__(self):
		"""Not terribly useful - this only tells how many chunks there are in the RecordSet.
		   Use this as a poor man's fast cardinality check against other RecordSets.
		"""
		return len(self._groups)
	
	def __nonzero__(self):
		for group in self._groups:
			if group:
				return True
		else:
			return False
	
	# Iterable 
	# Sequence
	
	def __getitem__(self, selector):
		"""Get a particular set of records given the selector.
		   Note that this is record-centric, like the iterator.
		"""
		if isinstance(selector, tuple):
			column,slicer = selector
			return self.column(column)[slicer]
		elif isinstance(selector, slice):
			return islice(self.records, selector)     
		elif isinstance(selector, int):
			index = selector
			for group in self._groups:
				if len(group) > index:
					return group[index]
				index -= len(group)
			else:
				raise IndexError("There are not enough records in the groups to meet the index %d" % index)
		else:
			raise NotImplementedError("The selector '%r' is not implemented" % selector)
			#return self._groups[selector]
	
	@property
	def groups(self):
		return (group 
				for group 
				in self._groups)
	
	@property
	def records(self):
		return (record 
				for group in self._groups 
				for record in group)
	
	def __iter__(self):
		return self.records
		#return (recordGroup for recordGroup in self._groups)

	# Container
	def __contains__(self, search):
		"""Search from the start for the search object.
		   If a record is provided, then the groups will themselves be 
			 exhaustively searched.
		"""
		if isinstance(search, self._RecordType):
			for group in self._groups:
				if search in group:
					return True
		elif search in self._groups:
			return True
		return False

	def __reversed__(self):
		"""Reverses BOTH the groups and the records in the groups.
		   Pure generators are returned.
		"""
		return (reversed(group) for group in reversed(self._groups))
				
	def index(self, search, fromTop=True):
		"""Returns the index of the group the search item is found in."""
		if fromTop:
			iterDir = (gg for gg in reversed(enumerate(self._groups)))
		else:
			iterDir = (gg for gg in enumerate(self._groups))
			
		if isinstance(search, self._RecordType):
			for gix, group in iterDir:
				if record in group:
					return gix
		elif isinstance(search, tuple):
			for gix, group in iterDir:
				if search == group:
					return gix
				for record in group:
					if record._tuple == search:
						return gix
		raise ValueError('Search item %r was not found' % search)

	def count(self, search):
		"""Returns the number of times the search item is found.
		   Note that this tests for equivalency, not instantiation!
		"""
		if isinstance(search, self._RecordType):
			return sum(1
					   for group in self._groups
					   for record in group
					   if record == search )
		elif isinstance(search, tuple):
			return sum(1 for group in self._groups if search == group)
		return 0

	def append(self, addition):
		"""Append the group of records to the end of _groups.
		   If a record is given, an group of one will be appended.
		"""
		if isinstance(addition, RecordSet):
			self.extend(addition)
		else:
			if isinstance(addition, self._RecordType):
				newGroup = (self.coerceRecordType(addition),)
			else: 
				# tuple creation is slightly faster if the generator is consumed by a list first
				newGroup = tuple([self.coerceRecordType(entry)
								  for entry
								  in addition ])
			self._groups.append(newGroup)
			self.notify(None, -1)
	
	def extend(self, additionalGroups):
		"""Extend the records by concatenating the record groups of another RecordSet.
		"""
		if isinstance(additionalGroups, RecordSet):
			assert self._RecordType._fields == additionalGroups._RecordType._fields, 'RecordSets can only be extended by other RecordSets of the same RecordType.'
			self._groups.extend(additionalGroups._groups)
			self.notify(None, slice(-len(additionalGroups),None))
		else:
			for group in additionalGroups:
				self.append(group)
	
	def __iadd__(self, addition):
		"""Overload the shorthand += for convenience."""
		if isinstance(addition, self._RecordType):
			self.append(addition)
		else:
			self.extend(addition)
		return self
	
	def _graph_attributes(self):
		fields = ', '.join(self._RecordType._fields)
		label = 'RecordSet\n%s' % fields
		return {
			'label': label,
			'shape': 'cylinder',
		}
	
	def __str__(self):
		return 'RecordSet=%r' % repr(self._RecordType._fields)
			   
	def __repr__(self, elideLimit=20):
		'Format the representation string for better printing'
		records = list(islice((r for r in self.records), elideLimit))
		totalRecordCount = sum(len(g) for g in self.groups)
		out = ['RecordSet with %d groups of %d records' % (len(self), totalRecordCount)]
		# preprocess
		maxWidths = [max([len(f)] + [len(repr(v))+1 for v in column]) 
					 for f,column 
					 in zip(self._RecordType._fields,
							zip(*records) 
							   if records 
							   else ['']*len(self._RecordType._fields))]
		digits = math.floor(math.log10(elideLimit or 1)) + 1
		maxGixWidth = math.floor(math.log10(len(self._groups) or 1)) + 1
		prefixPattern = ' %%%ds  %%%ds |' % (maxGixWidth, digits)
		recordPattern = prefixPattern + ''.join(' %%%ds' % mw for mw in maxWidths)
		out += [recordPattern % tuple(['',''] + list(self._RecordType._fields))]
		out += [recordPattern % tuple(['',''] + ['-'*len(field) for field in self._RecordType._fields])]
		
		remaining = elideLimit
		for gix,group in enumerate(self._groups):
			for j,record in enumerate(group):
				out += [recordPattern % tuple(['' if j else gix,j] + [repr(v) for v in record])]
				remaining -= 1
				if not remaining:
					break
			if not remaining:
				break
		if totalRecordCount > elideLimit:
			out += ['  ... and %d elided' % (totalRecordCount - elideLimit)]   
		out += ['']
		return '\n'.join(out)