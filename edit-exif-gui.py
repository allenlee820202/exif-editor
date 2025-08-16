import os
import json
import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QComboBox, QTextEdit, QSplitter, QProgressBar, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QSize, Qt, QThread, pyqtSignal, QTimer
import exif

class ThumbnailLoader(QThread):
    thumbnail_ready = pyqtSignal(str, QPixmap, dict)
    loading_progress = pyqtSignal(int, int)
    
    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self.should_stop = False
        
    def run(self):
        total_files = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            if self.should_stop:
                break
                
            try:
                # Create thumbnail more efficiently using PIL directly
                from PIL import Image
                from PyQt5.QtGui import QImage
                with Image.open(file_path) as img:
                    img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                    # Convert PIL image to QPixmap
                    img_rgb = img.convert('RGB')
                    h, w, ch = img_rgb.size[1], img_rgb.size[0], 3
                    bytes_per_line = ch * w
                    qimg = QImage(img_rgb.tobytes(), w, h, bytes_per_line, QImage.Format_RGB888)
                    thumbnail = QPixmap.fromImage(qimg)
                    
                # Load basic file info (no EXIF yet - lazy load)
                file_dict = {
                    'file_path': file_path, 
                    'name': os.path.basename(file_path), 
                    'ctime': os.path.getctime(file_path)
                }
                
                self.thumbnail_ready.emit(file_path, thumbnail, file_dict)
                self.loading_progress.emit(i + 1, total_files)
                
            except Exception as e:
                print(f"Error loading thumbnail for {file_path}: {e}")
                continue
                
    def stop(self):
        self.should_stop = True

class LocationHistoryProcessor(QThread):
    processing_progress = pyqtSignal(int, int)
    processing_complete = pyqtSignal(list)
    
    def __init__(self, location_file, photo_files, time_range):
        super().__init__()
        self.location_file = location_file
        self.photo_files = photo_files
        self.time_range = time_range
        
    def run(self):
        try:
            # Load and filter location history
            with open(self.location_file, 'r') as f:
                location_data = json.load(f)
            
            # Filter locations within time range
            filtered_locations = []
            start_time, end_time = self.time_range
            
            for entry in location_data:
                entry_time = self.parse_time(entry.get('startTime', ''))
                if entry_time and start_time <= entry_time <= end_time:
                    filtered_locations.append(entry)
            
            # Calculate GPS for each photo
            photo_gps_data = []
            total_photos = len(self.photo_files)
            
            for i, file_path in enumerate(self.photo_files):
                try:
                    # Get photo timestamp
                    photo_time = self.get_photo_timestamp(file_path)
                    if photo_time:
                        # Find closest location
                        gps_coords = self.find_closest_location(photo_time, filtered_locations)
                        if gps_coords:
                            photo_gps_data.append({
                                'file_path': file_path,
                                'timestamp': photo_time,
                                'gps': gps_coords,
                                'filename': os.path.basename(file_path)
                            })
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                
                self.processing_progress.emit(i + 1, total_photos)
            
            self.processing_complete.emit(photo_gps_data)
            
        except Exception as e:
            print(f"Error processing location history: {e}")
            self.processing_complete.emit([])
    
    def parse_time(self, time_str):
        """Parse ISO time string to datetime object"""
        try:
            # Handle format: "2013-07-21T18:20:06.088+08:00"
            if time_str:
                # Remove microseconds and parse
                time_str = time_str.split('.')[0] + time_str[-6:]
                return datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except Exception:
            pass
        return None
    
    def get_photo_timestamp(self, file_path):
        """Extract timestamp from photo EXIF data"""
        try:
            datetime_str = exif.get_exif_date_time_original(file_path)
            timezone_offset = exif.get_offset_time_data(file_path)
            timestamp = None
            if datetime_str:
                timestamp = datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
            if timezone_offset:
                # timezone_offset looks like "+08:00" or "-05:00"
                # Parse sign, hours, and minutes from the offset string
                sign = 1 if timezone_offset[0] == '+' else -1
                hours = int(timezone_offset[1:3])
                minutes = int(timezone_offset[4:6])
                offset = datetime.timedelta(hours=sign * hours, minutes=sign * minutes)
                timestamp = timestamp.replace(tzinfo=datetime.timezone(offset))
            return timestamp
        except Exception:
            # Fallback to file modification time
            try:
                return datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            except Exception:
                pass
        return None
    
    def find_closest_location(self, photo_time, locations):
        """Find the closest location entry to photo timestamp"""
        closest_location = None
        min_time_diff = float('inf')
        
        for entry in locations:
            entry_time = self.parse_time(entry.get('startTime', ''))
            if not entry_time:
                continue
                
            time_diff = abs((photo_time - entry_time).total_seconds())
            if time_diff >= min_time_diff:
                continue
            
            # Handle 'visit' entries
            if 'visit' in entry and 'topCandidate' in entry['visit']:
                candidate = entry['visit']['topCandidate']
                if 'placeLocation' in candidate:
                    geo_str = candidate['placeLocation']
                    if geo_str.startswith('geo:'):
                        coords = geo_str[4:].split(',')
                        if len(coords) == 2:
                            try:
                                lat, lon = float(coords[0]), float(coords[1])
                                min_time_diff = time_diff
                                closest_location = {
                                    'lat': lat,
                                    'lon': lon,
                                    'semantic_type': f"Visit: {candidate.get('semanticType', 'Unknown')}",
                                    'probability': candidate.get('probability', '0'),
                                    'time_diff_minutes': int(time_diff / 60)
                                }
                            except ValueError:
                                continue
            
            # Handle 'activity' entries
            elif 'activity' in entry:
                activity = entry['activity']
                geo_str = None
                activity_type = 'Unknown'
                
                # Get activity type from topCandidate
                if 'topCandidate' in activity and 'type' in activity['topCandidate']:
                    activity_type = activity['topCandidate']['type']
                
                # Try to get location from start first, then end
                if 'start' in activity:
                    geo_str = activity['start']
                elif 'end' in activity:
                    geo_str = activity['end']
                
                if geo_str and geo_str.startswith('geo:'):
                    coords = geo_str[4:].split(',')
                    if len(coords) == 2:
                        try:
                            lat, lon = float(coords[0]), float(coords[1])
                            min_time_diff = time_diff
                            closest_location = {
                                'lat': lat,
                                'lon': lon,
                                'semantic_type': f"Activity: {activity_type}",
                                'probability': '1.0',  # Activities are definitive locations
                                'time_diff_minutes': int(time_diff / 60)
                            }
                        except ValueError:
                            continue
        
        return closest_location

class LocationPreviewDialog(QDialog):
    def __init__(self, photo_gps_data, parent=None):
        super().__init__(parent)
        self.photo_gps_data = photo_gps_data
        self.confirmed = False
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('GPS Location Preview')
        self.setModal(True)
        self.resize(900, 600)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel(f'Found GPS data for {len(self.photo_gps_data)} photos. Review before applying:')
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(header_label)
        
        # Table to show photo and GPS data
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Thumbnail', 'Filename', 'Timestamp', 'Latitude', 'Longitude', 'Location Type'])
        self.table.setRowCount(len(self.photo_gps_data))
        
        # Configure table
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Populate table
        for row, data in enumerate(self.photo_gps_data):
            # Thumbnail
            thumbnail_label = QLabel()
            try:
                pixmap = QPixmap(data['file_path'])
                thumbnail = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                thumbnail_label.setPixmap(thumbnail)
            except Exception:
                thumbnail_label.setText('No preview')
            thumbnail_label.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 0, thumbnail_label)
            
            # File info
            self.table.setItem(row, 1, QTableWidgetItem(data['filename']))
            self.table.setItem(row, 2, QTableWidgetItem(data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')))
            
            # GPS data
            gps = data['gps']
            self.table.setItem(row, 3, QTableWidgetItem(f"{gps['lat']:.6f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{gps['lon']:.6f}"))
            
            # Location type with time difference
            location_info = f"{gps['semantic_type']} ({gps['time_diff_minutes']} min diff)"
            self.table.setItem(row, 5, QTableWidgetItem(location_info))
        
        # Set row height to accommodate thumbnails
        self.table.verticalHeader().setDefaultSectionSize(70)
        
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        
        confirm_button = QPushButton('Confirm & Update GPS Data')
        confirm_button.clicked.connect(self.confirm_update)
        confirm_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def confirm_update(self):
        self.confirmed = True
        self.accept()

class ExifEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.thumbnail_loader = None
        self.exif_cache = {}  # Cache for lazy-loaded EXIF data
        self.location_processor = None
        self.location_cache = {}  # Cache for location history data
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Exif Editor')
        self.setGeometry(100, 100, 1000, 600)

        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        self.folder_entry = QLineEdit(self)
        folder_button = QPushButton('Browse', self)
        folder_button.clicked.connect(self.select_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel('Folder:'))
        folder_layout.addWidget(self.folder_entry)
        folder_layout.addWidget(folder_button)

        self.sort_combo = QComboBox(self)
        self.sort_combo.addItems(['Name', 'Creation Time', 'DateTimeOriginal'])
        self.sort_combo.currentIndexChanged.connect(self.sort_photos)
        # Set default sort criteria to 'DateTimeOriginal'
        self.sort_combo.setCurrentIndex(2)

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel('Sort by:'))
        sort_layout.addWidget(self.sort_combo)

        # Progress bar for loading
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)

        # Thumbnail list
        self.thumbnail_list = QListWidget(self)
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(100, 100))
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.thumbnail_list.itemClicked.connect(self.display_photo_details)
        self.thumbnail_list.itemClicked.connect(self.display_gps_data)
        self.thumbnail_list.itemClicked.connect(self.display_offset_time_data)
        self.thumbnail_list.itemClicked.connect(self.update_exif_date_time_original_display)
        self.thumbnail_list.itemSelectionChanged.connect(self.handle_item_selection_changed)

        # GPS data layout
        self.gps_entry = QLineEdit(self)
        update_gps_button = QPushButton('Update GPS Data', self)
        update_gps_button.clicked.connect(lambda: self.update_gps_for_all_images(self.thumbnail_list.selectedItems(), self.gps_entry.text()))

        gps_layout = QHBoxLayout()
        gps_layout.addWidget(QLabel('GPS Coordinates (lat, lon):'))
        gps_layout.addWidget(self.gps_entry)
        gps_layout.addWidget(update_gps_button)

        # Google Location History button
        location_history_button = QPushButton('Load Google Location History', self)
        location_history_button.clicked.connect(self.load_google_location_history)
        location_history_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 6px;")
        gps_layout.addWidget(location_history_button)

        # OffsetTimeOriginal updater layout
        self.timezone_entry = QLineEdit(self)
        update_time_zone_button = QPushButton('Update time zone', self)
        update_time_zone_button.clicked.connect(lambda: self.update_offset_time_for_all_images(self.thumbnail_list.selectedItems(), self.timezone_entry.text()))

        offset_time_layout = QHBoxLayout()
        offset_time_layout.addWidget(QLabel('Time zone(OffsetTimeOriginal, OffsetTimeDigitized)'))
        offset_time_layout.addWidget(self.timezone_entry)
        offset_time_layout.addWidget(update_time_zone_button)

        # Local date time display
        self.local_date_time = QLabel(self)

        # Local date time offset layout
        self.local_date_time_offset = QLineEdit(self)
        update_local_date_time_offset_button = QPushButton('Update local date time offset', self)
        update_local_date_time_offset_button.clicked.connect(lambda: self.update_local_date_time_by_offset_for_all_images(self.thumbnail_list.selectedItems(), self.local_date_time_offset.text()))
        update_local_date_time_offset_button.clicked.connect(lambda: self.update_exif_date_time_original_display(self.thumbnail_list.selectedItems()[0]))

        local_date_time_offset_layout = QHBoxLayout()
        local_date_time_offset_layout.addWidget(QLabel('Local date time offset'))
        local_date_time_offset_layout.addWidget(self.local_date_time_offset)
        local_date_time_offset_layout.addWidget(update_local_date_time_offset_button)

        left_layout.addLayout(folder_layout)
        left_layout.addLayout(sort_layout)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.thumbnail_list)
        left_layout.addLayout(gps_layout)
        left_layout.addLayout(offset_time_layout)
        left_layout.addWidget(self.local_date_time)
        left_layout.addLayout(local_date_time_offset_layout)

        # Sidebar for photo preview and EXIF data
        self.sidebar = QWidget(self)
        sidebar_layout = QVBoxLayout()
        self.photo_preview = QLabel(self)
        self.photo_preview.setFixedSize(300, 300)
        self.exif_data_text = QTextEdit(self)
        self.exif_data_text.setReadOnly(True)
        sidebar_layout.addWidget(self.photo_preview)
        sidebar_layout.addWidget(self.exif_data_text)
        self.sidebar.setLayout(sidebar_layout)
        self.sidebar.hide()  # Initialize sidebar as hidden

        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        splitter.addWidget(self.sidebar)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folder:
            self.folder_entry.setText(folder)
            self.load_thumbnails(folder)

    def load_thumbnails(self, folder):
        # Stop any existing loader
        if self.thumbnail_loader:
            self.thumbnail_loader.stop()
            self.thumbnail_loader.wait()
            
        self.thumbnail_list.clear()
        self.exif_cache.clear()
        
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not files:
            return
            
        # For DateTimeOriginal sorting, we need to load some EXIF data first
        sort_criteria = self.sort_combo.currentText()
        if sort_criteria == 'Name':
            files.sort(key=lambda x: os.path.basename(x).lower())
        elif sort_criteria == 'Creation Time':
            files.sort(key=lambda x: os.path.getctime(x))
        elif sort_criteria == 'DateTimeOriginal':
            # For this sort, we'll do basic sorting by file creation time first
            # and later update the sort when EXIF data is available
            files.sort(key=lambda x: os.path.getctime(x))

        # Show progress bar and start threaded loading
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(files))
        self.progress_bar.setValue(0)
        
        # Start thumbnail loader thread
        self.thumbnail_loader = ThumbnailLoader(files)
        self.thumbnail_loader.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.thumbnail_loader.loading_progress.connect(self.on_loading_progress)
        self.thumbnail_loader.finished.connect(self.on_loading_finished)
        self.thumbnail_loader.start()

    def on_thumbnail_ready(self, file_path, thumbnail, file_dict):
        """Called when a thumbnail is ready from the worker thread"""
        item = QListWidgetItem(QIcon(thumbnail), file_dict['name'])
        item.setData(Qt.UserRole, file_dict)
        item.setData(Qt.UserRole + 1, None)  # EXIF data not loaded yet - lazy load
        self.thumbnail_list.addItem(item)
        
    def on_loading_progress(self, current, total):
        """Update progress bar"""
        self.progress_bar.setValue(current)
        
    def on_loading_finished(self):
        """Called when thumbnail loading is complete"""
        self.progress_bar.setVisible(False)
        # If we need to sort by DateTimeOriginal, trigger a re-sort now
        if self.sort_combo.currentText() == 'DateTimeOriginal':
            QTimer.singleShot(0, self.sort_by_datetime_original)

    def sort_by_datetime_original(self):
        """Sort thumbnails by DateTimeOriginal after loading"""
        items_data = []
        for i in range(self.thumbnail_list.count()):
            item = self.thumbnail_list.item(i)
            file_path = item.data(Qt.UserRole)['file_path']
            
            # Get datetime original for sorting
            try:
                datetime_original = exif.get_datetime_original(file_path)
            except:
                datetime_original = ''
                
            # Store the data, not the item object
            items_data.append((datetime_original, item.data(Qt.UserRole), item.icon()))
        
        # Sort by datetime
        items_data.sort(key=lambda x: x[0])
        
        # Clear and recreate items in sorted order
        self.thumbnail_list.clear()
        for _, file_dict, icon in items_data:
            new_item = QListWidgetItem(icon, file_dict['name'])
            new_item.setData(Qt.UserRole, file_dict)
            new_item.setData(Qt.UserRole + 1, None)  # EXIF data will be lazy loaded
            self.thumbnail_list.addItem(new_item)

    def sort_photos(self):
        folder = self.folder_entry.text()
        if folder:
            self.load_thumbnails(folder)

    def display_photo_details(self, item):
        file_path = item.data(Qt.UserRole)['file_path']
        
        # Display photo preview
        pixmap = QPixmap(file_path)
        self.photo_preview.setPixmap(pixmap.scaled(self.photo_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Lazy load EXIF data
        exif_dict = self._get_exif_data(file_path, item)
        
        # Display EXIF data
        if exif_dict:
            self.exif_data_text.setText(exif.format_exif_data(exif_dict))
        else:
            self.exif_data_text.setText("No EXIF data available")

    def _get_exif_data(self, file_path, item=None):
        """Lazy load and cache EXIF data"""
        if file_path in self.exif_cache:
            return self.exif_cache[file_path]
            
        try:
            exif_dict = exif.extract_exif_data(file_path)
            self.exif_cache[file_path] = exif_dict
            
            # Also store in item if provided
            if item:
                item.setData(Qt.UserRole + 1, exif_dict)
                
            return exif_dict
        except Exception as e:
            print(f"Error loading EXIF data for {file_path}: {e}")
            self.exif_cache[file_path] = None
            return None

    def display_gps_data(self, item):
        file_path = item.data(Qt.UserRole)['file_path']
        lat, lon = exif.extract_gps_data(file_path)
        self.gps_entry.setText(f"{lat}, {lon}")

    def update_gps_for_all_images(self, items, gps_str):
        if items is None:
            return
        gps_data = self.convert_gps_str_to_gps_data(gps_str)
        try:
            for item in items:
                file_path = item.data(Qt.UserRole)['file_path']
                exif.update_image_gps_exif(file_path, gps_data)
            QMessageBox.information(self, 'Success', 'GPS data updated successfully!')
        except ValueError:
                QMessageBox.warning(self, 'Error', 'Invalid GPS coordinates format. Please use "lat, lon".')
    
    def convert_gps_str_to_gps_data(self, gps_str):
        lat, lon = map(float, gps_str.split(', '))
        return {'lat': lat, 'lon': lon}

    def display_offset_time_data(self, item):
        file_path = item.data(Qt.UserRole)['file_path']
        self.timezone_entry.setText(exif.get_offset_time_data(file_path))

    def update_offset_time_for_all_images(self, items, offset_time):
        if items is None:
            return
        try:
            for item in items:
                file_path = item.data(Qt.UserRole)['file_path']
                exif.update_image_offset_time_exif(file_path, offset_time)
            QMessageBox.information(self, 'Success', 'OffsetTimeOriginal updated successfully!')
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Invalid OffsetTimeOriginal format. Please use "[+-]HH:MM".')
    
    def update_exif_date_time_original_display(self, item):
        file_path = item.data(Qt.UserRole)['file_path']
        date_time_original = exif.get_exif_date_time_original(file_path)
        self.local_date_time.setText(f"DateTimeOriginal: {date_time_original}")

    def update_local_date_time_by_offset_for_all_images(self, items, local_date_time_offset):
        if items is None:
            return
        try:
            for item in items:
                file_path = item.data(Qt.UserRole)['file_path']
                exif.update_local_date_time_by_offset(file_path, local_date_time_offset)
            QMessageBox.information(self, 'Success', 'Local date time offset updated successfully!')
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Wrong offset format. Please use "[+-]HH:MM".')

    def handle_item_selection_changed(self):
        selected_items = self.thumbnail_list.selectedItems()
        if not selected_items:
            self.sidebar.hide()  # Hide sidebar when no photo is selected
        else:
            self.sidebar.show()  # Show sidebar when at least one photo is selected
            
    def load_google_location_history(self):
        """Load Google Location History and match with photos"""
        if self.thumbnail_list.count() == 0:
            QMessageBox.warning(self, 'No Photos', 'Please load photos first before loading location history.')
            return
        
        # Select location history file
        location_file, _ = QFileDialog.getOpenFileName(
            self, 
            'Select Google Location History JSON file', 
            '', 
            'JSON files (*.json);;All files (*)'
        )
        
        if not location_file:
            return
        
        # Get all photo file paths
        photo_files = []
        for i in range(self.thumbnail_list.count()):
            item = self.thumbnail_list.item(i)
            file_path = item.data(Qt.UserRole)['file_path']
            photo_files.append(file_path)
        
        # Extract time range from photos
        time_range = self.extract_photo_time_range(photo_files)
        if not time_range:
            QMessageBox.warning(self, 'No Timestamps', 'Could not extract timestamps from photos.')
            return
        
        # Expand time range by 24 hours on each side for timezone handling
        start_time, end_time = time_range
        expanded_start = start_time - datetime.timedelta(hours=24)
        expanded_end = end_time + datetime.timedelta(hours=24)
        expanded_range = (expanded_start, expanded_end)
        
        # Show progress and start processing
        self.progress_bar.setVisible(True)
        self.progress_bar.setFormat('Processing location history... %p%')
        
        # Start location history processor
        self.location_processor = LocationHistoryProcessor(location_file, photo_files, expanded_range)
        self.location_processor.processing_progress.connect(self.on_location_processing_progress)
        self.location_processor.processing_complete.connect(self.on_location_processing_complete)
        self.location_processor.run()
    
    def extract_photo_time_range(self, photo_files):
        """Extract earliest and latest timestamps from photos"""
        timestamps = []
        
        for file_path in photo_files:
            try:
                # Try to get EXIF timestamp first
                datetime_str = exif.get_exif_date_time_original(file_path)
                timezone_offset = exif.get_offset_time_data(file_path)
                timestamp = None
                if datetime_str:
                    timestamp = datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
                else:
                    # Fallback to file modification time
                    timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if timezone_offset:
                    # timezone_offset looks like "+08:00" or "-05:00"
                    # Parse sign, hours, and minutes from the offset string
                    sign = 1 if timezone_offset[0] == '+' else -1
                    hours = int(timezone_offset[1:3])
                    minutes = int(timezone_offset[4:6])
                    offset = datetime.timedelta(hours=sign * hours, minutes=sign * minutes)
                    timestamp = timestamp.replace(tzinfo=datetime.timezone(offset))
                else:
                    timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                timestamps.append(timestamp)

            except Exception as e:
                print(f"Could not extract timestamp from {file_path}: {e}")
                continue
        
        if not timestamps:
            return None
        
        return (min(timestamps), max(timestamps))
    
    def on_location_processing_progress(self, current, total):
        """Update progress during location processing"""
        self.progress_bar.setValue(current)
        self.progress_bar.setMaximum(total)
    
    def on_location_processing_complete(self, photo_gps_data):
        """Handle completion of location processing"""
        self.progress_bar.setVisible(False)
        
        if not photo_gps_data:
            QMessageBox.information(self, 'No Matches', 'No location matches found for the photos in the selected time range.')
            return
        
        # Show preview dialog
        preview_dialog = LocationPreviewDialog(photo_gps_data, self)
        if preview_dialog.exec_() == QDialog.Accepted and preview_dialog.confirmed:
            self.apply_gps_data_to_photos(photo_gps_data)
    
    def apply_gps_data_to_photos(self, photo_gps_data):
        """Apply GPS data to photos after user confirmation"""
        try:
            success_count = 0
            error_count = 0
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(len(photo_gps_data))
            self.progress_bar.setValue(0)
            
            for i, data in enumerate(photo_gps_data):
                try:
                    file_path = data['file_path']
                    gps_data = {
                        'lat': data['gps']['lat'],
                        'lon': data['gps']['lon']
                    }
                    
                    # Update GPS data in photo
                    exif.update_image_gps_exif(file_path, gps_data)
                    success_count += 1
                    
                    # Update cache if photo is already loaded
                    if file_path in self.exif_cache:
                        del self.exif_cache[file_path]  # Clear cache to force reload
                    
                except Exception as e:
                    print(f"Error updating GPS for {data['filename']}: {e}")
                    error_count += 1
                    
                self.progress_bar.setValue(i + 1)
            
            self.progress_bar.setVisible(False)
            
            # Show results
            if success_count > 0:
                message = f"Successfully updated GPS data for {success_count} photos"
                if error_count > 0:
                    message += f" ({error_count} errors)"
                QMessageBox.information(self, 'Update Complete', message)
                
                # Refresh display if current photo is selected
                selected_items = self.thumbnail_list.selectedItems()
                if selected_items:
                    self.display_gps_data(selected_items[0])
            else:
                QMessageBox.warning(self, 'Update Failed', f'Failed to update GPS data. {error_count} errors occurred.')
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, 'Error', f'An error occurred while updating GPS data: {str(e)}')

    def closeEvent(self, event):
        """Clean up when closing the application"""
        if self.thumbnail_loader:
            self.thumbnail_loader.stop()
            self.thumbnail_loader.wait()
        if self.location_processor:
            self.location_processor.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication([])
    window = ExifEditor()
    window.show()
    app.exec_()