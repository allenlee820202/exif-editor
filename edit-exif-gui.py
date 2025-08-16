import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QComboBox, QTextEdit, QSplitter, QProgressBar
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

class ExifEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.thumbnail_loader = None
        self.exif_cache = {}  # Cache for lazy-loaded EXIF data
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
            
    def closeEvent(self, event):
        """Clean up when closing the application"""
        if self.thumbnail_loader:
            self.thumbnail_loader.stop()
            self.thumbnail_loader.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication([])
    window = ExifEditor()
    window.show()
    app.exec_()