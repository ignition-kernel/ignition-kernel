import textwrap



META_QUERIES = {None: {
	'insert': textwrap.dedent("""
		-- Insert from PlasticORM_Connection
		insert into %s
			(%s)
		values
			(%s)
		"""),
	'update': textwrap.dedent("""
		-- Update from PlasticORM_Connection
		update %s
		set %s
		where %s
		"""),
	'basic_filtered': textwrap.dedent("""
		-- A Basic filter query for PlasticORM
		select %s
		from %s
		where %s
		"""),
}	}