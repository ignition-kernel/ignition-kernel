import functools, textwrap



class Template_PlasticORM_Connection(object):
	_engine = None
	_param_token = 'PARAM_TOKEN'
	

	"""Enables mixins to be properly error'd if missing methods."""
	def __init__(self, *args, **kwargs):
		raise NotImplementedError("DB engines should be made as a mixin.")


	def __enter__(self):
		raise NotImplementedError("DB engines should be made as a mixin.")
		return self
	

	def __exit__(self, *args):
		raise NotImplementedError("DB engines should be made as a mixin.")
	

	def _execute_query(self, query, values):
		raise NotImplementedError("DB engines should be made as a mixin.")


	def _execute_insert(self, insertQuery, insertValues):
		raise NotImplementedError("DB engines should be made as a mixin.")


	def _execute_update(self, updateQuery, updateValues):
		raise NotImplementedError("DB engines should be made as a mixin.")


	def primaryKeys(self, schema, table):
		pkQuery = self._get_query_template('primaryKeys')
		return self.query(pkQuery, [table, schema])


	def columnConfig(self, schema, table):
		columnQuery = self._get_query_template('columns')
		return self.query(columnQuery, [table, schema])


	def tableExists(self, schema, table):
		existsQuery = self._get_query_template('tableExists')
		results = self.query(existsQuery, [table, schema])
		return len(list(results.records)) == 1



class PlasticORM_Connection_Base(Template_PlasticORM_Connection):
	"""Helper class for connecting to the database.
	Replace and override as needed.
	"""
	__meta_queries__ = shared.data.plastic.metaqueries.base.META_QUERIES
	
	_engine = ''
	_param_token = 'PARAM_TOKEN'
	_keep_alive = True
	connection = None


	# def dumpCore(function):
	#     @functools.wraps(function)
	#     def handle_error(self,*args,**kwargs):
	#         try:
	#             return function(self,*args,**kwargs)
	#         except Exception as error:
	#             print ('DB Error: ', str(error))
	#             if args:
	#                 print ('Arguments: ', args)
	#             if kwargs:
	#                 print ('Key word arguments: ', kwargs)
	#             raise error
	#     return handle_error
	

	def _get_query_template(self, queryType):
		qt = self.__meta_queries__[self._engine].get(queryType) or self.__meta_queries__[None][queryType]
		return qt.replace('PARAM_TOKEN',self._param_token)
	

	# @dumpCore
	def query(self,query,params=[]):
		query = query.replace('PARAM_TOKEN', self._param_token)
		return self._execute_query(query,params)


	def queryOne(self,query,params=[]):
		return self.query(query,params)[0]


	# @dumpCore
	def insert(self, table, columns, values):
		insertQuery = self._get_query_template('insert')
		insertQuery %= (table, 
						','.join(columns), 
						','.join([self._param_token]*len(values)))
		
		insertQuery = insertQuery.replace('PARAM_TOKEN', self._param_token)
		return self._execute_insert(insertQuery,values)
	
	
	# @dumpCore
	def update(self, table, setDict, keyDict):
		setColumns,setValues = zip(*sorted(setDict.items()))
		keyColumns,keyValues = zip(*sorted(keyDict.items()))
		
		updateQuery = self._get_query_template('update')
		updateQuery %= (table, 
						','.join('%s=%s' % (setColumn, self._param_token)
								 for setColumn 
								 in setColumns), 
						'\n\t and '.join('%s=%s' % (keyColumn, self._param_token)
										 for keyColumn 
										 in keyColumns))
		
		updateQuery = updateQuery.replace('PARAM_TOKEN', self._param_token)
		self._execute_update(updateQuery, setValues+keyValues)