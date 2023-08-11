

from shared.data.plastic.recordset import RecordSet
from shared.data.plastic.connectors.base import PlasticORM_Connection_Base
from shared.data.plastic.core import PlasticORM_Base


META_QUERIES = {
	'ignition': {},
}

ENGINES = [
	'base', 'mysql', 'postgres', 'sqlite'
]

def autopopulate_metaqueries(META_QUERIES=META_QUERIES, ENGINES=ENGINES):
	for engine in ENGINES:
		try:
			META_QUERIES.update(
				shared.data.plastic.metaqueries.getDict()[engine].META_QUERIES
			)
		except Exception as error:
			raise error

autopopulate_metaqueries()




def isIgnition():
	try:
		_ = getattr(system, 'db')
		return True
	except:
		return False


class Ignition_Connector(PlasticORM_Connection_Base):
	__meta_queries__ = META_QUERIES
	
	_engine = None
	_param_token = '?'
	
	
	def __init__(self, dbName):
		self.dbName = dbName
		self._engine = system.db.getConnectionInfo(self.dbName).getValueAt(0,'DBType').lower()
		self.tx = None
		

	def __enter__(self):
		if self.tx == None:
			self.tx = system.db.beginTransaction(self.dbName)
		return self
	

	def __exit__(self, *args):
		if self.tx:
			system.db.commitTransaction(self.tx)
			system.db.closeTransaction(self.tx)
			self.tx = None
			

	def _execute_query(self, query, values):
		if self.tx:
			return RecordSet(initialData=system.db.runPrepQuery(query, values, self.dbName, self.tx))
		else:
			return RecordSet(initialData=system.db.runPrepQuery(query, values, self.dbName))
	

	def _execute_insert(self, insertQuery, insertValues):
		if self.tx:
			return system.db.runPrepUpdate(insertQuery, insertValues, self.dbName, self.tx, getKey=1)
		else:
			return system.db.runPrepUpdate(insertQuery, insertValues, self.dbName, getKey=1)


	def _execute_update(self, updateQuery, updateValues):
		if self.tx:
			system.db.runPrepUpdate(updateQuery, updateValues, self.dbName, self.tx, getKey=0)
		else:
			system.db.runPrepUpdate(updateQuery, updateValues, self.dbName, getKey=0)


class PlasticIgnition(PlasticORM_Base):
	_connectionType = Ignition_Connector
	
	_dbInfo = None

	pass



def connect_table(db, schema, table, autocommit=False):
	return type(table, (PlasticIgnition,), {
			'_dbInfo': db,
			'_schema': schema,
			'_table': table,
			'_autocommit': autocommit,
		})