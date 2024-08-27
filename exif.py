import piexif
from PIL import Image
import datetime

def get_datetime_original(file_path):
    return piexif.load(file_path).get('Exif', {}).get(piexif.ExifIFD.DateTimeOriginal, '')

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
    lat = convert_from_dms(gps_ifd.get(piexif.GPSIFD.GPSLatitude, ((0, 1), (0, 1), (0, 1))))
    lon = convert_from_dms(gps_ifd.get(piexif.GPSIFD.GPSLongitude, ((0, 1), (0, 1), (0, 1))))
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
        piexif.GPSIFD.GPSLatitude: convert_to_dms(abs(gps_data['lat'])),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if gps_data['lon'] >= 0 else 'W',
        piexif.GPSIFD.GPSLongitude: convert_to_dms(abs(gps_data['lon'])),
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

def get_exif_date_time_original(file_path):
    image = Image.open(file_path)
    exif_dict = piexif.load(image.info['exif'])
    return exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')

def update_local_date_time_by_offset(file_path, local_date_time_offset):
    image = Image.open(file_path)
    exif_dict = piexif.load(image.info['exif'])
    exif_dict = update_exif_local_date_time_by_offset(exif_dict, local_date_time_offset)
    exif_bytes = piexif.dump(exif_dict)
    image.save(file_path, "jpeg", exif=exif_bytes)

def update_exif_local_date_time_by_offset(exif_dict, local_date_time_offset):
    ifd = 'Exif'

    exif_dict[ifd][piexif.ExifIFD.DateTimeOriginal] = calculate_new_date_time_by_offset(exif_dict[ifd][piexif.ExifIFD.DateTimeOriginal].decode('utf-8'), local_date_time_offset).encode('utf-8')
    exif_dict[ifd][piexif.ExifIFD.DateTimeDigitized] = calculate_new_date_time_by_offset(exif_dict[ifd][piexif.ExifIFD.DateTimeDigitized].decode('utf-8'), local_date_time_offset).encode('utf-8')
    return exif_dict

# original_date_time: YYYY:MM:DD HH:MM:SS
# offset: [+-]HH:MM
def calculate_new_date_time_by_offset(original_date_time, offset):
    original_dt = datetime.datetime.strptime(original_date_time, '%Y:%m:%d %H:%M:%S')
    offset_dt = datetime.timedelta(hours=int(offset[:3]), minutes=int(offset[4:]))
    return (original_dt + offset_dt).strftime('%Y:%m:%d %H:%M:%S')

def convert_from_dms(dms):
    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1] / 60
    seconds = dms[2][0] / dms[2][1] / 3600
    return degrees + minutes + seconds

def convert_to_dms(value):
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = int(((value - degrees) * 60 - minutes) * 60 * 100)
    return ((degrees, 1), (minutes, 1), (seconds, 100))
