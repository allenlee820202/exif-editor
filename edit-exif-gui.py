import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QComboBox, QTextEdit, QSplitter
from PyQt5.QtGui import QPixmap, QIcon, QCursor
from PyQt5.QtCore import QSize, Qt, QTimer, QPoint
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

class PhotoGPSUpdater(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Photo GPS Updater')
        self.setGeometry(100, 100, 1000, 600)

        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        self.folder_entry = QLineEdit(self)
        self.folder_button = QPushButton('Browse', self)
        self.folder_button.clicked.connect(self.select_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel('Folder:'))
        folder_layout.addWidget(self.folder_entry)
        folder_layout.addWidget(self.folder_button)

        self.sort_combo = QComboBox(self)
        self.sort_combo.addItems(['Name', 'Creation Time'])
        self.sort_combo.currentIndexChanged.connect(self.sort_photos)

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel('Sort by:'))
        sort_layout.addWidget(self.sort_combo)

        self.thumbnail_list = QListWidget(self)
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(100, 100))
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.thumbnail_list.itemClicked.connect(self.display_photo_details)

        left_layout.addLayout(folder_layout)
        left_layout.addLayout(sort_layout)
        left_layout.addWidget(self.thumbnail_list)

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

        for file_path in files:
            pixmap = QPixmap(file_path)
            thumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QListWidgetItem(QIcon(thumbnail), os.path.basename(file_path))
            item.setData(Qt.UserRole, file_path)

            # Extract EXIF data
            try:
                image = Image.open(file_path)
                exif_dict = piexif.load(image.info['exif'])
                # Remove thumbnail data from EXIF because its format is not compatible with piexif
                exif_dict.pop('thumbnail', None)
                item.setData(Qt.UserRole + 1, exif_dict)  # Store EXIF data in the item
            except Exception as e:
                print(f"Error loading EXIF data for {file_path}: {e}")
                item.setData(Qt.UserRole + 1, None)  # Store None if EXIF data cannot be loaded

            self.thumbnail_list.addItem(item)

    def sort_photos(self):
        folder = self.folder_entry.text()
        if folder:
            self.load_thumbnails(folder)

    def display_photo_details(self, item):
        file_path = item.data(Qt.UserRole)
        exif_dict = item.data(Qt.UserRole + 1)

        # Display photo preview
        pixmap = QPixmap(file_path)
        self.photo_preview.setPixmap(pixmap.scaled(self.photo_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Display EXIF data
        if exif_dict:
            metadata = self.format_exif_data(exif_dict)
            self.exif_data_text.setText(metadata)
        else:
            self.exif_data_text.setText("No EXIF data available")

        self.sidebar.show()  # Show sidebar when a photo is selected

    def format_exif_data(self, exif_dict):
        metadata = []
        for ifd in exif_dict:
            for tag in exif_dict[ifd]:
                tag_name = piexif.TAGS[ifd][tag]["name"]
                tag_value = exif_dict[ifd][tag]
                metadata.append(f"{tag_name}: {tag_value}")
        return "\n".join(metadata)

    def clear_selection(self):
        self.thumbnail_list.clearSelection()
        self.sidebar.hide()  # Hide sidebar when no photo is selected

if __name__ == '__main__':
    app = QApplication([])
    window = PhotoGPSUpdater()
    window.show()
    app.exec_()