import piexif
from PIL import Image

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
