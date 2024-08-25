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
