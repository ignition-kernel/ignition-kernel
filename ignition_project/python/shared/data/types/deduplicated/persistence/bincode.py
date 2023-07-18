


from shared.data.binary.handlers.helper import GenericHandler
from shared.data.binary.bincode import ConsolidatedHandler
from shared.data.binary.handlers.stream import FileStreamHandler
from shared.data.binary.handlers.numeric import LongHandler

from shared.data.types.memo import EnumeratedLookup




class EnumeratedLookupFilePersistenceHandlerMixin(
        FileStreamHandler, 
        GenericHandler,
        LongHandler,
    ):
    
    _LOOKUP_TYPE = EnumeratedLookup

    def __init__(self, filepath, enumerated_lookup=None):
        super(EnumeratedLookupFilePersistenceHandlerMixin, self).__init__(filepath)
        self.next_entry_ix = None
        self.last_read_position = None
        
        self.lookup = enumerated_lookup
        
        # default to the non-destructive mode
        self.mode = 'rb'


    def write(self):
        if self.next_entry_ix is None:
            with self.file_mode('wb'):
                self.write_header()
        with self.file_mode('ab'):
            self.write_entries() 

    def write_header(self):
        self.write_str(self.lookup._instance_label)
        self.write_long(self.lookup.__initialized__)
        self.next_entry_ix = 0

    def write_entries(self):
        # iterate over current instances
        for ix, entry in enumerate(self.lookup.__lookup_table__[self.next_entry_ix:]):
            self.write_entry(entry)
            
            # start on the next one
            self.next_entry_ix += 1
    
    def write_entry(self, entry):
        """Allow subclasses to override and tune how objects are written without clobbering read_object"""
        self.write_object(entry)


    def read(self):
        with self.file_mode('rb'):
            if self.last_read_position is not None:
                self.stream.seek(self.last_read_position)
            header = self.read_header()
            
            self.lookup = self._LOOKUP_TYPE(**header)
            
            self.read_entries()
            
            self.next_entry_ix = len(self.lookup) # len of 0-index is the same as enumerate ix + 1
            self.last_read_position = self.stream.tell()

    def read_header(self):
        return {
            'label': self.read_str(),
            'seed': self.read_long(),
        }

    def read_entries(self):
        # note that this does NOT require the references _actually_ be loaded - the stupid thing can work anyhow,
        # even if it's uselessly so without the magic decoder ring __lookup__ primed =/        
        while True:
            try:
                obj = self.read_entry()
            except EOFError: # end of file - byte read failed
                break
            _ = self.lookup.index(obj)

    def read_entry(self):
        """Allow subclasses to override and tune how objects are read without clobbering read_object"""
        entry = self.read_object()
        return entry


class EnumeratedLookupBincoder(
        EnumeratedLookupFilePersistenceHandlerMixin,
        ConsolidatedHandler
    ):
    pass
    










