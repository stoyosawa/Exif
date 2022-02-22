#!/usr/bin/env python
# 2022-02-22: ST

'''jpeg module - Parse a JPEG file into the segments.

A jpeg file is a concatenation of bytes segments.
Each segment can be broken down into the header and body.
The header consists of
- 2-bytes segment identifier called 'marker' (unsigned int). Must starts from 0xFF.
- 2-bytes body length INCLUDING this 2 bytes (unsigned int)
The rest is the body.

Exceptions are SOI (Start of Image) and EOI (End of Image),
which appear in the beginning and end of the file respectively,
and consist only of markers.

This module ignores actual image (compressed) bytes.

References:
- https://exiftool.org/TagNames/JPEG.html
'''

# Accompanying HSON file that lists the marker int - names (meaning) mappings.
JSON_FILE = 'jpeg.json'

class JpegMarkers():
    '''A container for JPEG markers dict: {value(int): name(str)}'''
    _instance = None
    _markers = None

    def __new__(cls, filename=JSON_FILE):
        '''Create a JPEG marker dict (singleton).
        Note: Only the popular markers are supported (otherwise 'No name').
        '''
        if cls._instance == None:                        # Create just once
            cls._instance = super().__new__(cls)

            import json
            with open(filename) as fp:
                json_jpeg = json.load(fp)
                cls._markers = json_jpeg['markers']
                # print(cls._markers)                    # debug

        return cls._instance


    def get_name(self, marker):
        '''Get the JPEG marker string name from hex-string value (e.g., FFD8).
        'marker' is a four-char hex string with no leading 0x and uppercased.
        '''
        try:
            return self._markers[marker]
        except:
            return f'No name ({marker})'


    def get_names_all(self):
        '''Return all the JPEG markers (dict).'''
        return self._markers



class JpegSegment():
    '''A container for one JPEG segment.
    It's main members are:
    - marker_int: JPEG marker id in int.
    - length: The length of the segment
    - data: The data (its length is 'length' above).
    '''

    def __init__(self,
            marker,            # marker (int).
            length,            # data length (original length - 2)
            data               # Segment data (excluding marker & length) (bytes)
        ):
        marker_dict = JpegMarkers()
        self.marker_int = marker
        self.marker_hex = f'{marker:04X}'                # Uppercase
        self.marker_name = marker_dict.get_name(self.marker_hex)
        self.length = length
        self.data = data

    def __len__(self):
        '''Return the byte size of the body.
        e.g., for APP1/Exif, data starts from Exif ID.
        len(self.data) = self.length.
        '''
        return len(self.data)


    def __str__(self):
        return str(self.get_dict())


    def get_dict(self):
        '''Returns the dict for this object excluding data '''
        return {
            'marker_int': self.marker_int,
            'marker_hex': self.marker_hex,
            'marker_name': self.marker_name,
            'length': self.length,            
        }

    def get_dict_brief(self):
        '''Same as get_dict but only return the marker_int and length.'''
        return {
            'marker_int': self.marker_int,
            'length': self.length
        }


    def get_data(self):
        '''Returns the data part of the segment (starting from 'Exif\0\0' in APP1).'''
        return 



class JpegStruct():
    '''Break a JPEF file into segments.
    Raises Exception when
    1) The file is not present.
    2) The file does not start from SOI (FFD8).
    '''

    def __init__(self, filename):
        # fields
        self.count = 0                                   # #segments
        self.filename = filename                         # filename
        self.segments = []                               # a list of segment objs.

        with open(filename, 'rb') as fp:
            # If the first bytes are not SOI, raise exception.
            soi = int.from_bytes(fp.read(2), byteorder='big', signed=False)
            if soi != 0xFFD8:
                raise Exception('Missing SOI. Not a JPEG file.')

            # Loop around each segment
            while True:
                marker = int.from_bytes(fp.read(2), byteorder='big', signed=False)
                if marker == 0xFFD9:                     # End of Image. End.
                    break
                if marker <= 0xFF00:                     # Not a marker segment
                    break

                # The length field includes itself.
                length = int.from_bytes(fp.read(2), byteorder='big', signed=False) - 2
                data = fp.read(length)

                self.segments.append(
                    JpegSegment(marker, length, data)
                )
                self.count += 1


    def __str__(self):
        text = []
        for i in range(self.count):
            text.append(str(self.segments[i]))
        return '\n'.join(text)


    def get_segment(self, marker):
        '''Get the segment by marker (int).
        When there are mutiple segments with the same marker, it returns the first one.
        Returns None if not found.
        '''
        # A list of markers for finding the index of the segment
        marker_list = [self.segments[i].marker_int for i in range(self.count)]
        try:
            index = marker_list.index(marker)
            return self.segments[index]
        except:
            return None



if __name__ == '__main__':
    '''For testing'''
    from sys import argv

    # Read the JPEG file.
    jpeg = JpegStruct(argv[1])
    print(jpeg)

    # Try extracting APP1 (Exif) segment.
    exif = jpeg.get_segment(0xFFE1)
    print('Exif: ', exif)

    # Try extracting APP0 (Jfif) segment.
    jfif = jpeg.get_segment(0xFFE0)
    print('Jfif: ', jfif)

    # Try extracting unknown segment.
    unknown = jpeg.get_segment(0xFF01)
    print('Unknown(FF01): ', unknown)
