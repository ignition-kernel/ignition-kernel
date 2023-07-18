

from shared.data.types.deduplicated.dictslots import MetaDictSlots, DictSlots

from shared.data.types.deduplicated.persistence.attribute import Meta1IndexedAttributePersistenceMixin
from shared.data.types.deduplicated.persistence.combined import MetaFullPersistenceMixin
from shared.data.types.deduplicated.persistence.instance import PersistableInstanceLookupMixin, InstanceReferencesHandler
from shared.data.types.deduplicated.persistence.core import resolve_import_path

from shared.data.binary.handlers.string import StringHandler
from shared.data.binary.handlers.numeric import LongHandler
from shared.data.binary.handlers.helper import UnsignedIntTupleAsLongHandler
from shared.data.types.deduplicated.persistence.bincode import EnumeratedLookupFilePersistenceHandlerMixin




class DictSlotsInstanceReferencesBincoder(
		InstanceReferencesHandler,
		EnumeratedLookupFilePersistenceHandlerMixin, 
		StringHandler, 
		UnsignedIntTupleAsLongHandler, 
		LongHandler
	):
	
	# override for the specific case of the representative type
	def write_entry(self, entry):
		encoded_instance_value = self.encode_long_from_tuple_of_unsigned_ints(entry.references())
		self.write_long(encoded_instance_value)

	def read_entry(self):
		lng = self.read_long()
		references_tuple = self.decode_tuple_of_unsigned_ints_from_long(lng)
		return self.representing_class(references_tuple, _bypass_encoding=True)
	
	def read_entries(self):
		self.lookup.__lookup_table__.append(None) # to ensure one-indexing
		# sanity check follows in super
		super(DictSlotsInstanceReferencesBincoder, self).read_entries()




class MetaPersistableDictSlots(
		Meta1IndexedAttributePersistenceMixin,
		MetaFullPersistenceMixin, 
		MetaDictSlots
	):
	
	_INSTANCE_BINCODER_TYPE = DictSlotsInstanceReferencesBincoder
	
	def init_cache(cls, seed=None):
		super(MetaPersistableDictSlots, cls).init_cache(seed)
		cls.__instance_configurations__.clear()



class PersistableDictSlots(PersistableInstanceLookupMixin, DictSlots):
	__metaclass__ = MetaPersistableDictSlots
	pass





def _run_tests(dump_location = r'C:\Workspace\temp\coredump'):

	from shared.tools.pretty import p,pdir,install;install()
	
	from shared.data.types.deduplicated.persistence.dictslots import PersistableDictSlots
	
	print 'Running roundtrip persistence test: %r' % (dump_location,)
	
	class DDS(PersistableDictSlots):
	    __slots__ = 'a b c d'.split()
	
	    def __repr__(self):
	        fmtstr = '<%s %s>' % (type(self).__name__,
	            ' '.join('%%(%s)r' % slot for slot in self.__slots__),)
	        return fmtstr % self
	
	print '   (for %r)' % (DDS.__classpath__,)
	
	
	cycle = 25
	
	
	for i in range(0,1000,4):
	    dds = DDS(*(chr(ord('a') + (i+x)%cycle) for x in range(4)))
	
	
	current_seed = DDS.__lookup__.seed
	
	#print 'Created'
	#print '=== values ==='
	#DDS.__lookup__.__lookup_table__
	#
	#print '=== instances ==='
	#DDS.__instance_lookup__.__lookup_table__
	
	DDS.dump(dump_location)
	
	_ = DDS('aa', 'bb', 'c', 'dd')
	
	DDS.dump(dump_location)
	
	DDS.init_cache(123456)
	
	DDS.load(dump_location, current_seed)
	
	
	print 'Round trip'
	print '=== values ==='
	p(DDS.__lookup__.__lookup_table__)
	
	print '=== instances ==='
	p(DDS.__instance_lookup__.__lookup_table__)
	
	
	assert DDS.__instance_lookup__.__lookup_table__[-1].references() == (26,27,3,28)
