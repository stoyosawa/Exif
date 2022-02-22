#!/usr/bin/env python
# 2022-02-22: ST

'''jfif module - Parse the JFIF APP0 segment (obtained from jpeg module).

References: 
- https://hp.vector.co.jp/authors/VA032610/JPEGFormat/marker/APP0JFIF.htm (in Japanese)
- https://en.wikipedia.org/wiki/JPEG_File_Interchange_Format
- https://www.w3.org/Graphics/JPEG/jfif3.pdf
'''

class Jfif:
    '''Jfif decoder (APP0 = 0xFFE0).
    Ignores the thumbnail section.
    '''

    UNITS = [
        'No units',
        'dots per inch',
        'dots per cm'
    ]

    def get_unit(index):
        '''Returns the unit for {X, Y}density in string (see UNITS above).'''
        try:
            return Jfif.UNITS[index]
        except:
            return f'Wrong unit ({index})'


    def __init__(self, app0_data):
        '''app0_data (bytes) = APP0 segment - (APP0 marker + APP0 length)'''

        # The ints are all unsinged and big-endian (spec does not clearly say so, though)
        endian = 'big'

        # 0-4th bytes (5 bytes): Jfif Identifier (string).
        jfif_identifier = app0_data[:5]
        if jfif_identifier != b'JFIF\x00':
            raise Exception(f'Not a valid Jdid segment. Wrong Jfif Identifier: {app0_data[:5]}')

        # 5-6th bytes (2): Version. 5th major, 6th minor. Both int. Converted to "major.minor" string.
        self.version = str(app0_data[5]) + '.' + str(app0_data[6])

        # 7th (1): The units for Xdensity, Ydensity. One of [0, 1, 2]. Converts to a string.
        self.units = Jfif.get_unit(app0_data[7])

        # 8-11th (4): Xdensity and Ydensity, 2 bytes each.
        self.Xdensity = int.from_bytes(app0_data[8:10], endian)
        self.Ydensity = int.from_bytes(app0_data[10:12], endian)

        # 12-13th (4): Xthumbnail、Ythumbnail sizes. int. (0, 0) if there is no thumbnail.
        self.Xthumbnail = app0_data[12]
        self.Ythumbnail = app0_data[13]

        # 14th-: Normally thumbnail image data follows.
        # However, some implementation (e.g., Apple iPhone 12) write "AMPF" (41 4D 50 46) in 14-17th bytes.
        # Couldn't find the spec for this mysterious field.

        # Thumbnail image date (may include AMPF)
        if self.Xthumbnail * self.Ythumbnail == 0:
            self.thumbnail = None
        else:
            self.thumbnail = app0_data[14:]


    def get_dict(self):
        '''Returns the members in dict format. Except thumbnail image data.'''
        return {
            'version': self.version,
            'Units': self.units,
            'Xdensity': self.Xdensity,
            'Ydensity': self.Ydensity,
            'Xthumbnail': self.Xthumbnail,
            'Ythumbnail': self.Ythumbnail
            # 'Thumbnail': self.thumbnail
        }

    def __str__(self):
        return str(self.get_dict())



if __name__ == '__main__':
    '''For test.'''
    from jpeg import JpegStruct
    from sys import argv
    import os

    # Test all the Jpeg files under a specified directory.
    for file in os.listdir(argv[1]):
        if os.path.splitext(file)[1].lower() != '.jpg':
            continue
        print(f'{file}... ', end='')

        # Read the Jpeg file and parse into segments.
        jpeg_segment = JpegStruct(os.path.join(argv[1], file))
        print(f'{jpeg_segment.count} segments... ', end='')

        # Extract Jfif segment (marker = FFE0). None if not present.
        app0_data = jpeg_segment.get_segment(0xFFE0)
        if app0_data == None:
            print('No APP0')
            continue
    
        # Jfif content.
        try:
            jfif = Jfif(app0_data.data)
            print(jfif)
        except:
            print('Looks like not Jfif. Skipped.')
