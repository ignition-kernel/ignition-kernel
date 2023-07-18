"""
	Helpers to store, encode, and compare hierarchies.
	
"""

from shared.data.types.deduplicated.persistence.instance import MetaInstancePersistenceMixin, PersistableInstanceLookupMixin, InstanceReferencesHandler
from shared.data.types.deduplicated.persistence.memo import EnumeratedLookupFilePersistenceHandlerMixin
from shared.data.types.deduplicated.hierarchy import MetaHierarchy, Hierarchy, NamespacedHierarchy
from shared.data.binary.handlers.string import StringHandler
from shared.data.binary.handlers.numeric import CompressedLongHandler




class HierarchyInstanceBincoder(
		InstanceReferencesHandler,
		EnumeratedLookupFilePersistenceHandlerMixin, 
		StringHandler,
		CompressedLongHandler,
	):
	
	
	def write_entries(self):
		# skip the first (0th) which is None (needed as the root/anchor, and shouldn't be encoded)
		if not self.next_entry_ix:
			self.next_entry_ix = 1
		super(HierarchyInstanceBincoder, self).write_entries()


	# override for the specific case of the representative type
	def write_entry(self, entry):
		try:
			parent_ix = entry.parent.__index__()
		except AttributeError:
			parent_ix = 0
		self.write_str(entry.identifier)
		self.write_long_compressed(parent_ix)

	def read_entries(self):
		self.lookup.__lookup_table__.append(None) # to ensure one-indexing
		# sanity check follows in super
		super(HierarchyInstanceBincoder, self).read_entries()

	def read_entry(self):
		identifier = self.read_str()
		parent_reference = self.read_long_compressed()
		return self.representing_class._init_new(
			identifier=identifier, 
			parent=self.representing_class[parent_reference]
		)
	


class MetaPersistableHierarchy(MetaInstancePersistenceMixin, MetaHierarchy):
	"""Ensure that each hierarchy has their own lookups"""
	_INSTANCE_BINCODER_TYPE = HierarchyInstanceBincoder

	def init_cache(cls, seed=None):
		super(MetaPersistableHierarchy, cls).init_cache(seed)
		# root parent is None, so we need a reference for this
		cls.__instance_lookup__.__lookup_table__.append(None)


class PersistableHierarchy(PersistableInstanceLookupMixin, Hierarchy):
	"""Encode a string as a tree, tracking counts of (all) children and
	essentially deduplicating common root chains.
	"""
	__metaclass__ = MetaPersistableHierarchy

	@classmethod
	def _init_new(cls, **new_config):
		instance = super(PersistableHierarchy, cls)._init_new(**new_config)
		# make sure these are indexed in order
		_ = cls.__instance_lookup__.index(instance)
		return instance


class PersistableNamespacedHierarchy(PersistableInstanceLookupMixin, NamespacedHierarchy):
	"""Encode a string as a tree, tracking counts of (all) children and
	essentially deduplicating common root chains.
	"""
	__metaclass__ = MetaPersistableHierarchy

	@classmethod
	def _init_new(cls, **new_config):
		instance = super(PersistableNamespacedHierarchy, cls)._init_new(**new_config)
		# make sure these are indexed in order
		_ = cls.__instance_lookup__.index(instance)
		return instance






def _run_tests(dump_location = r'C:\Workspace\temp\coredump'):

	from shared.tools.pretty import p,pdir,install;install() 
	
	from shared.data.types.deduplicated.persistence.hierarchy import PersistableHierarchy as Hierarchy #, NamespacedHierarchy
	
	print '=' * 80
	print 'Testing persistence of hierarchy'
	
	
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

	print 'Hierarchy comparison tests passed!'

	current_seed = Hierarchy.__instance_lookup__.seed
	
	Hierarchy.dump(dump_location)
	
	cp5 = Hierarchy('root -> trunk -> branch c -> leaf d')
	
	Hierarchy.dump(dump_location)
	
	print '=== instances (after dump) ==='
	p(Hierarchy.__instance_lookup__.__lookup_table__)
	
	Hierarchy.init_cache(123456)
	
	Hierarchy.load(dump_location, current_seed)
	
	print '=== instances (after load) ==='
	p(Hierarchy.__instance_lookup__.__lookup_table__)
	
	from shared.data.types.deduplicated.persistence.hierarchy import PersistableNamespacedHierarchy as NamespacedHierarchy
	
	#ncp1 = NamespacedHierarchy('zone 1', 'root')
	ncp11 = NamespacedHierarchy('zone 1', 'root -> trunk -> branch a -> leaf a')
	ncp21 = NamespacedHierarchy('zone 1', 'root -> trunk -> branch b')
	ncp31 = NamespacedHierarchy('zone 1', 'root -> trunk -> branch b -> leaf b')
	ncp41 = NamespacedHierarchy('zone 1', 'root -> trunk -> branch c -> leaf c')
	
	ncp12 = NamespacedHierarchy('zone 2', 'root -> trunk -> branch a -> leaf a')
	ncp22 = NamespacedHierarchy('zone 2', 'root -> trunk -> branch b')
	ncp32 = NamespacedHierarchy('zone 2', 'root -> trunk -> branch b -> leaf b')
	ncp42 = NamespacedHierarchy('zone 2', 'root -> trunk -> branch c -> leaf c')
	
	
	assert ncp31.parent is ncp21
	assert ncp21.parent is NamespacedHierarchy('zone 1', 'root -> trunk')
	
	assert not(  ncp21 <  ncp21  )
	assert       ncp21 <= ncp21
	assert not(  ncp21 <  ncp31  )
	assert not(  ncp21 <= ncp31  )
	assert       ncp31 <  ncp21
	assert       ncp31 <= ncp21
	
	assert not(  ncp21 >  ncp21  )
	assert       ncp21 >= ncp21
	assert       ncp21 >  ncp31
	assert       ncp21 >= ncp31
	assert not(  ncp31 >  ncp21  )
	assert not(  ncp31 >= ncp21  )
	
	assert ncp41 & ncp31 is NamespacedHierarchy('zone 1', 'root -> trunk')
	assert ncp31 & ncp21 is ncp21
	
	# validating for other namespace
	assert ncp32.parent is ncp22
	assert ncp22.parent is NamespacedHierarchy('zone 2', 'root -> trunk')
	
	assert not(  ncp22 <  ncp22  )
	assert       ncp22 <= ncp22
	assert not(  ncp22 <  ncp32  )
	assert not(  ncp22 <= ncp32  )
	assert       ncp32 <  ncp22
	assert       ncp32 <= ncp22
	
	assert not(  ncp22 >  ncp22  )
	assert       ncp22 >= ncp22
	assert       ncp22 >  ncp32
	assert       ncp22 >= ncp32
	assert not(  ncp32 >  ncp22  )
	assert not(  ncp32 >= ncp22  )
	
	assert ncp42 & ncp32 is NamespacedHierarchy('zone 2', 'root -> trunk')
	assert ncp32 & ncp22 is ncp22

	# verify namespaces don't overlap (duh, but may as well)
	assert ncp12.parent > ncp12
	assert not (ncp12.parent > ncp11)

	print 'NamespacedHierarchy comparison tests passed!'

	print '=' * 80
	print 'Testing persistence of NamespacedHierarchy'
	
	current_seed = NamespacedHierarchy.__instance_lookup__.seed
	
	NamespacedHierarchy.dump(dump_location)
	
	ncp51 = NamespacedHierarchy('zone 1', 'root -> trunk -> branch c -> leaf d')
	
	NamespacedHierarchy.dump(dump_location)
	
	print '=== instances (after dump) ==='
	p(NamespacedHierarchy.__instance_lookup__.__lookup_table__)
	
	NamespacedHierarchy.init_cache(123456)
	
	NamespacedHierarchy.load(dump_location, current_seed)
	
	print '=== instances (after load) ==='
	p(NamespacedHierarchy.__instance_lookup__.__lookup_table__)
