enum PhotoSort { name, creationTime, datetimeOriginal }

extension PhotoSortMapping on PhotoSort {
  String get apiValue {
    switch (this) {
      case PhotoSort.name:
        return 'name';
      case PhotoSort.creationTime:
        return 'creation_time';
      case PhotoSort.datetimeOriginal:
        return 'datetime_original';
    }
  }

  String get label {
    switch (this) {
      case PhotoSort.name:
        return 'Name';
      case PhotoSort.creationTime:
        return 'Creation Time';
      case PhotoSort.datetimeOriginal:
        return 'DateTimeOriginal';
    }
  }
}

class PhotoSummary {
  PhotoSummary({
    required this.filePath,
    required this.name,
    required this.ctime,
    required this.datetimeOriginal,
  });

  final String filePath;
  final String name;
  final double ctime;
  final String datetimeOriginal;

  factory PhotoSummary.fromJson(Map<String, dynamic> json) {
    return PhotoSummary(
      filePath: json['file_path'] as String,
      name: json['name'] as String,
      ctime: (json['ctime'] as num).toDouble(),
      datetimeOriginal: (json['datetime_original'] as String?) ?? '',
    );
  }
}

class PhotoDetails {
  PhotoDetails({
    required this.filePath,
    required this.exifText,
    required this.latitude,
    required this.longitude,
    required this.timezoneOffset,
    required this.datetimeOriginal,
  });

  final String filePath;
  final String exifText;
  final double latitude;
  final double longitude;
  final String timezoneOffset;
  final String datetimeOriginal;

  factory PhotoDetails.fromJson(Map<String, dynamic> json) {
    return PhotoDetails(
      filePath: json['file_path'] as String,
      exifText: json['exif_text'] as String,
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      timezoneOffset: (json['timezone_offset'] as String?) ?? '',
      datetimeOriginal: (json['datetime_original'] as String?) ?? '',
    );
  }
}

class BatchActionResult {
  BatchActionResult({
    required this.updatedCount,
    required this.failedPaths,
    required this.errors,
  });

  final int updatedCount;
  final List<String> failedPaths;
  final List<String> errors;

  factory BatchActionResult.fromJson(Map<String, dynamic> json) {
    return BatchActionResult(
      updatedCount: json['updated_count'] as int,
      failedPaths: (json['failed_paths'] as List<dynamic>)
          .map((item) => item as String)
          .toList(),
      errors: (json['errors'] as List<dynamic>)
          .map((item) => item as String)
          .toList(),
    );
  }
}

class LocationGps {
  LocationGps({
    required this.lat,
    required this.lon,
    required this.semanticType,
    required this.probability,
    required this.timeDiffMinutes,
  });

  final double lat;
  final double lon;
  final String semanticType;
  final String probability;
  final int timeDiffMinutes;

  factory LocationGps.fromJson(Map<String, dynamic> json) {
    return LocationGps(
      lat: (json['lat'] as num).toDouble(),
      lon: (json['lon'] as num).toDouble(),
      semanticType: json['semantic_type'] as String,
      probability: (json['probability'] as String?) ?? '1.0',
      timeDiffMinutes: json['time_diff_minutes'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'lat': lat,
      'lon': lon,
      'semantic_type': semanticType,
      'probability': probability,
      'time_diff_minutes': timeDiffMinutes,
    };
  }
}

class LocationMatch {
  LocationMatch({
    required this.filePath,
    required this.filename,
    required this.timestamp,
    required this.gps,
  });

  final String filePath;
  final String filename;
  final String timestamp;
  final LocationGps gps;

  factory LocationMatch.fromJson(Map<String, dynamic> json) {
    return LocationMatch(
      filePath: json['file_path'] as String,
      filename: json['filename'] as String,
      timestamp: json['timestamp'] as String,
      gps: LocationGps.fromJson(json['gps'] as Map<String, dynamic>),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'file_path': filePath,
      'filename': filename,
      'timestamp': timestamp,
      'gps': gps.toJson(),
    };
  }
}
