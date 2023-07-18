"""
	See the classes at shared.data.types.stats

"""
from shared.data.binary.handlers.numeric import LongHandler, FloatHandler
from shared.data.binary.handlers.helper import UnsignedIntTupleAsLongHandler

from shared.data.types.stats import Histogram, StatisticalDescription


class HistogramHandler(
		FloatHandler,
		UnsignedIntTupleAsLongHandler,
		LongHandler,
	):
	
	def write_histogram(self, histogram):
		assert isinstance(histogram, Histogram)
		self.write_float(histogram.start)
		self.write_float(histogram.stop)
		self.write_float(histogram.step)
		counts = self.encode_long_from_tuple_of_unsigned_ints(
			(histogram.outliers+1,) + tuple(i + 1 for i in histogram.counts)
		)
		self.write_long(counts)
		
	def read_histogram(self):
		start, stop, step = self.read_float(), self.read_float(), self.read_float(),
		outliers_and_counts = self.decode_tuple_of_unsigned_ints_from_long(self.read_long())
		outliers = outliers_and_counts[0] - 1
		counts = tuple(x - 1 for x in outliers_and_counts[1:])
		return Histogram(
			counts=counts,
			outliers=outliers,
			start=start, 
			stop=stop,
			step=step, 
		)


class StatisticalDescriptionHandler(
		FloatHandler,
		LongHandler,
	):
	
	def write_statistical_description(self, sd):
		assert isinstance(sd, StatisticalDescription)
		self.write_long(sd.n)
		for x in 'mean min max span variance stddev sum'.split():
			self.write_float(sd[x])
		
	def read_statistical_description(self):
		return StatisticalDescription(
			*((self.read_long(),) + tuple(self.read_float() 
				for x in 'mean min max span variance stddev sum'.split()
			))
		)




# include in opposite order of their dependence to prevent MRO confusion
class StatsHandler(
		HistogramHandler,
		StatisticalDescriptionHandler,
	): pass






def _run_tests():
	from io import BytesIO
	from StringIO import StringIO
	
	from java.lang import Exception as JavaException
	
	from shared.data.types.stats import Histogram, StatisticalDescription

	entry = {
			"histogram": {
				"counts": [0, 0, 0, 0, 6, 12, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
				"outliers": 0
			},
			"min": 49.5453,
			"max": 51.0179,
			"variance": 0.21236614115789482,
			"mean": 50.35886999999999,
			"sum": 1007.1773999999998,
			"n": 20,
			"standard deviation": 0.460832009693223,
			"span": 1.4726
		}
	
	histogram = Histogram(
		counts=entry['histogram']['counts'], 
		outliers=entry['histogram']['outliers'], 
			**{
				"stop": 95,
				"start": 45,
				"step": 1
			})
	
	sd = StatisticalDescription(**entry)
	
	
	from shared.data.binary.handlers.stats import StatsHandler
	
	stream = BytesIO()
	
	bincoder = StatsHandler()
	bincoder.stream = stream
	
	
	bincoder.write_statistical_description(sd)
	bincoder.write_histogram(histogram)
	
	# reset for read back
	bincoder.stream.seek(0)
	
	sd2 = bincoder.read_statistical_description()
	h2 = bincoder.read_histogram()
	
	
	assert sd2.asdict() == sd.asdict()
	assert h2.asdict() == histogram.asdict()
