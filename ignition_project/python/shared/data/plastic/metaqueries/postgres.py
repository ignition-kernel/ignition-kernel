import textwrap



META_QUERIES = {'postgres': {
	'primaryKeys': textwrap.dedent("""
			-- Query for primary keys for PlasticORM
			with query_params as (
				select PARAM_TOKEN as table_name
					,  PARAM_TOKEN as schema_name
			)
			,	pk_cols as
			(
				select query_params.table_name
					,	query_params.schema_name
					,	pk_cols as ordinal_position
				from pg_catalog.pg_constraint as pgc
					cross join lateral unnest(pgc.conkey) as pk_cols
					cross join query_params
				where pgc.contype  = 'p'
					and pgc.conrelid = concat(query_params.schema_name, '.', query_params.table_name)::REGCLASS	
			)
			select c.column_name,
				case when c.identity_generation is not null
					then 1 else 0 end as autoincrement
			from information_schema.columns as c
				inner join pk_cols
					on pk_cols.ordinal_position = c.ordinal_position
				cross join query_params
			where c.table_name = query_params.table_name
				and c.table_schema = query_params.schema_name
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