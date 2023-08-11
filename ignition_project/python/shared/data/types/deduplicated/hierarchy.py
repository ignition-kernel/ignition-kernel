"""
	Helpers to store, encode, and compare hierarchies.
	
"""
import re



def follow(thing, next_function, test=lambda x:bool(x)):
	"""Helper to iterate down what is basically a linked list."""
	while thing:
		yield thing
		thing = next_function(thing)




class MetaHierarchy(type):
	"""Ensure that each hierarchy class can't be accidentally mixed"""
	def __init__(new_class, class_name, class_bases, class_configuration):
		super(MetaHierarchy, new_class).__init__(class_name, class_bases, class_configuration)
		new_class._ROOT = {}




class Hierarchy(object):
	"""Encode a string as a tree, tracking counts of (all) children and
	essentially deduplicating common root chains.
	"""
	__metaclass__ = MetaHierarchy
	__slots__ = ['identifier', 'parent', 'children', 'population']
	
	_ROOT = {}
	
	__DELIMITER__ = ' -> '

	def __new__(cls, path):
		# TODO: this probably does twice the work it needs to when deduplicated
		cursor = cls._ROOT
		parts = path.split(cls.__DELIMITER__)
		for part in parts:
			if part not in cursor:
				entry = cls._init_new(parent=cursor, identifier=part)
				cursor[part] = entry
			cursor = cursor[part]
		return cursor
	
	@classmethod
	def _init_new(cls, **new_config):
		instance = super(Hierarchy, cls).__new__(cls)
		# these get set more efficiently in __new__
		parent = new_config.get('parent', None)
		instance.parent = parent if isinstance(parent, type(instance)) else None
		if instance.parent:
			for parent in follow(parent, lambda e: e.parent):
				parent.population += 1
		instance.identifier = new_config.get('identifier', None)
		instance.children = {}
		instance.population = 0
		return instance

	@property
	def all_children(self):
		for child in self.children.values():
			yield child
			for grandchild in child.all_children:
				yield grandchild
	
	@property
	def parents(self):
		for parent in follow(self, lambda e: e.parent):
			yield parent
	
	
	def __lt__(self, node):
		"""self < node if node is one of self's parents"""
		return any(node is parent for parent in self.parents if parent is not self)
	
	def __le__(self, node):
		"""self <= node if node is one of self's parents"""
		return any(node is parent for parent in self.parents)

	def __gt__(self, node):
		"""self > node if self is one of node's parents"""
		return any(self is parent for parent in node.parents if parent is not node)
	
	def __ge__(self, node):
		"""self >= node if self is one of node's parents"""
		return any(self is parent for parent in node.parents)
	
	def __and__(self, node):
		"""Returns the common ancestry, if any."""
		trunk = list(a for a,b in zip(
					reversed(list(self.parents)), 
					reversed(list(node.parents))
				) if a is b)
		if trunk:
			return trunk[-1]
		else:
			return None
			
	def astuple(self):
		return tuple(reversed(entry.identifier for entry in self.parents))
	
	def __contains__(self, identifier):
		return identifier in self.children
		
	def __setitem__(self, identifier, entry):
		assert isinstance(entry, type(self)), 'Hierarchies cannot be mixed: %r is not %r' % (entry, type(self))
		assert identifier == entry.identifier, 'Identifiers must match'
		self.children[identifier] = entry
		
	def __getitem__(self, identifier):
		return self.children[identifier]
		
	def __str__(self):		
		return self.__DELIMITER__.join(reversed(list(
			entry.identifier for entry in self.parents
		)))
		
	def __repr__(self):
		return '<%s %s>' % (type(self).__name__, self,)



class NamespacedHierarchy(Hierarchy):
	
	_NAMESPACE_PREFIX = ''
	_NAMESPACE_SUFFIX = ': '

	_NAMESPACE_PATTERN = None
	
	def __new__(cls, path, namespace=None):
		if namespace is None:
			# late eval so we don't have to figure this out via metaclass nonsense
			if cls._NAMESPACE_PATTERN is None:
				cls._NAMESPACE_PATTERN = re.compile(r'(?:%s(.*?)%s)?(.*)' % (
			        		re.escape(cls._NAMESPACE_PREFIX),re.escape(cls._NAMESPACE_SUFFIX),))
		
			namespace, path = cls._NAMESPACE_PATTERN.match(path).groups()
        
		if not namespace in cls._ROOT:
			entry = cls._init_new(identifier=namespace)
			cls._ROOT[namespace] = entry
		
		cursor = cls._ROOT[namespace]
		parts = path.split(cls.__DELIMITER__)
		for part in parts:
			if part not in cursor:
				entry = cls._init_new(parent=cursor, identifier=part)
				cursor[part] = entry				
			cursor = cursor[part]
			
		return cursor

	def __str__(self):
		entries = list(reversed(list(
				entry.identifier for entry in self.parents
				# convert the first delimiter to the namespace separator
			)))
		# head is the namespace
		if len(entries) == 1:
			return self._NAMESPACE_PREFIX + entries[0] + self._NAMESPACE_SUFFIX
		else:
			return self._NAMESPACE_PREFIX + self.__DELIMITER__.join(entries).replace(self.__DELIMITER__, self._NAMESPACE_SUFFIX, 1)



def _run_tests():
	
	from shared.data.types.deduplicated.hierarchy import Hierarchy


	cp1 = Hierarchy('root -> trunk -> branch a -> leaf a')
	cp2 = Hierarchy('root -> trunk -> branch b')
	cp3 = Hierarchy('root -> trunk -> branch b -> leaf b')
	cp4 = Hierarchy('root -> trunk -> branch c -> leaf c')
	
	
	assert cp3.parent is cp2
	assert cp2.parent is Hierarchy('root -> trunk')
	
	assert not(  cp2 <  cp2  )
	assert       cp2 <= cp2
	assert not(  cp2 <  cp3  )
	assert not(  cp2 <= cp3  )
	assert       cp3 <  cp2
	assert       cp3 <= cp2
	
	assert not(  cp2 >  cp2  )
	assert       cp2 >= cp2
	assert       cp2 >  cp3
	assert       cp2 >= cp3
	assert not(  cp3 >  cp2  )
	assert not(  cp3 >= cp2  )
	
	
	assert cp4 & cp3 is Hierarchy('root -> trunk')
	assert cp3 & cp2 is cp2

	print 'Comparison tests passed!'
