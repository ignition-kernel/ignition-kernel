"""
	Dict Posing As Class
	
	Because d.A is sometimes nicer than d['A']
"""


class DictPosingAsClass(object):
	"""
	Convert a dictionary to an object that's class-like.

	Enter expected fields in __slots__.

	Set _skip_undefined to True to ignore dict fields that
	  are not in __slots__.

	Entries in _coerce_fields should be keys that are in __slots__
	  and values that are functions (or types).

	>>> dpac = DPAC(**some_dict)
	"""
	__slots__ = tuple()

	# True == exclusive to __slots__
	# False == no error if extra args beyond what's in __slots__, just skipped
	_skip_undefined=False

	_coerce_fields = {}

	@classmethod
	def _nop(cls, x):
		return x
	def _coerce(self, key, value):
		return self._coerce_fields.get(key, self._nop)(value)

	def __init__(self, **kwargs):
		if self._skip_undefined:
			for key,value in kwargs.items():
				try:
					self.__setitem__(key, value)
				except AttributeError:
					pass
		else:
			for key,value in kwargs.items():
				self.__setitem__(key, value)

	def keys(self):
		ks = []
		for key in self.__slots__:
			try:
				_ = getattr(self, key)
				ks.append(key)
			except AttributeError:
				pass
		return ks

	def values(self):
		vs = []
		for key in self.__slots__:
			try:
				vs.append(getattr(self, key))
			except AttributeError:
				pass
		return vs

	def __contains__(self, key):
		try:
			_ = getattr(self, key)
			return True
		except AttributeError:
			return False

	def __setitem__(self, key, val):
		setattr(self, key, self._coerce(key,val))

	def __getitem__(self, key):
		if not key in self.__slots__:
			raise AttributeError('"%s" is not a key in __slots__' % key)
		try:
			return getattr(self, key)
		except AttributeError:
			return None

	def _asdict(self):
		d = {}
		for key in self.__slots__:
			try:
				v = getattr(self, key)
				d[key] = v._asdict() if isinstance(v, DictPosingAsClass) else v
			except AttributeError:
				pass
		return d
	
#	@property
#	def format_dict(self):
#		return self._asdict()
	
	def _astuple(self):
		t = tuple()
		for key in self.__slots__:
			try:
				v = getattr(self, key)
				t += (v._astuple() if isinstance(v, DictPosingAsClass) else v,)
			except AttributeError:
				pass
		return t
	
#	@property
#	def format_tuple(self):
#		return self._astuple()

	def __repr__(self):
		return repr(self._asdict())


class DPAC_JSON(DictPosingAsClass):
	"""An example of extending it for easier serializing"""
	@classmethod
	def _coerceToString(cls, thing):
		if isinstance(thing, DictPosingAsClass):
			return thing._asdict()
		if isinstance(thing, tuple):
			return list(thing)
		if isinstance(thing, (arrow.Arrow, datetime)):
			return thing.isoformat()
		return repr(thing)

	def __repr__(self):
		return rapidjson.dumps(self._asdict(), indent=2, default=self._coerceToString)



class PassThruDict(object):
	"""A sloppy JS-like object thing that will work through attributes.
	
	Call _cull_empty to GC unused or empty PTDs	
	"""
	__slots__ = ['_dict', '_strict_getattr']
	
	
	def __init__(self, somedict=None, auto_attr=True):
		self._dict = somedict or {}
		self._strict_getattr = not auto_attr
	
	def __getattr__(self, attr):
		try: # attempt to use the Python attributes _first_ (so our mechanics work!)
			return super(PassThruDict, self).__getattr__(attr)
		except AttributeError as error:
			try:
				return getattr(self._dict, attr)
			except AttributeError:
				pass
			try:
				target = self._dict[attr]
				if isinstance(target, dict):
					return type(self)(target)
				else:
					return target
			except KeyError:
				if self._strict_getattr or attr.startswith('__'):
					raise error
				else:
					self._dict[attr] = type(self)()
					return self._dict[attr]

	def __setattr__(self, attr, value):
		try: # attempt to use the Python attributes _first_ (so our mechanics work!)
			assert attr in self.__slots__
			return super(PassThruDict, self).__setattr__(attr, value)
		except (AssertionError, AttributeError) as error:
			if isinstance(value, dict):
				self._dict[attr] = type(self)(value)
			else:
				self._dict[attr] = value
	
	def _cull_empty(self):
		d = self._dict
		for attr in frozenset(d):
			try:
				v = d[attr]
				if isinstance(v, PassThruDict):
					if v is None:
						del d[attr]
					else:
						v._cull_empty()
			except KeyError:
				pass
		
	def __bool__(self):
		return bool(self._dict)
	
	def __len__(self):
		if self._strict_getattr:
			return len(self._dict)
		else: # don't count empty attributes
			return len(self.values())
	
	def keys(self):
		return [k for k,v in self._dict.items()
				if (v if isinstance(v, PassThruDict) else True)		
			   ]
	
	def values(self):
		return [v for v in self._dict.values()
				if (v if isinstance(v, PassThruDict) else True)
			   ]
	
	def __getitem__(self, key):
		return self._dict[key]
	
	def __setitem__(self, key, value):
		self._dict[key] = value
	
	def __repr__(self):
		return repr(self._dict)
