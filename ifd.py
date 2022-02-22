#!/usr/bin/env python
# 2022-02-17: Satoshi Toyosawa

import fractions

# Accompanying JSON file that lists the data types (BYTES, ASCII, etc) and IFD tags.
JSON_FILE = 'ifd.json'


# Conversion functions for a various types
# They all have the same signature, intentionally

def _bytes_to_bytes(b, endian='big', signed=False):      # endian, signed not necessary
    return b

def _bytes_to_int(b, endian='big', signed=False):
    return int.from_bytes(b, byteorder=endian, signed=signed)

def _bytes_to_string(b, endian='big', signed=False):
    return b.decode(encoding='utf-8')[:-1]               # Remove the \0 at the end

def _bytes_to_fraction(b, endian='big', signed=False):
    numerator = int.from_bytes(b[0:4], byteorder=endian)
    denominator = int.from_bytes(b[4:8], byteorder=endian)
    return fractions.Fraction(numerator, denominator)



class IfdInfo():
    ''' Descriptions of IFD Type and Tags fields.
    The accompanying JSON file lists all the IFD types listed in the Exif 2.3 spec.
    For more. see https://exiftool.org/TagNames/EXIF.html.
    '''
    _instance = None                                     # This instance
    _ifd_types = None                                    # dict: loaded from file
    _ifd_tags = None                                     # ditto

    def __new__(cls, filename=JSON_FILE):
        if cls._instance == None:                        # Create just once
            cls._instance = super().__new__(cls)

            import json
            with open(filename) as fp:
                json_ifd = json.load(fp)
                cls._ifd_types = json_ifd['types']       # dict
                cls._ifd_tags = json_ifd['tags']         # dict
                # print(cls._ifd_types)                  # Debug
                # print(cls._ifd_tags)                   # Debug

        return cls._instance                             # Return this class instance


    def get_ifd_tag_by_id(self, tag_id):
        ''' Get the tag name from intefer tag_id
        Note that IfdInfo._ifd_tags is indexed by four hex degit WITHOUT leading 0x.
        '''
        hex_nox = f'{tag_id:04X}'                        # Must be upper-case
        if hex_nox not in self._ifd_tags:
            return None
        else:
            return self._ifd_tags[hex_nox]


    def get_ifd_type_by_id(self, type_id):
        str_id = str(type_id)
        if str_id not in self._ifd_types:
            return None
        else:
            return self._ifd_types[str_id]


class Ifd():

    def __init__(self, index, endian, app1_data):
        """ Initialize from Exif (APP1) block """

        # Fields
        self.index = -1                                  # i-th IFD block
        self.endian = endian                             # 'big' or 'little' (from Exif header)
        self.tag_int = 0                                 # Tag number. int.
        self.tag_name = None                             # Tag name. str.
        self.type_int = 0                                # Type number. int.
        self.type_dict = None                            # Type description. {name, type, length, signed}
        self.count = 0                                   # A number of values here.
        self.offset_bytes = None                         # The pointer to the value. COUNTED from the Exif idenfiier here!! In Bytes format.
        self.data = app1_data                            # APP1 data bytes (Starting from Exif\0\0)

        # Instanciate IFD information table
        ifd_info = IfdInfo()

        # The starting byte (in the app1_data) of the i-th field is calculated as below because
        # - Exif identifier: 6 bytes
        # - Tiff header: 8 bytes (Tag 2 + Type 2 + Count 4)
        # - IFD counts: 2 bytes
        # - One IFD field is 12 bytes
        pos = 12 * index + 16

        # Tag (2 bytes; int and string)
        self.tag_int = int.from_bytes(app1_data[pos:pos+2], byteorder=endian)
        self.tag_name = ifd_info.get_ifd_tag_by_id(self.tag_int)

        # Type (2 bytes; int and dict)
        self.type_int = int.from_bytes(app1_data[pos+2:pos+4], byteorder=endian)
        self.type_dict = ifd_info.get_ifd_type_by_id(self.type_int)

        # Count (4 bytes; int)
        self.count = int.from_bytes(app1_data[pos+4:pos+8], byteorder=endian)

        # Offset (4 bytes; read as bytes)
        self.offset_bytes = app1_data[pos+8:pos+12]      # Bytes
        self.value = self._read_value_from_offset()


    def get_dict(self):
        ''' Returns all the members except the byte data. '''
        return {
            'tag_int': self.tag_int,
            'tag_name': self.tag_name,
            'type_int': self.type_int,
            'type_dict': self.type_dict,
            'count': self.count,
            'offset': self.offset_bytes,
            'value': self.value
        }

    def get_dict_brief(self):
        ''' Returns only the essential members '''
        return {
            'tag': self.tag_name,
            'type': self.type_dict['name'],
            'value': self.value
        }

    def __str__(self):
        return f'{self.tag_name} ({self.type_dict["name"]}): {self.value}'


    def _read_value_from_offset(self):
        ''' Return the byte value the offset is pointing to.
        The offset field contains the actual value IF it fits into this 4 bytes space.
        Otherwise, the location where the offset is pointing to.
        '''
        value_size = self.count * self.type_dict['length']

        # Which way do you go?
        if value_size <= 4: 
            b = self.offset_bytes[:value_size]           # Inside the offset
        else:
            offset = int.from_bytes(self.offset_bytes, byteorder=self.endian) + 6    # add 6 for 'exif\0\0'
            b = self.data[offset:offset+value_size]

        # I need to know if it were signed.
        try:
            signed = self.type_dict['signed']
        except:
            signed = None                                # Dummy

        return Ifd._bytes_to_value(
                b,                                       # Bytes to parse
                self.type_dict['type'],                  # data type
                self.endian,                             # 'big' or 'little'
                signed                                   # True if signed. Only for int.
            )


    def _bytes_to_value(b, dtype, endian, signed):
        ''' A private function to convert the bytes into the specific data type.
        The following functions are intentionally given the same signature irrespectively.
        '''

        caller = {
            'bytes': _bytes_to_bytes,
            'string': _bytes_to_string,
            'int': _bytes_to_int,
            'Fraction': _bytes_to_fraction,
        }
        return caller[dtype](b, endian, signed)



if __name__ == '__main__':
    """ For testing. """
    from sys import argv
    from jpeg import JpegStruct
    from exif import Exif

    # Read the JPEG file and parse.
    jpeg = JpegStruct(argv[1]) 

    # Get the Exif segment
    app1_segment = jpeg.get_segment(0xFFE1)
    print(f'APP1 segment read. {len(app1_segment)} bytes')

    # app1_segment.data starts from Exif ID. Parse it.
    exif = Exif(app1_segment.data)
    byte_order = exif.byte_order
    print(f'Found {exif.ifd_count} IFDs. Byte Order: {byte_order}')

    # loop around
    for idx in range(exif.ifd_count):
        ifd = Ifd(idx, byte_order, exif.data)
        print(f'#{idx}:{ifd}')
