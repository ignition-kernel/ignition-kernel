import textwrap



META_QUERIES = {'sqlite': {
	'primaryKeys': textwrap.dedent("""
			-- Query for primary keys for PlasticORM using SQLite3
			-- NOTE: requires additional processing!
			PRAGMA table_info(PARAM_TOKEN)
			"""),
	'columns': textwrap.dedent("""
			-- Query for column names for PlasticORM using SQLite3
			-- NOTE: requires additional processing!
			PRAGMA table_info(PARAM_TOKEN)
			"""),
	'tableExists': textwrap.dedent("""
			-- Query for column names for PlasticORM using SQLite3
			SELECT name 
			FROM sqlite_master 
			WHERE type='table' 
				AND name=PARAM_TOKEN
			"""),
	}	}

