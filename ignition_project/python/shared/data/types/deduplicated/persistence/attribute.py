


from shared.data.types.deduplicated.persistence.core import MetaBasePersistenceMixin
from shared.data.types.deduplicated.persistence.memo import EnumeratedLookup, EnumeratedLookupBincoder

import os




class MetaAttributePersistenceMixin(MetaBasePersistenceMixin):

	_ATTRIBUTE_BINCODER_TYPE = EnumeratedLookupBincoder

	def __new__(metacls, class_name, class_bases, class_configuration):
		class_configuration['_attribute_bincoder'] = None
		# allow attribute lookup to potentially be shared
		_ = class_configuration.setdefault('__lookup__', None)
		return super(MetaAttributePersistenceMixin, metacls).__new__(metacls, class_name, class_bases, class_configuration)

	def init_cache(cls, seed=None):
		super(MetaAttributePersistenceMixin, cls).init_cache(seed)
		if cls.__lookup__ is None:
			# use the existing lookup, if any already exists
			cls.__lookup__ = EnumeratedLookup(label=cls.__classpath__)
		# ... but blow the cache anyway to be safe
		cls.__lookup__.clear(cls.__seed__)


	def dump(cls, folder_path, seed=None):
		super(MetaAttributePersistenceMixin, cls).dump(folder_path, seed)
		cls._attribute_bincoder.write()


	def load(cls, folder_path, seed=None):
		super(MetaAttributePersistenceMixin, cls).load(folder_path, seed)
		
		cls._attribute_bincoder.read()

		# replace with new lookup generated by bincoder
		cls.__lookup__ = cls._attribute_bincoder.lookup
		
		# ... and clear out to ensure it's a one-shot
		cls._attribute_bincoder = None
		

	def _init_bincoders(cls, folder_path, seed=None):
		super(MetaAttributePersistenceMixin, cls)._init_bincoders(folder_path, seed)
		seed = seed or cls.__lookup__.seed
		attribute_filepath = cls._attribute_bincoder_filepath(folder_path, seed, prep_directory=True)
		cls._attribute_bincoder = cls._ATTRIBUTE_BINCODER_TYPE(attribute_filepath, cls.__lookup__)


	def _attribute_bincoder_filepath(cls, folder_path, seed, prep_directory=False):
		target_folder = cls._target_folder(folder_path, seed, prep_directory)
		return os.path.join(target_folder, 'attributes.bin')


	def _verify_bincoder_targets(cls, folder_path, seed=None):
		super(MetaAttributePersistenceMixin, cls)._verify_bincoder_targets(folder_path, seed)
		assert cls._attribute_bincoder, 'Attribute bincoder not initialized'
		seed = seed or cls.__lookup__.seed
		attribute_filepath = cls._attribute_bincoder_filepath(folder_path, seed)
		assert os.path.exists(attribute_filepath), 'Attribute value lookup file does not exist:  %r' % (attribute_filepath,)
		assert attribute_filepath == cls._attribute_bincoder.filepath, 'Already initialized attribute bincoder targetting different filepath'



class NonePaddedAttributeBincoder(EnumeratedLookupBincoder):
	"""Special case of when an attribute must be 1-indexed."""
	
	def write_header(self):
		assert self.lookup.__lookup_table__[0] is None, 'Attribute enumerated lookups start with None to force 1-indexing for the instance refrences.'
		super(NonePaddedAttributeBincoder, self).write_header()
		self.next_entry_ix = 1 # skip first, since it's just None


class Meta1IndexedAttributePersistenceMixin(MetaAttributePersistenceMixin):
	_ATTRIBUTE_BINCODER_TYPE = NonePaddedAttributeBincoder
	
	def init_cache(cls, seed=None):
		super(Meta1IndexedAttributePersistenceMixin, cls).init_cache(seed)
		
		# to make all references 1-indexed and to ensure reference 0 is always None
		# (though encoding None will still reference a new slot the first time!)
		cls.__lookup__.__lookup_table__.append(None)
