import piexif
from PIL import Image
import dms

def extract_exif_data(file_path):
    try:
        image = Image.open(file_path)
        exif_dict = piexif.load(image.info['exif'])
        # Remove thumbnail data from EXIF because its format is not compatible with piexif
        exif_dict.pop('thumbnail', None)
        return exif_dict
    except Exception as e:
        print(f"Error loading EXIF data for {file_path}: {e}")
        raise e

def format_exif_data(exif_dict):
    metadata = []
    for ifd in exif_dict:
        for tag in exif_dict[ifd]:
            tag_name = piexif.TAGS[ifd][tag]["name"]
            tag_value = exif_dict[ifd][tag]
            metadata.append(f"{tag_name}: {tag_value}")
    metadata.sort()
    return "\n".join(metadata)

def extract_gps_data(file_path):
    image = Image.open(file_path)
    exif_dict = piexif.load(image.info['exif'])
    gps_ifd = exif_dict.get('GPS', {})
    lat = dms.convert_from_dms(gps_ifd.get(piexif.GPSIFD.GPSLatitude, ((0, 1), (0, 1), (0, 1))))
    lon = dms.convert_from_dms(gps_ifd.get(piexif.GPSIFD.GPSLongitude, ((0, 1), (0, 1), (0, 1))))
    return lat, lon

def update_image_gps_exif(file_path, gps_data):
    image = Image.open(file_path)
    exif_dict = piexif.load(image.info['exif'])
    exif_dict = update_exif_gps(exif_dict, gps_data)
    exif_bytes = piexif.dump(exif_dict)
    image.save(file_path, "jpeg", exif=exif_bytes)

def update_exif_gps(exif_dict, gps_data):
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: 'N' if gps_data['lat'] >= 0 else 'S',
        piexif.GPSIFD.GPSLatitude: dms.convert_to_dms(abs(gps_data['lat'])),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if gps_data['lon'] >= 0 else 'W',
        piexif.GPSIFD.GPSLongitude: dms.convert_to_dms(abs(gps_data['lon'])),
    }
    exif_dict['GPS'] = gps_ifd
    return exif_dict

# Get offset time data from EXIF of given image file. Return empty string if not found.
def get_offset_time_data(file_path):
    image = Image.open(file_path)
    exif_ifd = piexif.load(image.info['exif']).get('Exif', {})
    if (exif_ifd.get(piexif.ExifIFD.OffsetTimeOriginal) is not None):
        offset_time_byte = exif_ifd[piexif.ExifIFD.OffsetTimeOriginal]
        return offset_time_byte.decode('utf-8')
    else:
        return ''


def update_image_offset_time_exif(file_path, offset_time):
    image = Image.open(file_path)
    exif_dict = piexif.load(image.info['exif'])
    exif_dict = update_exif_offset_time(exif_dict, offset_time)
    exif_bytes = piexif.dump(exif_dict)
    image.save(file_path, "jpeg", exif=exif_bytes)


def update_exif_offset_time(exif_dict, offset_time):
    ifd = 'Exif'

    if ifd not in exif_dict:
        exif_dict[ifd] = {}

    exif_dict[ifd][piexif.ExifIFD.OffsetTimeOriginal] = offset_time.encode('utf-8')
    exif_dict[ifd][piexif.ExifIFD.OffsetTimeDigitized] = offset_time.encode('utf-8')
    return exif_dict
