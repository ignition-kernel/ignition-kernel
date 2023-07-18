"""
	Binary represenation of numbers
	
	For these, the builtin struct library is used to ensure a
	standardized and non-ambiguous format is used.

	NOTE: longs are treated as 64 bit long integers, NOT like Python
		  `long` types. A proper treatment would chain bytes together
		  so the long could be arbitrarily large, but getting the sign
		  and the chaining right was annoying.
"""

__all__ = [
	'BoolHandler',
	'IntHandler',
	'FloatHandler',
	'ComplexHandler',
	
	'NumericHandlers',
]   


from shared.data.binary.handlers.stream import StreamHandler


import struct



class BoolHandler(StreamHandler):

	def write_bool(self, boolean_value):
		self.write_to_stream(chr(1 if boolean_value else 0))

	def read_bool(self):
		return True if ord(self.read_from_stream(1)) else False


class ByteHandler(StreamHandler):
	_BYTE_MASK = (1<<8)-1
	
	def write_byte(self, byte_number):
		self.write_to_stream(chr(byte_number))
	
	def read_byte(self):
		return ord(self.read_from_stream(1))


class RawBytesChunkHandler(ByteHandler):

	
	def write_raw_bytes_chunk(self, chunk, num_bytes=None):
		if num_bytes is None:
			num_bytes, remainder = divmod(chunk.bit_length(), 8)
			if remainder:
				num_bytes += 1
		ba = bytearray(
					((chunk >> (byte_offset * 8)) & self._BYTE_MASK)
					for byte_offset
					in range(num_bytes)
				)
		_ = self.write_to_stream(ba)

	def read_raw_bytes_chunk(self, num_bytes):
		chunk = 0
		for byte_number in range(num_bytes):
			chunk += (ord(self.read_from_stream(1)) << (byte_number * 8))
		return chunk


class ShortHandler(StreamHandler):
	
	# Class properties to let engine be tuned or subclass overridden
	# network encoding is big endian, but may as well asssume networky
	_SHORT_STRUCT_WRITE_CODE = '!h'
	_SHORT_STRUCT_READ_BYTES = 2
	_UNSIGNED_SHORT_STRUCT_WRITE_CODE = '!H'
	_UNSIGNED_SHORT_STRUCT_READ_BYTES = 2
	   
	def write_short(self, short_value):
		self.write_to_stream(struct.pack(self._SHORT_STRUCT_WRITE_CODE, short_value))
	
	def read_short(self):
		raw_bytes = self.read_from_stream(self._SHORT_STRUCT_READ_BYTES)
		return struct.unpack(self._SHORT_STRUCT_WRITE_CODE, raw_bytes)[0]


	def write_unsigned_short(self, unsigned_short_value):
		self.write_to_stream(struct.pack(self._UNSIGNED_SHORT_STRUCT_WRITE_CODE, unsigned_short_value))

	def read_unsigned_short(self):
		raw_bytes = self.read_from_stream(self._UNSIGNED_SHORT_STRUCT_READ_BYTES)
		return struct.unpack(self._UNSIGNED_SHORT_STRUCT_WRITE_CODE, raw_bytes)[0]



class IntHandler(StreamHandler):
	
	# Class properties to let engine be tuned or subclass overridden
	# network encoding is big endian, but may as well asssume networky
	_INTEGER_STRUCT_WRITE_CODE = '!i'
	_INTEGER_STRUCT_READ_BYTES = 4
	_UNSIGNED_INTEGER_STRUCT_WRITE_CODE = '!I'
	_UNSIGNED_INTEGER_STRUCT_READ_BYTES = 4
	
#   MAX_STRUCT_ENCODABLE_LONG = (1<<((8*8)-1))-1 # ((8 bytes by 8 bits per byte) less one bit) less one
	
	def write_int(self, integer_value):
		self.write_to_stream(struct.pack(self._INTEGER_STRUCT_WRITE_CODE, integer_value))
	
	def read_int(self):
		raw_bytes = self.read_from_stream(self._INTEGER_STRUCT_READ_BYTES)
		return struct.unpack(self._INTEGER_STRUCT_WRITE_CODE, raw_bytes)[0]


	def write_unsigned_int(self, unsigned_integer_value):
		self.write_to_stream(struct.pack(self._UNSIGNED_INTEGER_STRUCT_WRITE_CODE, unsigned_integer_value))

	def read_unsigned_int(self):
		raw_bytes = self.read_from_stream(self._UNSIGNED_INTEGER_STRUCT_READ_BYTES)
		return struct.unpack(self._UNSIGNED_INTEGER_STRUCT_WRITE_CODE, raw_bytes)[0]



class LongHandler(RawBytesChunkHandler):
	
	#   LONG_STRUCT_WRITE_CODE = '!q'
	#   LONG_STRUCT_READ_BYTES = 8
	#### Profiling suggests that the struct method is similar in time to the more 
	#### drawn out arbitrary type, except that the long long type is able to encode arbitrarily
	#### large longs, which is a fairly major boon.
	#
	#   def write_long(self, long_value):
	#       if long_value < self.MAX_STRUCT_ENCODABLE_LONG:
	#           self.write_to_stream(struct.pack(self.LONG_STRUCT_WRITE_CODE, long_value))
	#       else:
	#           self.write_unsigned_long(long_value)
	#   
	#   def read_long(self):
	#       return struct.unpack(self.LONG_STRUCT_WRITE_CODE, 
	#                            self.read_from_stream(self.LONG_STRUCT_READ_BYTES))[0]
	
	
	# NOTE: IMPORTANT!
	#       At our expected scale, 16M is plenty but 65k is likely too small.
	#       We could use 4 bytes, but why waste 33% more than needed?
	# Therefore super large ints are written in chunks of 3, since we're likely to not
	# overuse that space and it lets us typically pack more in!
	# 
	# And, IFF we ever do use more than 3 bytes, well, that'll be 50% larger than a normal
	# long. So it's more of a long-con stats game.
	_LONG_BYTE_CHUNKS = 3

	# less one for chain flag 
	# (for 3 bytes: bit shift 23 (from 0) to be on 23 (the 24th bit, last of 3 bytes))
	_LONG_BYTE_CHUNK_BITS = (_LONG_BYTE_CHUNKS*8)-1
	_LONG_BYTE_CONTINUATION_FLAG_MASK = (1 << _LONG_BYTE_CHUNK_BITS)
	_LONG_BYTE_CHUNK_MASK = (_LONG_BYTE_CONTINUATION_FLAG_MASK - 1)

	
	# flag sign on the first byte's penultimate bit to the continuation bit
	_LONG_BYTE_NEGATIVE_FLAG_MASK = (1<<(_LONG_BYTE_CHUNK_BITS-1))
	

	def write_long(self, long_value):
		
		negative = long_value < 0
		# encode as positive, but flag later as negative
		# dealing with chained bytes as well as 
		if negative:
			long_value *= -1
		
		# process first chunk of long given
		chunk = long_value & (self._LONG_BYTE_CHUNK_MASK >> 1) # less one for sign
		
		if negative:
			chunk |= self._LONG_BYTE_NEGATIVE_FLAG_MASK
	
		# first chunk drains one less bit due to sign big
		long_value = (long_value >> (self._LONG_BYTE_CHUNK_BITS - 1))
		
		if long_value:
			chunk |= self._LONG_BYTE_CONTINUATION_FLAG_MASK
		
		self.write_raw_bytes_chunk(chunk, self._LONG_BYTE_CHUNKS)
		
		while long_value:
			chunk = long_value & self._LONG_BYTE_CHUNK_MASK
			long_value = (long_value >> self._LONG_BYTE_CHUNK_BITS)
			
			# mark to continue draining
			if long_value:
				chunk |= self._LONG_BYTE_CONTINUATION_FLAG_MASK
			
			self.write_raw_bytes_chunk(chunk, self._LONG_BYTE_CHUNKS)

	def read_long(self):
		long_value = 0
		chunk = self.read_raw_bytes_chunk(self._LONG_BYTE_CHUNKS)
		
		negative = (chunk & self._LONG_BYTE_NEGATIVE_FLAG_MASK)
		
		long_value |= (chunk & (self._LONG_BYTE_CHUNK_MASK >> 1))
		chunk_bit_offset = (self._LONG_BYTE_CHUNK_BITS-1)
		
		while chunk & self._LONG_BYTE_CONTINUATION_FLAG_MASK:
			chunk = self.read_raw_bytes_chunk(self._LONG_BYTE_CHUNKS)
			long_value |= ((chunk & self._LONG_BYTE_CHUNK_MASK) << chunk_bit_offset)
			chunk_bit_offset += self._LONG_BYTE_CHUNK_BITS
		
		if negative:
			long_value *= -1
		
		return long_value



class CompressedLongHandler(RawBytesChunkHandler):
	# Many applications will never ever get to large values, but _might_.
	# So this uses the smallest byte chunking, focusing on 'wasting' a bit
	# every byte with the assumption that most of the time at least one of
	# the default 3 bytes is wasted as zero.
	def write_long_compressed(self, long_value):
		
		negative = long_value < 0
		# encode as positive, but flag later as negative
		# dealing with chained bytes as well as 
		if negative:
			long_value *= -1
		
		# process first chunk of long given
		chunk = long_value & (127 >> 1) # less one for sign
		
		if negative:
			chunk |= 64
	
		# first chunk drains one less bit due to sign big
		long_value = (long_value >> (7 - 1))
		
		if long_value:
			chunk |= 128
		
		self.write_raw_bytes_chunk(chunk, 1)
		
		while long_value:
			chunk = long_value & 127
			long_value = (long_value >> 7)
			
			# mark to continue draining
			if long_value:
				chunk |= 128
			
			self.write_raw_bytes_chunk(chunk, 1)

	def read_long_compressed(self):
		long_value = 0
		chunk = self.read_raw_bytes_chunk(1)
		
		negative = (chunk & 64)
		
		long_value |= (chunk & (127 >> 1))
		chunk_bit_offset = (7-1)
		
		while chunk & 128:
			chunk = self.read_raw_bytes_chunk(1)
			long_value |= ((chunk & 127) << chunk_bit_offset)
			chunk_bit_offset += 7
		
		if negative:
			long_value *= -1
		
		return long_value



class FloatHandler(StreamHandler):

	# Class properties to let engine be tuned or subclass overridden
	_FLOAT_STRUCT_WRITE_CODE = '!d'
	_FLOAT_STRUCT_READ_BYTES = 8

	def write_float(self, float_value):
		self.write_to_stream(struct.pack(self._FLOAT_STRUCT_WRITE_CODE, float_value)) # assume double

	def read_float(self):
		raw_bytes = self.read_from_stream(self._FLOAT_STRUCT_READ_BYTES)
		return struct.unpack(self._FLOAT_STRUCT_WRITE_CODE, raw_bytes)[0]



class ComplexHandler(FloatHandler):

	def write_complex(self, complex_number):
		self.write_float(complex_number.real) 
		self.write_float(complex_number.imag)

	def read_complex(self):
		return complex(self.read_float(),self.read_float())



# include in opposite order of their dependence to prevent MRO confusion
class NumericHandlers(
		ComplexHandler,
		FloatHandler,
		LongHandler,
		IntHandler,
		ShortHandler,
		BoolHandler,
	): pass



##############################################################################
##
## The following works for arbitrarily large UNSIGNED long integers
##
#
#_MASK_7_BITS = (128-1) #  0b01111111
#_MASK_8_BYTES = ((1<<64)-1)
#
#
#def cast_long_to_bytes(x):
#   prefix = ''
#   
#   # check if we need to chain more bytes to describe the length
#   if x>>7:
#       bit_chunks = [x & _MASK_7_BITS]
#       x = x>>7
#       while x:
#           bit_chunks[-1] += (1<<7) # flag the chain continues
#           bit_chunks.append(x & _MASK_7_BITS)
#           x = x>>7
#       for b in bit_chunks:
#           prefix += chr(b) # struct.pack('!B', b)
#   else:
#       prefix += chr(x) # struct.pack('!B', x)
#   return prefix
#
#
#def drain_1_byte_from_stream(stream):
#   return ord(stream.read(1)) # struct.unpack('!B', stream.read(1))[0]
#   
#
#def cast_bytes_to_long(stream):
#   bit_chunks = [drain_1_byte_from_stream(stream)]
#   
#   while bit_chunks[-1]>>7: # drain while flag signals another byte
#       bit_chunks.append(drain_1_byte_from_stream(stream))
#   x = 0
#   for offset, b in enumerate(bit_chunks):
#       x |= (b & _MASK_7_BITS) << (7*offset)
#   return x
#   
