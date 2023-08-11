import sqlite3

import textwrap

from shared.data.plastic.recordset import RecordSet
from shared.data.plastic.connectors.base import META_QUERIES, PlasticORM_Connection_Base
from shared.data.plastic.core import PlasticORM_Base



class Sqlite_Connector(PlasticORM_Connection_Base):
	__meta_queries__ = shared.data.plastic.metaqueries.sqlite.META_QUERIES

	_engine = 'sqlite'
	_param_token = '?'
	_keep_alive = True
	connection = None
	
	
	def __init__(self, dbFile=':memory:'):
		self.config = dbFile
		if self._keep_alive:
			self.connect()
		else:
			self.connection = None    


	def connect(self, forceReconnect=False):
		if self.connection and forceReconnect:
			self.connection.close()
			self.connection = None

		if self.connection is None:
			self.connection = sqlite3.connect(self.config)


	def __enter__(self):
		self.connect()
		return self
	

	def __exit__(self, *args):
		if not self.connection == None:
			# Commit changes before closing (sqlite doesn't autocommit)
			self.connection.commit()
			if not self._keep_alive:
				self.connection.close()
				self.connection = None
	

	# Override these depending on the DB engine
	def _execute_query(self, query, values):
		"""Execute a query. Returns rows of data."""
		with self as plasticDB:
			cursor = plasticDB.connection.cursor()
			cursor.execute(query,values)
			if not cursor.description:
				return []
			rs = RecordSet(initialData=cursor.fetchall(), recordType=next(zip(*cursor.description)))
		return rs    
	

	def _execute_insert(self, insertQuery, insertValues):
		"""Execute an insert query. Returns an integer for the row inserted."""
		with self as plasticDB:
			cursor = plasticDB.connection.cursor()
			cursor.execute(insertQuery, insertValues)
			return cursor.lastrowid
		

	def _execute_update(self, updateQuery, updateValues):
		"""Execute an updated query. Returns nothing."""
		with self as plasticDB:
			cursor = plasticDB.connection.cursor()
			cursor.execute(updateQuery, updateValues)


	# SQLite retrieves these a bit differently...
	def primaryKeys(self, schema, table):
		"""PK and autoincrement"""
		pkQuery = self._get_query_template('primaryKeys')
		pkQuery = pkQuery.replace('?', table) # can't var a pragma...
		results = self.query(pkQuery, [])
		pkCols = []
		for row in results:
			if row['pk']:                  # sqlite autoincrements int primary keys
				pkCols.append( (row['name'], 1 if row['type'].lower() == 'integer' else 0) )
		return RecordSet(initialData=pkCols, recordType=('COLUMN_NAME', 'autoincrements'))


	def columnConfig(self, schema, table):
		columnQuery = self._get_query_template('columns')
		columnQuery = columnQuery.replace('?', table) # can't var a pragma...
		results = self.query(columnQuery, [])
		cols = []
		for row in results:
			cols.append( (row['name'], not row['notnull']) )
		return RecordSet(initialData=cols, recordType=('COLUMN_NAME', 'IS_NULLABLE'))


class PlasticSqlite(PlasticORM_Base):
	_connectionType = Sqlite_Connector

	_dbInfo = ':memory:'

	pass