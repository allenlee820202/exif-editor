import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class BackendException implements Exception {
  BackendException(this.message);
  final String message;

  @override
  String toString() => message;
}

class BackendClient {
  BackendClient({required this.baseUrl, http.Client? client})
    : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _client.get(_uri(path));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      String message = 'Request failed with status ${response.statusCode}';
      try {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        final detail = body['detail'];
        if (detail is String && detail.isNotEmpty) {
          message = detail;
        }
      } catch (_) {
        if (response.body.isNotEmpty) {
          message = response.body;
        }
      }
      throw BackendException(message);
    }

    if (response.body.isEmpty) {
      return <String, dynamic>{};
    }

    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw BackendException('Unexpected response format.');
    }
    return decoded;
  }

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> payload,
  ) async {
    final response = await _client.post(
      _uri(path),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      String message = 'Request failed with status ${response.statusCode}';
      try {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        final detail = body['detail'];
        if (detail is String && detail.isNotEmpty) {
          message = detail;
        }
      } catch (_) {
        if (response.body.isNotEmpty) {
          message = response.body;
        }
      }
      throw BackendException(message);
    }

    if (response.body.isEmpty) {
      return <String, dynamic>{};
    }

    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw BackendException('Unexpected response format.');
    }
    return decoded;
  }

  Future<void> checkHealth() async {
    final response = await _client.get(_uri('/health'));
    if (response.statusCode != 200) {
      throw BackendException(
        'Backend health check failed (${response.statusCode}).',
      );
    }
  }

  Future<String> pickFolderPath() async {
    final json = await _get('/picker/folder');
    final path = json['path'];
    if (path is! String || path.isEmpty) {
      throw BackendException('No folder path was returned.');
    }
    return path;
  }

  Future<String> pickLocationHistoryPath() async {
    final json = await _get('/picker/location-history-file');
    final path = json['path'];
    if (path is! String || path.isEmpty) {
      throw BackendException('No file path was returned.');
    }
    return path;
  }

  Future<List<PhotoSummary>> listPhotos({
    required String folder,
    required PhotoSort sortBy,
  }) async {
    final json = await _post('/photos/list', {
      'folder': folder,
      'sort_by': sortBy.apiValue,
    });

    final photosJson = json['photos'] as List<dynamic>? ?? [];
    return photosJson
        .map((entry) => PhotoSummary.fromJson(entry as Map<String, dynamic>))
        .toList();
  }

  Future<PhotoDetails> photoDetails(String filePath) async {
    final json = await _post('/photos/details', {'file_path': filePath});
    return PhotoDetails.fromJson(json);
  }

  Future<BatchActionResult> updateGps({
    required List<String> filePaths,
    required double lat,
    required double lon,
  }) async {
    final json = await _post('/photos/update-gps', {
      'file_paths': filePaths,
      'lat': lat,
      'lon': lon,
    });
    return BatchActionResult.fromJson(json);
  }

  Future<BatchActionResult> updateTimezone({
    required List<String> filePaths,
    required String offset,
  }) async {
    final json = await _post('/photos/update-timezone', {
      'file_paths': filePaths,
      'offset': offset,
    });
    return BatchActionResult.fromJson(json);
  }

  Future<BatchActionResult> updateDateTimeOffset({
    required List<String> filePaths,
    required String offset,
  }) async {
    final json = await _post('/photos/update-datetime-offset', {
      'file_paths': filePaths,
      'offset': offset,
    });
    return BatchActionResult.fromJson(json);
  }

  Future<List<LocationMatch>> previewLocationHistory({
    required String locationFile,
    required List<String> photoFiles,
  }) async {
    final json = await _post('/location-history/preview', {
      'location_file': locationFile,
      'photo_files': photoFiles,
    });

    final matchesJson = json['matches'] as List<dynamic>? ?? [];
    return matchesJson
        .map((entry) => LocationMatch.fromJson(entry as Map<String, dynamic>))
        .toList();
  }

  Future<BatchActionResult> applyLocationMatches(
    List<LocationMatch> matches,
  ) async {
    final json = await _post('/location-history/apply', {
      'matches': matches.map((match) => match.toJson()).toList(),
    });
    return BatchActionResult.fromJson(json);
  }

  void dispose() {
    _client.close();
  }
}
