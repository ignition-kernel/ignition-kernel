import pymysql
# try:
#     import mysql.connector as mysql_connector
# except ImportError:
#     import pymysql as mysql_connector

import textwrap

from shared.data.plastic.recordset import RecordSet
from shared.data.plastic.connectors.base import PlasticORM_Connection_Base
from shared.data.plastic.core import PlasticORM_Base



class Mysql_Connector(PlasticORM_Connection_Base):
	
	__meta_queries__ = shared.data.plastic.metaqueries.mysql.META_QUERIES

	_engine = 'mysql'
	_param_token = '%s'
	_keep_alive = True
	connection = None


	def __init__(self, configDict):
		self.config = configDict
		if self._keep_alive:
			self.connect()
		else:
			self.connection = None
	

	def connect(self, forceReconnect=False):
		if self.connection and forceReconnect:
			self.connection.close()
			self.connection = None

		if self.connection is None:
			self.connection = pymysql.connect(**self.config)


	def __enter__(self):
		self.connect()
		return self
	

	def __exit__(self, *args):
		if not self.connection == None:
			# Commit changes before closing
			if not self.connection.autocommit:
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
			rs = RecordSet(initialData=cursor.fetchall(), recordType=next(zip(*cursor.description)))
		return rs    
	

	def _execute_insert(self, insertQuery, insertValues):
		"""Execute an insert query. Returns an integer for the row inserted."""
		with self as plasticDB:
			cursor = plasticDB.connection.cursor()
			cursor.execute(insertQuery,insertValues)
			return cursor.lastrowid
		

	def _execute_update(self, updateQuery, updateValues):
		"""Execute an updated query. Returns nothing."""
		with self as plasticDB:
			cursor = plasticDB.connection.cursor()
			cursor.execute(updateQuery,updateValues)


class PlasticMysql(PlasticORM_Base):
	_connectionType = Mysql_Connector

	_schema = 'plastic_test'
	_dbInfo = dict(
		host='mysql8-test.corso.systems',
		port=30306,
		db='plastic_test',
		user='root',
		password='**********',
	)

	pass