import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QComboBox, QTextEdit, QSplitter
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QSize, Qt
import piexif
import exif

class ExifEditor(QWidget):
    def __init__(self):
        super().__init__()
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

        # Thumbnail list
        self.thumbnail_list = QListWidget(self)
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(100, 100))
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.thumbnail_list.itemClicked.connect(self.display_photo_details)
        self.thumbnail_list.itemClicked.connect(self.display_gps_data)
        self.thumbnail_list.itemClicked.connect(self.display_offset_time_data)
        self.thumbnail_list.itemClicked.connect(self.get_exif_date_time_original)
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
        update_local_date_time_offset_button.clicked.connect(lambda: self.get_exif_date_time_original)

        local_date_time_offset_layout = QHBoxLayout()
        local_date_time_offset_layout.addWidget(QLabel('Local date time offset'))
        local_date_time_offset_layout.addWidget(self.local_date_time_offset)
        local_date_time_offset_layout.addWidget(update_local_date_time_offset_button)

        left_layout.addLayout(folder_layout)
        left_layout.addLayout(sort_layout)
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
        self.thumbnail_list.clear()
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        sort_criteria = self.sort_combo.currentText()
        if sort_criteria == 'Name':
            files.sort(key=lambda x: os.path.basename(x).lower())
        elif sort_criteria == 'Creation Time':
            files.sort(key=lambda x: os.path.getctime(x))
        elif sort_criteria == 'DateTimeOriginal':
            files.sort(key=lambda x: piexif.load(x).get('Exif', {}).get(piexif.ExifIFD.DateTimeOriginal, ''))

        for file_path in files:
            pixmap = QPixmap(file_path)
            thumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QListWidgetItem(QIcon(thumbnail), os.path.basename(file_path))
            file_dict = {'file_path': file_path, 'name': os.path.basename(file_path), 'ctime': os.path.getctime(file_path)}
            item.setData(Qt.UserRole, file_dict)

            try:
                exif_dict = exif.extract_exif_data(file_path)
                item.setData(Qt.UserRole + 1, exif_dict)  # Store EXIF data in the item
            except Exception as e:
                item.setData(Qt.UserRole + 1, None)  # Store None if EXIF data cannot be loaded

            self.thumbnail_list.addItem(item)

    def sort_photos(self):
        folder = self.folder_entry.text()
        if folder:
            self.load_thumbnails(folder)

    def display_photo_details(self, item):
        file_path = item.data(Qt.UserRole)['file_path']
        exif_dict = item.data(Qt.UserRole + 1)

        # Display photo preview
        pixmap = QPixmap(file_path)
        self.photo_preview.setPixmap(pixmap.scaled(self.photo_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Display EXIF data
        if exif_dict:
            self.exif_data_text.setText(exif.format_exif_data(exif_dict))
        else:
            self.exif_data_text.setText("No EXIF data available")

    def display_gps_data(self, item):
        file_path = item.data(Qt.UserRole)['file_path']
        lat, lon = exif.extract_gps_data(file_path)
        self.gps_entry.setText(f"{lat}, {lon}")

    def update_gps_for_all_images(self, items, gps_str):
        if items:
            try:
                lat, lon = map(float, gps_str.split(', '))
                gps_data = {'lat': lat, 'lon': lon}
                for item in items:
                    file_path = item.data(Qt.UserRole)['file_path']
                    exif.update_image_gps_exif(file_path, gps_data)
                QMessageBox.information(self, 'Success', 'GPS data updated successfully!')
            except ValueError:
                QMessageBox.warning(self, 'Error', 'Invalid GPS coordinates format. Please use "lat, lon".')

    def display_offset_time_data(self, item):
        file_path = item.data(Qt.UserRole)['file_path']
        self.timezone_entry.setText(exif.get_offset_time_data(file_path))

    def update_offset_time_for_all_images(self, items, offset_time):
        if items:
            try:
                for item in items:
                    file_path = item.data(Qt.UserRole)['file_path']
                    exif.update_image_offset_time_exif(file_path, offset_time)
                QMessageBox.information(self, 'Success', 'OffsetTimeOriginal updated successfully!')
            except ValueError:
                QMessageBox.warning(self, 'Error', 'Invalid OffsetTimeOriginal format. Please use "[+-]HH:MM".')
    
    def get_exif_date_time_original(self, item):
        file_path = item.data(Qt.UserRole)['file_path']
        date_time_original = exif.get_exif_date_time_original(file_path)
        self.local_date_time.setText(f"DateTimeOriginal: {date_time_original}")

    def update_local_date_time_by_offset_for_all_images(self, items, local_date_time_offset):
        if items:
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

if __name__ == '__main__':
    app = QApplication([])
    window = ExifEditor()
    window.show()
    app.exec_()