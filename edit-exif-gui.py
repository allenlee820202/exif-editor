import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QComboBox
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QSize, Qt
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
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

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
        self.thumbnail_list.itemClicked.connect(self.display_gps_data)

        self.gps_entry = QLineEdit(self)
        self.update_button = QPushButton('Update GPS Data', self)
        self.update_button.clicked.connect(self.update_gps_data)

        gps_layout = QHBoxLayout()
        gps_layout.addWidget(QLabel('GPS Coordinates (lat, lon):'))
        gps_layout.addWidget(self.gps_entry)
        gps_layout.addWidget(self.update_button)

        layout.addLayout(folder_layout)
        layout.addLayout(sort_layout)
        layout.addWidget(self.thumbnail_list)
        layout.addLayout(gps_layout)

        self.setLayout(layout)

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
            self.thumbnail_list.addItem(item)

    def sort_photos(self):
        folder = self.folder_entry.text()
        if folder:
            self.load_thumbnails(folder)

    def display_gps_data(self, item):
        file_path = item.data(Qt.UserRole)
        image = Image.open(file_path)
        exif_dict = piexif.load(image.info['exif'])
        gps_ifd = exif_dict.get('GPS', {})
        lat = self.convert_from_dms(gps_ifd.get(piexif.GPSIFD.GPSLatitude, ((0, 1), (0, 1), (0, 1))))
        lon = self.convert_from_dms(gps_ifd.get(piexif.GPSIFD.GPSLongitude, ((0, 1), (0, 1), (0, 1))))
        self.gps_entry.setText(f"{lat}, {lon}")

    def convert_from_dms(self, dms):
        degrees = dms[0][0] / dms[0][1]
        minutes = dms[1][0] / dms[1][1] / 60
        seconds = dms[2][0] / dms[2][1] / 3600
        return degrees + minutes + seconds

    def update_gps_data(self):
        items = self.thumbnail_list.selectedItems()
        if items:
            gps_str = self.gps_entry.text()
            try:
                lat, lon = map(float, gps_str.split(', '))
                gps_data = {'lat': lat, 'lon': lon}
                for item in items:
                    file_path = item.data(Qt.UserRole)
                    process_image(file_path, gps_data)
                QMessageBox.information(self, 'Success', 'GPS data updated successfully!')
            except ValueError:
                QMessageBox.warning(self, 'Error', 'Invalid GPS coordinates format. Please use "lat, lon".')

if __name__ == '__main__':
    app = QApplication([])
    window = PhotoGPSUpdater()
    window.show()
    app.exec_()