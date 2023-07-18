


from shared.data.types.deduplicated.persistence.attribute import MetaAttributePersistenceMixin
from shared.data.types.deduplicated.persistence.instance import MetaInstancePersistenceMixin




class MetaFullPersistenceMixin(MetaInstancePersistenceMixin, MetaAttributePersistenceMixin):

	def _init_bincoders(cls, folder_path, seed=None):
		assert cls.__instance_lookup__.seed == cls.__lookup__.seed, (
				'Instance and accompanying attribute lookup seed mismatch: %r vs %r (resp.)' % (
					cls.__instance_lookup__.seed, cls.__lookup__.seed,))
		
		if seed is None:
			seed = cls.__lookup__.seed

		super(MetaFullPersistenceMixin, cls)._init_bincoders(folder_path, seed)
