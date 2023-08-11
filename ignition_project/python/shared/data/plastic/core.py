import functools


from shared.data.plastic.meta import MetaPlasticORM
from shared.data.plastic.connectors.base import PlasticORM_Connection_Base
from shared.data.plastic.column import PlasticColumn


class PlasticORM_Base(object):
	"""Base class that connects a derived class to the database.

	When declaring the subclass, set the defaults in it directly 
	  to avoid the overhead of auto-configuring.

	NOTE: If no columns are configured, the class will attempt to autoconfigure
	  regardless of whether _autoconfigure is set.
	"""
	__metaclass__ = MetaPlasticORM
	
	# set defaults for derived classes here
	
	# By default this is a nop. Be sure to set this is the 
	#   engine-specific derived class
	_connectionType = PlasticORM_Connection_Base
	_connection = None
	_dbInfo = None

	# Set _autocommit to True to have changes to the instaces immediately applied
	_autocommit = False
	
	# Set _autoconfigure to True to force the class to reconfigure every time
	# NOTE: if there are no columns or PKs defined, auto-configure runs regardless
	_autoconfigure = False

	# Configure these to avoid auto-configure overhead
	_columns = tuple()
	_primary_key_cols = tuple()
	_primary_key_auto = tuple()
	_not_nullable_cols = tuple()
	
	# If the _table is blank, the class name will be used instead.
	_table = ''

	# Be sure to set the _schema. This is does not default!
	_schema = None
	
	# Holding list for queuing the changes that need to be applied
	_pending = []

	def _delayAutocommit(function):
		"""During some internal housekeeping, it's handy to prevent Plastic to trying to
		apply changes part-way through.
		"""
		@functools.wraps(function)
		def resumeAfter(self, *args, **kwargs):
			try:
				bufferAutocommit = self._autocommit
				self._autocommit = False
				return function(self, *args, **kwargs)
			except Exception as err:
				raise
			finally:
				self._autocommit = bufferAutocommit
				
		return resumeAfter
	
		
	@_delayAutocommit
	def __init__(self, *args, **kwargs):
		"""Initialize the object's instance with the given values.

		Arguments are assumed to map directly in order to the columns.
		Key word arguments are applied over the arguments, if there's overlap.

		If key columns are given, then pull the rest unconfigured.

		Include the keyword arguement bypass_validation = True
		  to accept the values 
		"""
		# default value
		bypass_validation = kwargs.pop('bypass_validation', False)
		
		self._pending = [] # override class object to ensure changes are local
		
		values = dict((col,val) for col,val in zip(self._columns,args))
		values.update(kwargs)
		
		# Take whatever yer given and like it
		if bypass_validation:
			for column,value in values.items():
				setattr(self, column, value)

			self._pending = []
		else:
			# Check if the keys are given, if so get all the values for that record
			if all(key in values for key in self._primary_key_cols):
				self._retrieveSelf(**values)
			
			#... but then immediately override with the values provided
			for column,value in values.items():
				if getattr(self, column) != value:
					setattr(self, column, value)
	

	def __setattr__(self, attribute, value):
		"""Do the autocommit bookkeeping, if needed"""
		# Set columns as pending changes
		currentValue = getattr(self, attribute)
		if attribute in self._columns and currentValue != value:            
			self._pending.append(attribute)
		
		super(PlasticORM_Base,self).__setattr__(attribute, value)
		
		# Note that this means setting _autocommit to True will
		#  IMMEDIATELY commit any pending changes!  
		if self._autocommit and self._pending:
			self._commit()


	@property
	def _autoKeyColumns(self):
		"""Helper function for getting the key set"""
		return set(pkcol 
				   for pkcol,auto
				   in zip(self._primary_key_cols, self._primary_key_auto)
				   if auto)
	

	@property
	def _nonAutoKeyColumns(self):
		"""Helper function for getting the non-autoincrement functions"""
		return set(pkcol 
				   for pkcol,auto
				   in zip(self._primary_key_cols, self._primary_key_auto)
				   if not auto)
	

	@property
	def _nonKeyColumns(self):
		"""Helper function for getting the non-PK columns"""
		return set(self._columns).difference(self._primary_key_cols)


	@classmethod
#	@_delayAutocommit
	def find(cls, *filters):
		"""Return a list of instances for all the records that match the filters.

		The filters args is most easily generated as a sequence of PlasticColumn slices.
		  PlasticColumn slicing returns a tuple of filter string and values to apply.
		  Importantly, the values are applied as parameters.

		Filters can be applied by slicing a PlasticColumn.
		  For example, to get records on a table with an ID column...
		  ... between 4 and 10 (inclusive),
			Table.find(Table.ID[4:10])
		  ... less than 5 (exclusive)
			Table.find(Table.ID[:5])
		  ... greater than 12
			Table.find(Table.ID[12:])
		  ... Column3 equals 'asdf'
			Table.find(Table.Column3['asdf'])
		  ... ID is 3,4, or 7
			Table.find(Table.ID[3,4,7])
		  ... ColumnA is the same as ColumnB 
			  (this is... unlikely to be used, but it works as a consequence of the design)
			Table.find(Table.ColumnA[Table.ColumnB])

		NOTE: The slicing is NOT exactly the same semantically to normal list slicing.
		  This is to simplify and be easier to analogue to SQL
		"""
		# Split out the filter strings to use in the where clause
		#   and the values that are needed to be passed in as parameters
		filters,values = zip(*filters)
		values = [value 
				  for conditionValues in values
				  for value in conditionValues]
		
		with cls._connection as plasticDB:
			# Build the query string (as defined by the engine configured)
			recordsQuery = plasticDB._get_query_template('basic_filtered')
			recordsQuery %= (
				','.join(cls._columns),
				cls._table,
				'\n\t and '.join(condition for condition in filters)
				)
			
			records = plasticDB.query(recordsQuery, values)
		
		# Render the results into a list 
		objects = []
		for record in records:
			initDict = record._asdict()
			initDict['bypass_validation'] = True
			objects.append(cls(**initDict))

		return objects
		
		
	@_delayAutocommit
	def _retrieveSelf(self, **primaryKeyValues):
		"""Automatically fill in the column values for given PK record."""
		# primaryKeyValues is a dict with a value for each PK
		if primaryKeyValues:
			keyDict = dict((key,primaryKeyValues[key]) 
						   for key 
						   in self._primary_key_cols)
		else:
			keyDict = dict((key,getattr(self,key)) 
						   for key 
						   in self._primary_key_cols)

		# Assert that all PKs are set
		if any(value is None or isinstance(value, PlasticColumn)
			   for value 
			   in keyDict.values()):
			raise ValueError('Can not retrieve record missing key values: %s' % 
							 ','.join(col 
									  for col 
									  in keyDict 
									  if keyDict[key] is None))
		
		# Query for associated record
		with self._connection as plasticDB:
			
			keyColumns,keyValues = zip(*sorted(keyDict.items()))

			recordQuery = plasticDB._get_query_template('basic_filtered')
			recordQuery %= (
				','.join(sorted(self._nonKeyColumns)),
				self._table,
				','.join('%s = PARAM_TOKEN' % keyColumn 
						 for keyColumn 
						 in sorted(keyColumns)))

			entry = plasticDB.queryOne(recordQuery, keyValues)

			# apply retrieved values to the object
			for column in self._nonKeyColumns:
				setattr(self, column, entry[column])
			# slightly redundant, but meaningful for initialization
			for column,keyValue in keyDict.items():
				setattr(self, column, keyValue)

		# Clear the pending buffer, since we just retrieved    
		self._pending = []

	
	def _insert(self):
		"""Insert the current object's values as a new record.
		Can't insert if we're missing non-null or non-auto key columns
		(Darn well shouldn't have a nullable key column, but compound keys
		  can get silly.)
		"""
		# Don't attempt to insert if there aren't enough pending column values set
		#   to cover the required non-NULL columns (excluding auto key columns, since they, well, auto)
		if set(self._not_nullable_cols).union(self._nonAutoKeyColumns).difference(self._pending):
			return
		
		# Don't insert the auto columns
		if any(self._primary_key_auto):
			columns = sorted(set(self._pending).difference(self._autoKeyColumns))
		else:
			columns = self._pending
		
		# Collect the values from the object
		values = [getattr(self,column) for column in columns]
		
		# Delegate the insert to the engine and apply
		with self._connection as plasticDB:
			rowID = plasticDB.insert(self._table, columns, values)
			# I can't think of a case where there's more than one autocolumn, but /shrug
			# they're already iterables, so I'm just going to hit it with zip
			for column in self._autoKeyColumns:
				setattr(self,column,rowID)
		
		# Clear the pending buffer, since we just sync'd
		self._pending = []
		
		
	def _update(self):
		"""Update the current object's record with the changed (pending) values.
		This will also do some minor validation to make sure it's compliant.
		"""
		# Don't update a column to null when it shouldn't be
		for column in set(self._not_nullable_cols).intersection(self._pending):
			if getattr(self, column) is None:
				raise ValueError('Can not null column %s in table %s.%s' % (column, self._schema, self._table))

		setValues = dict((column,getattr(self,column))
					  for column 
					  in self._pending)
		
		keyValues = dict((keyColumn,getattr(self,keyColumn))
						 for keyColumn
						 in self._primary_key_cols)
		
		# Delegate the update to the engine and apply
		with self._connection as plasticDB:            
			plasticDB.update(self._table, setValues, keyValues)
		
		# Clear the pending buffer, since we just sync'd
		self._pending = []

		
	def _upsert(self):
		"""Attempt to decide if an update or insert is called for.
		"""
		
		values = {}
		for column in self._pending:
			value = getattr(self, column)
				
			# Don't upload unset values...
			if isinstance(value, PlasticColumn):
				continue
					
			values[column] = value
					
		pkValues = {}
		for pkColumn in self._primary_key_cols:
			pkValues[pkColumn] = values.get(pkColumn, getattr(self,pkColumn))
		
		# We need to do a specialized delay autocommit so we can safely attempt this.
		bufferAutocommit = self._autocommit
		
		# Check if the keys are given, if so get all the values for that record
		try:
			super(PlasticORM_Base,self).__setattr__('_autocommit', False)
		
			# If this fails, it'll throw an IndexError from the record set being empty
			self._retrieveSelf(**pkValues)
		
			#... but then immediately override with the values provided
			for column,value in values.items():
				if getattr(self, column) != value and not column in self._primary_key_cols:
					setattr(self, column, value)
			
			# Did we apply a new value that's not a PK and new? Then update!
			if self._pending:
				self._update()
			
		# if all else fails, then we should insert
		except IndexError:            
			self._insert()
			
		finally:
			# We have to bypass the normal trigger here, or the system
			# will attempt to do this all _again_. This is pretty exceptional,
			# since we're manually implementing an upsert and essentially
			# bouncing off exceptions and settings as rails.
			# HONK.
			super(PlasticORM_Base,self).__setattr__('_autocommit', bufferAutocommit)

		
	def _commit(self):
		"""Apply the changes, if any."""
		if not self._pending:
			return

		# Verify we have enough to insert
		# Ensure that the primary keys are at least set
		# NOTE: if PKs are set under autocommit conditions, 
		#   the engine will try to retrieve.
		# We'll do the same here, with the caveat that we'll update
		
		# So: are we switching to another record? If so pull and update!
		if set(self._pending) & set(self._primary_key_cols):            
			self._upsert()
		else:
			self._update()
			
			
	def __repr__(self):
		return '<%s (\n\t  %s)>' % (self._table, '\n\t, '.join('%s = %s' % (col,repr(getattr(self,col)))
												 for col
												 in self._columns))