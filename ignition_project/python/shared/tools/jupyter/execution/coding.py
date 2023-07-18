"""
	Inspect raw code for introspection
	
	The module name is probably bad, but 'inspection' and 'completion' aren't quite right.

"""
logger = shared.tools.jupyter.logging.Logger()



import re


def get_identifier_at_cursor(code_text, cursor_pos):
	"""
	Return the chunk of text in the code that the cursor lays upon.
	"""
	# if we're on the entry of a calling context, return that instead
	if code_text[cursor_pos:-30:-1].strip().startswith('('):
	    cursor_pos -= (1 + code_text[cursor_pos:-30:-1].index('('))
	
	return (
		(	# read left...
			re.findall(r'^((?:\w|[_.])+)', code_text[cursor_pos::-1]) or ['']
		)[0][::-1]
		+ ( # and append the remainder to the right
			re.findall(r'^(\w+|[_]+)', code_text[cursor_pos+1:]) or ['']
		)[0]
	)


def get_object_from_cursor(code_text, cursor_pos, global_scope=None, local_scope=None):
	"""
	Return the object under the cursor given the scopes provided, if any.
	"""
	object_identifier = get_identifier_at_cursor(code_text, cursor_pos)
	
	return get_object_from_identifier(object_identifier, global_scope, local_scope)


def get_object_from_identifier(object_identifier, global_scope=None, local_scope=None, potentially_incomplete_chain=False):
	"""
	Return the object by the given identifier and scopes.
	
	May be a chained identifier, so it could resolve given an attribute chain.
	"""
	if '.' in object_identifier:
		identifier_root, _, identifier_chain = object_identifier.partition('.')
	else:
		identifier_root = object_identifier
		identifier_chain = ''

	try:
		obj_root = (local_scope or {})[identifier_root]
	except KeyError:
		try:
			obj_root = (global_scope or {})[identifier_root]
		except KeyError:
			raise NameError
	
	assert obj_root
	
	if identifier_chain:
		chain_parts = identifier_chain.split('.')
		obj_chained = obj_root
		for part in chain_parts[:-1]:
			obj_chained = getattr(obj_chained, part)
			
		try:
			obj_chained = getattr(obj_chained, chain_parts[-1])
			return obj_chained, ''
		except AttributeError as error:
			if potentially_incomplete_chain:
				return obj_chained, chain_parts[-1]
			else:
				raise error
	else:
		return obj_root, ''


def match_references(object_identifier, global_scope=None, local_scope=None):
	"""
	Return things that might fill out the identifier (if incomplete) given the scopes.
	
	If given a complete identifier, it will provide the next available options
	"""
	try:
		obj_root, unmatched_identifier_remainder = get_object_from_identifier(
									object_identifier, 
									global_scope, local_scope, 
									potentially_incomplete_chain=True)
	except NameError as error: # find closest simple match
		return sorted([
			identifier 
			for identifier 
			in sorted(
				set(global_scope) | set(local_scope)
			)
			if identifier.startswith(object_identifier)
		])
	
	if unmatched_identifier_remainder:
		print unmatched_identifier_remainder
		partial_identifier = unmatched_identifier_remainder
		matched_identifier = object_identifier[:-len(partial_identifier)-1] # skips the final '.' to be added later for clarity
		
		matches = []
		for attribute in sorted(dir(obj_root)):
			# exact match - grab all of the attributes of _that_
			if attribute == partial_identifier:
				for sub_attribute in sorted(dir(getattr(obj_root, attribute))):
					matches.append(matched_identifier + '.' + attribute + '.' + sub_attribute)
			# partial match - add anything that looks like it
			elif attribute.startswith(partial_identifier):
				matches.append(matched_identifier + '.' + attribute)
		return matches
	else:
		matched_identifier = object_identifier
		if object_identifier.endswith('.'):  # make sure no trialing '.'
			matched_identifier = matched_identifier[:-1]
		return sorted([
			matched_identifier + '.' + attribute
			for attribute
			in sorted(dir(obj_root))
		])