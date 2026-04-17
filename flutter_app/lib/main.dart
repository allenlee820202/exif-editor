import 'dart:math' as math;
import 'dart:ui';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'backend_client.dart';
import 'models.dart';

const String _defaultBackendUrl = String.fromEnvironment(
  'BACKEND_BASE_URL',
  defaultValue: 'http://127.0.0.1:8765',
);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ExifEditorApp());
}

class ExifEditorApp extends StatelessWidget {
  const ExifEditorApp({super.key});

  @override
  Widget build(BuildContext context) {
    const accent = Color(0xFF2BAE66);
    final colorScheme = ColorScheme.fromSeed(
      seedColor: accent,
      brightness: Brightness.dark,
      surface: const Color(0xFF23282D),
    );

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'EXIF Editor Flutter',
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: colorScheme,
        fontFamily: 'Avenir Next',
        scaffoldBackgroundColor: Colors.transparent,
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0x4D1B2024),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0x55FFFFFF)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0x44FFFFFF)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: accent, width: 1.3),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 12,
            vertical: 12,
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: accent,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            textStyle: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.white,
            side: const BorderSide(color: Color(0x88FFFFFF)),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ),
      home: const ExifEditorHomePage(backendBaseUrl: _defaultBackendUrl),
    );
  }
}

class ExifEditorHomePage extends StatefulWidget {
  const ExifEditorHomePage({super.key, required this.backendBaseUrl});

  final String backendBaseUrl;

  @override
  State<ExifEditorHomePage> createState() => _ExifEditorHomePageState();
}

class _ExifEditorHomePageState extends State<ExifEditorHomePage> {
  late final BackendClient _client;

  final TextEditingController _gpsController = TextEditingController();
  final TextEditingController _timezoneController = TextEditingController();
  final TextEditingController _datetimeOffsetController =
      TextEditingController();
  final TextEditingController _folderController = TextEditingController();
  final TextEditingController _locationFileController = TextEditingController();

  bool _checkingBackend = false;
  bool _backendReady = false;
  bool _loadingPhotos = false;
  bool _loadingDetails = false;
  bool _runningBatchAction = false;
  bool _processingLocationHistory = false;

  String _statusText = 'Checking local Python backend...';
  String? _selectedFolder;
  String? _locationHistoryFile;

  List<PhotoSummary> _photos = <PhotoSummary>[];
  Set<String> _selectedPaths = <String>{};
  String? _activePath;
  PhotoDetails? _photoDetails;
  PhotoSort _sortBy = PhotoSort.datetimeOriginal;

  int _photoRequestToken = 0;
  int _detailsRequestToken = 0;
  int _imageRevision = 0;

  bool get _isAnyOperationRunning =>
      _checkingBackend ||
      _loadingPhotos ||
      _runningBatchAction ||
      _processingLocationHistory ||
      _loadingDetails;

  @override
  void initState() {
    super.initState();
    _client = BackendClient(baseUrl: widget.backendBaseUrl);
    _initializeBackend();
  }

  @override
  void dispose() {
    _gpsController.dispose();
    _timezoneController.dispose();
    _datetimeOffsetController.dispose();
    _folderController.dispose();
    _locationFileController.dispose();
    _client.dispose();
    super.dispose();
  }

  Future<bool> _ensureBackendReady() async {
    if (_backendReady) {
      return true;
    }
    await _initializeBackend();
    return _backendReady;
  }

  String _photoImageUrl(String filePath) {
    final base = Uri.parse(widget.backendBaseUrl);
    final uri = base.replace(
      path: '/photos/image',
      queryParameters: <String, String>{
        'path': filePath,
        'v': '$_imageRevision',
      },
    );
    return uri.toString();
  }

  Future<void> _setSelectedFolder(String folder) async {
    final normalized = folder.trim();
    if (normalized.isEmpty) {
      _showSnack('Enter a photo folder path first.', isError: true);
      return;
    }

    setState(() {
      _selectedFolder = normalized;
      _folderController.text = normalized;
      _photos = <PhotoSummary>[];
      _selectedPaths = <String>{};
      _activePath = null;
      _photoDetails = null;
    });

    await _refreshPhotos();
  }

  Future<void> _applyFolderFromInput() async {
    if (!await _ensureBackendReady()) {
      return;
    }
    await _setSelectedFolder(_folderController.text);
  }

  Future<void> _initializeBackend() async {
    setState(() {
      _checkingBackend = true;
      _statusText = 'Connecting to ${widget.backendBaseUrl} ...';
    });

    try {
      await _client.checkHealth();
      if (!mounted) {
        return;
      }
      setState(() {
        _backendReady = true;
        _statusText = 'Backend connected. Ready to edit EXIF metadata.';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _backendReady = false;
        _statusText =
            'Backend unavailable. Start `uv run python flutter_backend.py` or use scripts/dev-flutter-web.sh.';
      });
      _showSnack(error.toString(), isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _checkingBackend = false;
        });
      }
    }
  }

  Future<void> _selectFolder() async {
    if (!await _ensureBackendReady()) {
      return;
    }
    if (kIsWeb) {
      try {
        final pickedPath = await _client.pickFolderPath();
        await _setSelectedFolder(pickedPath);
      } catch (error) {
        if (error.toString().contains('Selection cancelled')) {
          return;
        }
        _showSnack(error.toString(), isError: true);
      }
      return;
    }
    final folder = await getDirectoryPath(
      confirmButtonText: 'Select Photo Folder',
    );
    if (folder == null) {
      return;
    }
    await _setSelectedFolder(folder);
  }

  Future<void> _refreshPhotos() async {
    final folder = _selectedFolder;
    if (!_backendReady || folder == null || folder.isEmpty) {
      return;
    }

    final requestToken = ++_photoRequestToken;
    setState(() {
      _loadingPhotos = true;
    });

    try {
      final photos = await _client.listPhotos(folder: folder, sortBy: _sortBy);
      if (!mounted || requestToken != _photoRequestToken) {
        return;
      }

      _folderController.text = folder;

      final validPaths = photos.map((photo) => photo.filePath).toSet();
      final preservedSelection = _selectedPaths
          .where(validPaths.contains)
          .toSet();

      String? activePath;
      if (_activePath != null && validPaths.contains(_activePath)) {
        activePath = _activePath;
      } else if (preservedSelection.isNotEmpty) {
        activePath = preservedSelection.first;
      } else if (photos.isNotEmpty) {
        activePath = photos.first.filePath;
        preservedSelection.add(activePath);
      }

      setState(() {
        _photos = photos;
        _selectedPaths = preservedSelection;
        _activePath = activePath;
      });

      if (activePath != null) {
        await _loadPhotoDetails(activePath);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      _showSnack(error.toString(), isError: true);
    } finally {
      if (mounted && requestToken == _photoRequestToken) {
        setState(() {
          _loadingPhotos = false;
        });
      }
    }
  }

  Future<void> _loadPhotoDetails(String filePath) async {
    if (!_backendReady) {
      return;
    }

    final requestToken = ++_detailsRequestToken;
    setState(() {
      _loadingDetails = true;
    });

    try {
      final details = await _client.photoDetails(filePath);
      if (!mounted || requestToken != _detailsRequestToken) {
        return;
      }
      setState(() {
        _photoDetails = details;
      });
      _gpsController.text =
          '${details.latitude.toStringAsFixed(6)}, ${details.longitude.toStringAsFixed(6)}';
      _timezoneController.text = details.timezoneOffset;
    } catch (error) {
      if (!mounted || requestToken != _detailsRequestToken) {
        return;
      }
      _showSnack(error.toString(), isError: true);
    } finally {
      if (mounted && requestToken == _detailsRequestToken) {
        setState(() {
          _loadingDetails = false;
        });
      }
    }
  }

  void _openPhoto(PhotoSummary photo) {
    setState(() {
      _activePath = photo.filePath;
      _selectedPaths.add(photo.filePath);
    });
    _loadPhotoDetails(photo.filePath);
  }

  void _togglePhotoSelection(String filePath) {
    setState(() {
      if (_selectedPaths.contains(filePath)) {
        _selectedPaths.remove(filePath);
      } else {
        _selectedPaths.add(filePath);
      }

      if (_selectedPaths.isEmpty) {
        _activePath = null;
        _photoDetails = null;
      } else if (_activePath == null || !_selectedPaths.contains(_activePath)) {
        _activePath = _selectedPaths.first;
      }
    });

    final activePath = _activePath;
    if (activePath != null) {
      _loadPhotoDetails(activePath);
    }
  }

  void _selectAllPhotos() {
    if (_photos.isEmpty) {
      return;
    }

    setState(() {
      _selectedPaths = _photos.map((photo) => photo.filePath).toSet();
      _activePath ??= _photos.first.filePath;
    });
    if (_activePath != null) {
      _loadPhotoDetails(_activePath!);
    }
  }

  void _clearSelection() {
    setState(() {
      _selectedPaths.clear();
      _activePath = null;
      _photoDetails = null;
    });
  }

  _GpsInput? _parseGpsInput(String value) {
    final parts = value.split(',');
    if (parts.length != 2) {
      return null;
    }
    final lat = double.tryParse(parts[0].trim());
    final lon = double.tryParse(parts[1].trim());
    if (lat == null || lon == null) {
      return null;
    }
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      return null;
    }
    return _GpsInput(lat: lat, lon: lon);
  }

  bool _isOffsetValid(String value) {
    final trimmed = value.trim();
    final pattern = RegExp(r'^[+-]\d{2}:\d{2}$');
    if (!pattern.hasMatch(trimmed)) {
      return false;
    }
    final hours = int.tryParse(trimmed.substring(1, 3));
    final minutes = int.tryParse(trimmed.substring(4, 6));
    if (hours == null || minutes == null) {
      return false;
    }
    return hours <= 23 && minutes <= 59;
  }

  Future<void> _runBatchOperation({
    required Future<BatchActionResult> Function(List<String> paths) action,
    required String successMessage,
  }) async {
    if (_selectedPaths.isEmpty) {
      _showSnack('Select at least one photo first.', isError: true);
      return;
    }

    setState(() {
      _runningBatchAction = true;
    });

    try {
      final result = await action(_selectedPaths.toList());
      if (!mounted) {
        return;
      }

      if (result.failedPaths.isEmpty) {
        _showSnack('$successMessage (${result.updatedCount} photos).');
      } else {
        _showSnack(
          '$successMessage partially completed: ${result.updatedCount} updated, ${result.failedPaths.length} failed.',
          isError: true,
        );
      }
      setState(() {
        _imageRevision += 1;
      });
      await _refreshPhotos();
    } catch (error) {
      if (!mounted) {
        return;
      }
      _showSnack(error.toString(), isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _runningBatchAction = false;
        });
      }
    }
  }

  Future<void> _updateGps() async {
    final parsed = _parseGpsInput(_gpsController.text.trim());
    if (parsed == null) {
      _showSnack('Invalid GPS format. Use "lat, lon".', isError: true);
      return;
    }

    await _runBatchOperation(
      action: (paths) =>
          _client.updateGps(filePaths: paths, lat: parsed.lat, lon: parsed.lon),
      successMessage: 'GPS update complete',
    );
  }

  Future<void> _updateTimezone() async {
    final offset = _timezoneController.text.trim();
    if (!_isOffsetValid(offset)) {
      _showSnack('Invalid offset. Use "[+-]HH:MM".', isError: true);
      return;
    }

    await _runBatchOperation(
      action: (paths) =>
          _client.updateTimezone(filePaths: paths, offset: offset),
      successMessage: 'Timezone update complete',
    );
  }

  Future<void> _updateDateTimeOffset() async {
    final offset = _datetimeOffsetController.text.trim();
    if (!_isOffsetValid(offset)) {
      _showSnack('Invalid offset. Use "[+-]HH:MM".', isError: true);
      return;
    }

    await _runBatchOperation(
      action: (paths) =>
          _client.updateDateTimeOffset(filePaths: paths, offset: offset),
      successMessage: 'Date/time offset update complete',
    );
  }

  Future<void> _loadLocationHistoryPreview() async {
    if (_photos.isEmpty) {
      _showSnack('Load a photo folder first.', isError: true);
      return;
    }

    if (!await _ensureBackendReady()) {
      return;
    }

    if (kIsWeb) {
      String typedPath = _locationFileController.text.trim();
      if (typedPath.isEmpty) {
        try {
          typedPath = await _client.pickLocationHistoryPath();
          _locationFileController.text = typedPath;
        } catch (error) {
          if (error.toString().contains('Selection cancelled')) {
            return;
          }
          _showSnack(error.toString(), isError: true);
          return;
        }
      }
      if (typedPath.isEmpty) {
        _showSnack('Enter location-history JSON path first.', isError: true);
        return;
      }
      setState(() {
        _processingLocationHistory = true;
        _locationHistoryFile = typedPath;
        _locationFileController.text = typedPath;
      });
    } else {
      const jsonGroup = XTypeGroup(label: 'JSON', extensions: <String>['json']);
      final file = await openFile(acceptedTypeGroups: <XTypeGroup>[jsonGroup]);
      if (file == null) {
        return;
      }
      setState(() {
        _processingLocationHistory = true;
        _locationHistoryFile = file.path;
        _locationFileController.text = file.path;
      });
    }

    try {
      final matches = await _client.previewLocationHistory(
        locationFile: _locationHistoryFile!,
        photoFiles: _photos.map((photo) => photo.filePath).toList(),
      );

      if (!mounted) {
        return;
      }

      if (matches.isEmpty) {
        _showSnack('No matching location points found for current photos.');
        return;
      }

      final confirmed =
          await showDialog<bool>(
            context: context,
            barrierDismissible: false,
            builder: (context) => _LocationPreviewDialog(
              matches: matches,
              backendBaseUrl: widget.backendBaseUrl,
              imageRevision: _imageRevision,
            ),
          ) ??
          false;

      if (!confirmed || !mounted) {
        return;
      }

      final applyResult = await _client.applyLocationMatches(matches);
      if (!mounted) {
        return;
      }

      if (applyResult.failedPaths.isEmpty) {
        _showSnack(
          'Applied location history to ${applyResult.updatedCount} photos.',
        );
      } else {
        _showSnack(
          'Applied to ${applyResult.updatedCount} photos with ${applyResult.failedPaths.length} failures.',
          isError: true,
        );
      }
      setState(() {
        _imageRevision += 1;
      });
      await _refreshPhotos();
    } catch (error) {
      if (!mounted) {
        return;
      }
      _showSnack(error.toString(), isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _processingLocationHistory = false;
        });
      }
    }
  }

  void _showSnack(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w600,
          ),
        ),
        backgroundColor: isError
            ? const Color(0xFF7F1D1D)
            : const Color(0xFF22543D),
      ),
    );
  }

  Widget _buildStatusPanel() {
    final statusColor = _backendReady
        ? const Color(0xFF2BAE66)
        : const Color(0xFFEAB308);
    return GlassPanel(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: <Widget>[
          Icon(
            _backendReady
                ? Icons.cloud_done_rounded
                : Icons.warning_amber_rounded,
            color: statusColor,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _statusText,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
            ),
          ),
          const SizedBox(width: 12),
          OutlinedButton.icon(
            onPressed: _checkingBackend ? null : _initializeBackend,
            icon: _checkingBackend
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh_rounded),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildControlsPanel() {
    return GlassPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _PanelHeading(
            icon: Icons.tune_rounded,
            title: 'Control Center',
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              Expanded(
                child: TextField(
                  controller: _folderController,
                  decoration: InputDecoration(
                    hintText: kIsWeb
                        ? '/absolute/path/to/photos'
                        : 'No photo folder selected',
                  ),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: _isAnyOperationRunning ? null : _selectFolder,
                icon: const Icon(Icons.folder_open_rounded),
                label: const Text('Browse'),
              ),
              if (kIsWeb) ...<Widget>[
                const SizedBox(width: 8),
                OutlinedButton(
                  onPressed: _isAnyOperationRunning
                      ? null
                      : _applyFolderFromInput,
                  child: const Text('Use Path'),
                ),
              ],
              const SizedBox(width: 8),
              IconButton(
                tooltip: 'Reload photos',
                onPressed: (_loadingPhotos || _selectedFolder == null)
                    ? null
                    : _refreshPhotos,
                icon: const Icon(Icons.sync_rounded),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              DropdownButton<PhotoSort>(
                value: _sortBy,
                borderRadius: BorderRadius.circular(12),
                items: PhotoSort.values
                    .map(
                      (sort) => DropdownMenuItem<PhotoSort>(
                        value: sort,
                        child: Text(sort.label),
                      ),
                    )
                    .toList(),
                onChanged: _loadingPhotos
                    ? null
                    : (sort) {
                        if (sort == null) {
                          return;
                        }
                        setState(() {
                          _sortBy = sort;
                        });
                        _refreshPhotos();
                      },
              ),
              _CounterBadge(label: 'Photos', value: _photos.length),
              _CounterBadge(label: 'Selected', value: _selectedPaths.length),
              OutlinedButton(
                onPressed: _photos.isEmpty ? null : _selectAllPhotos,
                child: const Text('Select all'),
              ),
              OutlinedButton(
                onPressed: _selectedPaths.isEmpty ? null : _clearSelection,
                child: const Text('Clear selection'),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _ActionEditor(
            title: 'GPS Coordinates (lat, lon)',
            controller: _gpsController,
            hintText: '37.7749, -122.4194',
            buttonLabel: 'Update GPS',
            onPressed: _isAnyOperationRunning ? null : _updateGps,
          ),
          const SizedBox(height: 10),
          _ActionEditor(
            title: 'Time Zone Offset',
            controller: _timezoneController,
            hintText: '+08:00',
            buttonLabel: 'Update Time Zone',
            onPressed: _isAnyOperationRunning ? null : _updateTimezone,
          ),
          const SizedBox(height: 10),
          _ActionEditor(
            title: 'Local DateTime Offset',
            controller: _datetimeOffsetController,
            hintText: '-01:30',
            buttonLabel: 'Apply Date Offset',
            onPressed: _isAnyOperationRunning ? null : _updateDateTimeOffset,
          ),
          const SizedBox(height: 10),
          Row(
            children: <Widget>[
              Expanded(
                child: TextField(
                  controller: _locationFileController,
                  decoration: InputDecoration(
                    hintText: kIsWeb
                        ? '/absolute/path/to/location-history.json'
                        : (_locationHistoryFile ??
                              'No location history file selected'),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              ElevatedButton.icon(
                onPressed: _isAnyOperationRunning
                    ? null
                    : _loadLocationHistoryPreview,
                icon: _processingLocationHistory
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.travel_explore_rounded),
                label: const Text('Load Location History'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPhotoBrowserPanel() {
    return GlassPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const _PanelHeading(
                icon: Icons.grid_view_rounded,
                title: 'Photo Browser',
              ),
              const Spacer(),
              if (_loadingPhotos)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: _photos.isEmpty
                ? const Center(
                    child: Text(
                      'Select a folder to load JPG/JPEG photos.',
                      style: TextStyle(color: Color(0xB3FFFFFF)),
                    ),
                  )
                : LayoutBuilder(
                    builder: (context, constraints) {
                      final columns = math.max(
                        2,
                        (constraints.maxWidth / 180).floor(),
                      );
                      return GridView.builder(
                        itemCount: _photos.length,
                        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: columns,
                          mainAxisSpacing: 10,
                          crossAxisSpacing: 10,
                          childAspectRatio: 0.78,
                        ),
                        itemBuilder: (context, index) {
                          final photo = _photos[index];
                          return _PhotoTile(
                            photo: photo,
                            isSelected: _selectedPaths.contains(photo.filePath),
                            isActive: _activePath == photo.filePath,
                            imageUrl: _photoImageUrl(photo.filePath),
                            onOpen: () => _openPhoto(photo),
                            onToggleSelection: () =>
                                _togglePhotoSelection(photo.filePath),
                          );
                        },
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailsPanel() {
    final details = _photoDetails;
    final activePath = _activePath;

    return GlassPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const _PanelHeading(
                icon: Icons.preview_rounded,
                title: 'Preview & EXIF',
              ),
              const Spacer(),
              if (_loadingDetails)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (activePath == null)
            const Expanded(
              child: Center(
                child: Text(
                  'Open a photo to inspect metadata.',
                  style: TextStyle(color: Color(0xB3FFFFFF)),
                ),
              ),
            )
          else
            Expanded(
              child: LayoutBuilder(
                builder: (context, panelConstraints) {
                  final previewHeight = math.min(
                    300.0,
                    math.max(140.0, panelConstraints.maxHeight * 0.40),
                  );

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      SizedBox(
                        width: double.infinity,
                        height: previewHeight,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(14),
                          child: Image.network(
                            _photoImageUrl(activePath),
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) =>
                                Container(
                                  color: const Color(0xAA1C2126),
                                  alignment: Alignment.center,
                                  child: const Text(
                                    'Unable to load image preview',
                                  ),
                                ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: <Widget>[
                          _DataChip(
                            label: 'Latitude',
                            value: (details?.latitude ?? 0).toStringAsFixed(6),
                          ),
                          _DataChip(
                            label: 'Longitude',
                            value: (details?.longitude ?? 0).toStringAsFixed(6),
                          ),
                          _DataChip(
                            label: 'Offset',
                            value: details?.timezoneOffset.isNotEmpty == true
                                ? details!.timezoneOffset
                                : 'N/A',
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'DateTimeOriginal: ${details?.datetimeOriginal.isNotEmpty == true ? details!.datetimeOriginal : 'N/A'}',
                        style: const TextStyle(
                          color: Color(0xD9FFFFFF),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Expanded(
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0x4020282D),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0x44FFFFFF)),
                          ),
                          child: SingleChildScrollView(
                            child: SelectableText(
                              details?.exifText ?? 'Loading EXIF metadata...',
                              style: const TextStyle(height: 1.4, fontSize: 12),
                            ),
                          ),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          const _AtmosphereBackground(),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final compact = constraints.maxWidth < 1180;

                  if (compact) {
                    return Column(
                      children: <Widget>[
                        _StaggerReveal(delay: 0, child: _buildStatusPanel()),
                        const SizedBox(height: 12),
                        Expanded(
                          child: ListView(
                            children: <Widget>[
                              _StaggerReveal(
                                delay: 80,
                                child: _buildControlsPanel(),
                              ),
                              const SizedBox(height: 12),
                              SizedBox(
                                height: math.max(
                                  320,
                                  constraints.maxHeight * 0.55,
                                ),
                                child: _StaggerReveal(
                                  delay: 160,
                                  child: _buildPhotoBrowserPanel(),
                                ),
                              ),
                              const SizedBox(height: 12),
                              SizedBox(
                                height: math.max(
                                  320,
                                  constraints.maxHeight * 0.55,
                                ),
                                child: _StaggerReveal(
                                  delay: 240,
                                  child: _buildDetailsPanel(),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    );
                  }

                  return Column(
                    children: <Widget>[
                      _StaggerReveal(delay: 0, child: _buildStatusPanel()),
                      const SizedBox(height: 12),
                      Expanded(
                        child: Row(
                          children: <Widget>[
                            Expanded(
                              flex: 7,
                              child: Column(
                                children: <Widget>[
                                  _StaggerReveal(
                                    delay: 80,
                                    child: _buildControlsPanel(),
                                  ),
                                  const SizedBox(height: 12),
                                  Expanded(
                                    child: _StaggerReveal(
                                      delay: 160,
                                      child: _buildPhotoBrowserPanel(),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              flex: 5,
                              child: _StaggerReveal(
                                delay: 240,
                                child: _buildDetailsPanel(),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AtmosphereBackground extends StatelessWidget {
  const _AtmosphereBackground();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xFF161A1E),
            Color(0xFF1D2429),
            Color(0xFF262D34),
          ],
        ),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Positioned(
            top: -120,
            right: -80,
            child: _GlowBlob(size: 320, color: const Color(0x6634D399)),
          ),
          Positioned(
            left: -70,
            bottom: -110,
            child: _GlowBlob(size: 260, color: const Color(0x5538BDF8)),
          ),
        ],
      ),
    );
  }
}

class _GlowBlob extends StatelessWidget {
  const _GlowBlob({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ImageFiltered(
      imageFilter: ImageFilter.blur(sigmaX: 40, sigmaY: 40),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(size),
        ),
      ),
    );
  }
}

class GlassPanel extends StatelessWidget {
  const GlassPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(14),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: const Color(0x66252B31),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0x4DFFFFFF)),
            boxShadow: const <BoxShadow>[
              BoxShadow(
                color: Color(0x33000000),
                blurRadius: 24,
                offset: Offset(0, 12),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}

class _PanelHeading extends StatelessWidget {
  const _PanelHeading({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Icon(icon, size: 20, color: const Color(0xFFD1FAE5)),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
        ),
      ],
    );
  }
}

class _CounterBadge extends StatelessWidget {
  const _CounterBadge({required this.label, required this.value});

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0x3D2BAE66),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0x8034D399)),
      ),
      child: Text(
        '$label: $value',
        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
      ),
    );
  }
}

class _ActionEditor extends StatelessWidget {
  const _ActionEditor({
    required this.title,
    required this.controller,
    required this.hintText,
    required this.buttonLabel,
    this.onPressed,
  });

  final String title;
  final TextEditingController controller;
  final String hintText;
  final String buttonLabel;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Row(
          children: <Widget>[
            Expanded(
              child: TextField(
                controller: controller,
                decoration: InputDecoration(hintText: hintText),
              ),
            ),
            const SizedBox(width: 10),
            ElevatedButton(onPressed: onPressed, child: Text(buttonLabel)),
          ],
        ),
      ],
    );
  }
}

class _PhotoTile extends StatelessWidget {
  const _PhotoTile({
    required this.photo,
    required this.isSelected,
    required this.isActive,
    required this.imageUrl,
    required this.onOpen,
    required this.onToggleSelection,
  });

  final PhotoSummary photo;
  final bool isSelected;
  final bool isActive;
  final String imageUrl;
  final VoidCallback onOpen;
  final VoidCallback onToggleSelection;

  @override
  Widget build(BuildContext context) {
    final borderColor = isActive
        ? const Color(0xFF34D399)
        : isSelected
        ? const Color(0xFF10B981)
        : const Color(0x66FFFFFF);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor, width: isActive ? 2 : 1),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0x40262F36), Color(0x66202930)],
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onOpen,
          borderRadius: BorderRadius.circular(16),
          child: Stack(
            children: <Widget>[
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  Expanded(
                    child: ClipRRect(
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(15),
                      ),
                      child: Image.network(
                        imageUrl,
                        fit: BoxFit.cover,
                        filterQuality: FilterQuality.medium,
                        errorBuilder: (context, error, stackTrace) => Container(
                          color: const Color(0x6620282F),
                          alignment: Alignment.center,
                          child: const Icon(
                            Icons.broken_image_rounded,
                            color: Color(0x99FFFFFF),
                          ),
                        ),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          photo.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          photo.datetimeOriginal.isNotEmpty
                              ? photo.datetimeOriginal
                              : 'No DateTimeOriginal',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 11,
                            color: Color(0xCCFFFFFF),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              Positioned(
                top: 8,
                right: 8,
                child: GestureDetector(
                  onTap: onToggleSelection,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 26,
                    height: 26,
                    decoration: BoxDecoration(
                      color: isSelected
                          ? const Color(0xE62BAE66)
                          : const Color(0xAA13191E),
                      borderRadius: BorderRadius.circular(26),
                      border: Border.all(color: const Color(0xB3FFFFFF)),
                    ),
                    child: Icon(
                      isSelected ? Icons.check_rounded : Icons.add_rounded,
                      size: 16,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DataChip extends StatelessWidget {
  const _DataChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: const Color(0x332BAE66),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0x552BAE66)),
      ),
      child: Text(
        '$label: $value',
        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class _LocationPreviewDialog extends StatelessWidget {
  const _LocationPreviewDialog({
    required this.matches,
    required this.backendBaseUrl,
    required this.imageRevision,
  });

  final List<LocationMatch> matches;
  final String backendBaseUrl;
  final int imageRevision;

  String _formatTimestamp(String value) {
    final parsed = DateTime.tryParse(value);
    if (parsed == null) {
      return value;
    }
    return parsed.toLocal().toString().split('.').first;
  }

  String _photoImageUrl(String filePath) {
    final base = Uri.parse(backendBaseUrl);
    final uri = base.replace(
      path: '/photos/image',
      queryParameters: <String, String>{
        'path': filePath,
        'v': '$imageRevision',
      },
    );
    return uri.toString();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final width = math.min(size.width * 0.88, 980.0);
    final height = math.min(size.height * 0.86, 700.0);

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(20),
      child: SizedBox(
        width: width,
        height: height,
        child: GlassPanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const _PanelHeading(
                icon: Icons.map_rounded,
                title: 'Location Preview',
              ),
              const SizedBox(height: 6),
              Text(
                'Found ${matches.length} matched photos. Confirm to write GPS metadata.',
                style: const TextStyle(color: Color(0xCCFFFFFF)),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: const Color(0x4020282D),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0x44FFFFFF)),
                  ),
                  child: ListView.separated(
                    itemCount: matches.length,
                    separatorBuilder: (context, index) =>
                        const Divider(height: 1, color: Color(0x33FFFFFF)),
                    itemBuilder: (context, index) {
                      final match = matches[index];
                      return ListTile(
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 6,
                        ),
                        leading: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: SizedBox(
                            width: 62,
                            height: 62,
                            child: Image.network(
                              _photoImageUrl(match.filePath),
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) =>
                                  Container(
                                    color: const Color(0x3320282D),
                                    alignment: Alignment.center,
                                    child: const Icon(
                                      Icons.broken_image_rounded,
                                      size: 18,
                                      color: Color(0x99FFFFFF),
                                    ),
                                  ),
                            ),
                          ),
                        ),
                        title: Text(
                          match.filename,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: Text(
                          '${_formatTimestamp(match.timestamp)}  |  ${match.gps.semanticType}',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        trailing: Text(
                          '${match.gps.lat.toStringAsFixed(5)}, ${match.gps.lon.toStringAsFixed(5)}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Color(0xFFD1FAE5),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: <Widget>[
                  OutlinedButton(
                    onPressed: () => Navigator.of(context).pop(false),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: () => Navigator.of(context).pop(true),
                    child: const Text('Confirm & Apply'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StaggerReveal extends StatefulWidget {
  const _StaggerReveal({required this.delay, required this.child});

  final int delay;
  final Widget child;

  @override
  State<_StaggerReveal> createState() => _StaggerRevealState();
}

class _StaggerRevealState extends State<_StaggerReveal> {
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    Future<void>.delayed(Duration(milliseconds: widget.delay), () {
      if (!mounted) {
        return;
      }
      setState(() {
        _visible = true;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSlide(
      duration: const Duration(milliseconds: 450),
      curve: Curves.easeOutCubic,
      offset: _visible ? Offset.zero : const Offset(0, 0.03),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 450),
        curve: Curves.easeOut,
        opacity: _visible ? 1 : 0,
        child: widget.child,
      ),
    );
  }
}

class _GpsInput {
  _GpsInput({required this.lat, required this.lon});

  final double lat;
  final double lon;
}
