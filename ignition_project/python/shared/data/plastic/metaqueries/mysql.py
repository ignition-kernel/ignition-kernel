import textwrap



META_QUERIES = {'mysql': {
	'primaryKeys': textwrap.dedent("""
			-- Query for primary keys for PlasticORM
			select c.COLUMN_NAME
			,   case when c.extra like '%%auto_increment%%' 
						then 1
					else 0
				end as autoincrements
			from information_schema.columns as c
			where lower(c.table_name) = lower(PARAM_TOKEN)
				and c.column_key = 'PRI'
				and lower(c.table_schema) = lower(PARAM_TOKEN)
			order by c.ordinal_position
			"""),
	'columns': textwrap.dedent("""
			-- Query for column names for PlasticORM 
			select c.COLUMN_NAME,
				case when c.IS_NULLABLE = 'NO' then 0
					else 1
				end as IS_NULLABLE
			from information_schema.columns as c
			where c.table_name = PARAM_TOKEN
				and c.table_schema = PARAM_TOKEN
			order by c.ordinal_position
			"""),
	'tableExists': textwrap.dedent("""
			-- Query for if a table exists
			select table_name
			from information_schema.tables
			where table_name = PARAM_TOKEN and table_schema = PARAM_TOKEN
			"""),	
}	}