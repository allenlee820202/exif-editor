import os
import sys
from PIL import Image
import piexif

def update_gps_data(exif_dict, gps_data):
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: 'N' if gps_data['lat'] >= 0 else 'S',
        piexif.GPSIFD.GPSLatitude: convert_to_dms(abs(gps_data['lat'])),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if gps_data['lon'] >= 0 else 'W',
        piexif.GPSIFD.GPSLongitude: convert_to_dms(abs(gps_data['lon'])),
    }
    exif_dict['GPS'] = gps_ifd
    return exif_dict

def convert_to_dms(value):
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = int(((value - degrees) * 60 - minutes) * 60 * 100)
    return ((degrees, 1), (minutes, 1), (seconds, 100))

def process_image(file_path, gps_data):
    image = Image.open(file_path)
    exif_dict = piexif.load(image.info['exif'])
    exif_dict = update_gps_data(exif_dict, gps_data)
    exif_bytes = piexif.dump(exif_dict)
    image.save(file_path, "jpeg", exif=exif_bytes)

def batch_process_images(directory, gps_data):
    for filename in os.listdir(directory):
        if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
            file_path = os.path.join(directory, filename)
            process_image(file_path, gps_data)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python edit-exif.py <directory> <latitude> <longitude>")
        sys.exit(1)

    directory = sys.argv[1]
    gps_data = {
        'lat': float(sys.argv[2]),
        'lon': float(sys.argv[3])
    }

    batch_process_images(directory, gps_data)
    print("Batch processing completed.")