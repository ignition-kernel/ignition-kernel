"""
	Deduplicated slot attributes - a minimalist, memoized struct

"""

__all__ = ['DictSlots']



from shared.data.types.dictslots import DictSlotsMixin

from java.lang.System import currentTimeMillis




class MetaDictSlots(type):
	"""Manufacture and enforce the deduplicated attribute slot setup.
	
	This takes the definition of slots given, but redirects them to private deduplicated
	enumerated lookup values.
	"""
	def __new__(metacls, class_name, class_bases, class_configuration):
		# for type validation and consistency (like how Pickle needs it)

		# grab and merge parent types if they have slots
		# The order here results in this:
		#   ClassAsdf.__slots__ = ['a','s','d','f']
		#   ClassQwer.__slots__ = ['q','w','e','r']
		#   ClassBoth(ClassAsdf, ClassQwer, PassThruInitMixin)
		#  where pass-thru is just __init__(self, *args) dumped directly into __slots__
		#  yielding 
		#   >>> b = ClassBoth(list('ASDFQWER'))
		#   >>> print b.a, b.q, b.r
		#   A Q R
		slots = []
		for base in class_bases:
			slots += list(getattr(base,'__slots__', []))
		slots += list(class_configuration.get('__slots__', []))
		class_configuration['__slots__'] = slots
				
		# ensure instance configurations (for dedupe lookup) is initialized uniquely for each subclass
		class_configuration['__instance_configurations__'] = {}

		# misdirect slots so it doesn't need to be wrangled by the end user
		assert not any(s.startswith('_') for s in slots), 'Attribute misdirection only works on public attributes in __slots__'

		encoded_slots = []
		for slot in slots:
			encoded_slot = '_' + slot
			encoded_slots.append(encoded_slot)
			
			def getter(self, encoded_slot=encoded_slot):
				return self.__lookup__.value(getattr(self, encoded_slot))
				
			def setter(self, new_value, encoded_slot=encoded_slot):
				setattr(self, encoded_slot, self.__lookup__.index(new_value))
				
			def deleter(self, encoded_slot=encoded_slot):
				setattr(self, encoded_slot, None)
			
			# swap over original as a property to make the change transparent
			class_configuration[slot] = property(fget=getter, fset=setter, fdel=deleter)

		class_configuration['__slots__'] = tuple(encoded_slots)
		class_configuration['__keys__'] = slots
		
		new_class = super(MetaDictSlots, metacls).__new__(metacls, class_name, class_bases, class_configuration)
		
		return new_class


	def generate(cls, *args, **kwargs):
		"""Generate an instance for the init call given more appropriate context.
		
		Override this for each subclass so __init__ doesn't need to be overridden.
		"""
		raise NotImplementedError('Subclasses must override what resolves the generator')
		# errors here mean that the init missed a calc
		local_vars = locals()
		slot_values = tuple(local_vars[attr] for attr in cls.keys())
		return cls(*slot_values)




class DictSlots(DictSlotsMixin):
	"""Like DictSlots (and namedtuple!), but goes a step further making binary expression 
	easier. It also pulls all the mixin designs into one, making it much easier to 
	understand how it functions.    
	"""
	__metaclass__ = MetaDictSlots
	
	# prevent creating additional objects, maintain literally one instance of anything
	__instance_configurations__ = {}
	#__instance_lookup__

	def __new__(cls, *slot_values, **overrides):
		"""Build an instance, assigning slots_values in order of __slots__,
		but automatically encoding them for deduplication via EnumeratedLookup.
		"""
		if overrides.pop('_bypass_encoding', False): # allow for pre-computed values (i.e. for reloading)
			instance_key = slot_values[0]
		else:
			instance_key = cls._encode_with_overrides(slot_values, overrides)
		
		assert len(instance_key) == len(cls.__slots__), 'Cannot resolve into slot values: %r' % (slot_values,)
		
		if instance_key not in cls.__instance_configurations__:
			# create only if needed
			instance = super(DictSlots, cls).__new__(cls, *slot_values)
			cls.__instance_configurations__[instance_key] = instance
		return cls.__instance_configurations__[instance_key]


	def __init__(self, *slot_values, **overrides):
		if overrides.pop('_bypass_encoding', False):
			for slot_ix, reference in enumerate(slot_values[0]):
				setattr(self, self.__slots__[slot_ix], reference)
		else:
			for attr, value in zip(self.keys(), slot_values):
				setattr(self, attr, value)


	@classmethod
	def _encode_with_overrides(cls, slot_values, slot_overrides):
		if not slot_overrides:
			return cls.encode(*slot_values)
		else:
			return cls.encode(*tuple(
				slot_overrides.get(key, slot_values[ix])
				for ix, key
				in enumerate(cls.keys())
			))
	
	
	@classmethod
	def encode(cls, *values):
		"""Convert values into integer indexes for lookup"""
		return cls.__lookup__.encode(*values)

	@classmethod
	def decode(cls, *indexes):
		"""Resolve indexes into their respective values."""
		return cls.__lookup__.decode(*indexes)


	# dict helpers

	@classmethod
	def keys(cls):
		return cls.__keys__

	def values(self):
		"""Actual values for slots of instance"""
		return tuple(getattr(self, key) for key in self.__keys__)
	
	def references(self):
		"""Lookup references for slots of instance"""
		return tuple(getattr(self, slot) for slot in self.__slots__)
	
	def items(self):
		return tuple((key, getattr(self, key)) for key in self.__keys__)

	def __getitem__(self, key):
		try:
			return getattr(self, key)
		except AttributeError:
			raise KeyError('%s is not an attribute of %r' % (key, self))
	
	def __setitem__(self, key, value):
		print key, value
		try:
			setattr(self, key, value)
		except AttributeError:
			raise KeyError('%s is not an attribute of %r' % (key, self))
	
	def __delitem__(self, key):
		try:
			setattr(self, key, None)
		except AttributeError:
			raise KeyError('%s is not an attribute of %r' % (key, self))


	def __len__(self):
		return len(self.__keys__)
	
	def __iter__(self):
		for key in self.__keys__:
			yield key
	
	def __reversed__(self):
		for key in reversed(self.__keys__):
			yield key


	def asdict(self):
		d = {}
		for key in self.keys():
			value = getattr(self, key)
			if isinstance(value, (DictSlots, DictSlotsMixin)):
				value = value.asdict()
			elif isinstance(value, (list, tuple, set)):
				value = [
					v.asdict() if isinstance(v, (DictSlots, DictSlotsMixin)) else v
					for v in value
				]
			d[key] = value
		return d
	
	
	def astuple(self):
		t = tuple()
		for key in self.keys():
			value = getattr(self, key)
			if isinstance(value, (DictSlots, DictSlotsMixin)):
				value = value.astuple()
			elif isinstance(value, (list, tuple, set)):
				value = tuple(
					v.astuple() if isinstance(v, (DictSlots, DictSlotsMixin)) else v
					for v in value
				)
			t += (value,)
		return t

