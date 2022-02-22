#!/usr/bin/env python
# 2022-02-22: ST

'''Exif parser.

An Exif block consits of:
- Exif ID (6 bytes) ... Always b'Exif\x00\x00'.
- Tiff header (8). It consists of:
    - Byte order (2). Either 4949 ('little') or 4D4D ('big').
    - 002A (2). Always this value.
    - Offset (4). The byte position of the top of IDF field (which is IFD count), counging from the top of Tiff header. Normally 0008.
- IFD counts (2)
- IFDs. They are described in the Ifd class.
'''
from ifd import Ifd

class ByteOrder:
    '''Translate Tiff byte order in int to Python's endian string.
    Returns None if neither 4949 or 4D4D.
    '''

    _instance = None
    _byte_orders = {
        b'\x4D\x4D': 'big',
        b'\x49\x49': 'little'
    }

    def __new__(cls):
        if cls._instance == None:
            cls._instance = super().__new__(cls)

        return cls._instance


    def get_byte_order(self, two_bytes):
        ''' Get the byte order string ('big' or 'little') from 2-bytes bytes.
        Returns None the bytes is corrupted.
        '''
        try:
            return self._byte_orders[two_bytes]
        except:
            return None


class Exif:
    '''Represents Exif segment.'''

    def __init__(self, app1_data):
        ''' Parse the APP1 data (entire APP1 segment minus APP1 marker and Length).
        Raises exception when:
        1) The Exif ID is not b'Exif\x00\x00'.
        2) The Byte Order field is not 4949 (little) or 4D4D (big)
        3) The 002A field is not 002A.
        '''
        # fields
        self.byte_order = None                           # 'big' or 'little'
        self.offset = 0                                  # Offset "FROM the top of app1_data" to the 0th IFD. 
        self.ifd_count = 0                               # A number of IFD fields
        self.ifd_fields = []                             # Ifd objects
        self.data = app1_data                            # Reference to the app1_data (starting from Exif ID)

        # The 1st 6 bytes is the Exif Identifier. The information is not stored here.
        # If not, raise Exception
        exif_identifier = app1_data[:6]
        if exif_identifier != b'Exif\x00\x00':
            raise Exception(f'Not a valid Exif segment. Wrong Exif Identifier: {app1_data[:6]}')

        # Tiff header 1st field: Byte order (2 bytes).
        byte_order = ByteOrder()
        self.byte_order = byte_order.get_byte_order(app1_data[6:8])
        if self.byte_order == None:
            raise Exception(f'Not a valid Exif segment. Wrong byte order: {app1_data[6:8]}')

        # Tiff header 2nd field (2 bytes): 002A. The information is not stored here.
        twoA = int.from_bytes(app1_data[8:10], self.byte_order)
        if twoA != 0x002A:
            raise Exception(f'Not a valid Exif segment. Wrong 002A: {app1_data[8:10]}')

        # Tiff header 3rd field (2 bytes): Offset
        # The original offset counts from the beginning of Byte Order.
        # For convenience, I count from the Exif identifier (the beginning of this app1_data), so add additional 6.
        self.offset = int.from_bytes(app1_data[10:14], self.byte_order) + 6

        # A number of IFD counts
        self.ifd_count = int.from_bytes(app1_data[14:16], self.byte_order)

        # The rest is IFD fields
        for idx in range(self.ifd_count):
            ifd = Ifd(idx, self.byte_order, self.data)
            self.ifd_fields.append(ifd.get_dict_brief())


    def __str__(self):
        return str(self.get_dict())


    def get_dict(self):
        ''' Returns all the members except data in dict format.'''
        return {
            'Byte order': self.byte_order,
            'Offset': self.offset,
            'IFD count': self.ifd_count,
            'IFDs': self.ifd_fields
        }

    def get_dict_tiff(self):
        ''' Return 3 fields Tiff header '''
        return {
            'Byte order': self.byte_order,
            'Offset': self.offset,
            'IFD count': self.ifd_count
        }

    def get_ifds(self):
        ''' Return IFD fields in an array '''
        return self.ifd_fields



if __name__ == '__main__':
    ''' For testing '''
    from jpeg import JpegStruct
    from sys import argv

    # Read a JPEG file and parse into segments
    jpeg = JpegStruct(argv[1])

    # Extract Exif segment (marker, length, exif ID, ..., data)
    app1_segment = jpeg.get_segment(0xFFE1)

    # Parse the Exif data
    exif = Exif(app1_segment.data)
    print(exif.get_dict_tiff())
    for idx, ifd in enumerate(exif.get_ifds()):
        print(f'#{idx}: {ifd}')
