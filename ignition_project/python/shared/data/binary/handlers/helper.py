"""
	Helpers to standardize the encoding process
	
	Isolating how types and lengths are encoded helps keep guesswork
	out of decoding the packed binary streams.
"""

__all__ = [
	'TypeHandler',
	'GenericHandler',
	'LengthHandler',
	
	'HelperHandlers',
]   



from shared.data.binary.handlers.numeric import CompressedLongHandler, ByteHandler


from io import BytesIO


class TypeHandler(CompressedLongHandler):

	def get_type_ix(self, obj):
		raise NotImplementedError('Override in consolidated handler class.')

	def write_type(self, obj):
		type_ix = self.get_type_ix(obj)
		self.write_type_ix(type_ix)

	# use signed int, since hashes are signed and that's 
	# likely to be the supplemental identifier, since it
	# can be invariant for the type
	def write_type_ix(self, type_ix):
		self.write_long_compressed(type_ix)

	def read_type_ix(self):
		return int(self.read_long_compressed())



class GenericHandler(TypeHandler):

	def write_object(self, obj):
		raise NotImplementedError('Placeholder: override in consolidated handler')

	def read_object(self):
		raise NotImplementedError('Placeholder: override in consolidated handler')      



class LengthHandler(CompressedLongHandler):

	def write_length(self, some_lengthy_object):
		self.write_length_raw(len(some_lengthy_object))

	def write_length_raw(self, length_integer):
		"""Convenience function to make sure that any length is written
		the same way, even if we have to provide it
		"""
		self.write_long_compressed(length_integer)

	def read_length(self):
		return int(self.read_long_compressed())



class PackedTuple(CompressedLongHandler):
	def __init__(self):
		self.stream = BytesIO()
		
	def iter_bytes(self):
		self.stream.seek(0)
		try:
			while True:
				yield self.read_byte()
		except EOFError:
			raise StopIteration
	
	def iter_long(self):
		self.stream.seek(0)
		try:
			while True:
				yield self.read_long_compressed()
		except EOFError:
			raise StopIteration     



class UnsignedIntTupleAsLongHandler(object):
	"""Encode (and decode) tuples of ints as a single Long."""
	
	@staticmethod
	def encode_long_from_tuple_of_unsigned_ints(tup):
		assert all(tup), "Zero can not be reliably encoded due to how long integers are encoded (at end of tuple)"   
		
		packed_bytes = PackedTuple()
		
		for i in tup:
			packed_bytes.write_long_compressed(i)
		
		x = 0
		for ix, b in enumerate(packed_bytes.iter_bytes()):
			x |= (b << (ix*8))
		return x

	@staticmethod
	def decode_tuple_of_unsigned_ints_from_long(lng):
		packed_bytes = PackedTuple()
		num_bytes, remainder = divmod(lng.bit_length(), 8)
		if remainder:
			num_bytes += 1
		for ix in range(num_bytes):
			packed_bytes.write_byte(255 & lng >> (ix*8))
		
		return tuple(int(l) for l in packed_bytes.iter_long())


#class UnsignedIntTupleAsLongHandler(object):
#    """Encode tuples of ints as a single Long"""
#    
#    @staticmethod
#    def encode_long_from_tuple_of_unsigned_ints(tup, bytes_per_entry=3):
#       assert all(tup), "Zero can not be reliably encoded due to how long integers are encoded (at end of tuple)"   
#       
#        entry_bits = 8*bytes_per_entry
#        x = 0
#        for ix, index in enumerate(tup):
#            if index.bit_length() > entry_bits: # (entry_bits-1) if entries are signed, which they're not
#                raise OverflowError('Value %r (%d bits) is larger than %d bytes per entry (%d bits)' % (
#                    index, index.bit_length(), bytes_per_entry, entry_bits))
#            x |= (index << (ix*entry_bits))
#        return x
#
#    @staticmethod
#    def decode_tuple_of_unsigned_ints_from_long(lng, bytes_per_entry=3):
#        entry_bits = 8*bytes_per_entry
#        entry_mask = (1<<entry_bits)-1
#        entries, remainder = divmod(lng.bit_length(), entry_bits)
#        if remainder:
#            entries += 1
#        return tuple(
#            int(entry_mask & (lng >> (ix*entry_bits)))
#            for ix in range(entries)
#        )



# include in opposite order of their dependence to prevent MRO confusion
class HelperHandlers(
		LengthHandler, 
		GenericHandler,
		TypeHandler,
	): pass
