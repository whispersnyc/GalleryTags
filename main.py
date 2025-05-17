import sys
import os
import re
import shutil
import ctypes
from ctypes import wintypes, windll
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, 
                            QLabel, QScrollArea, QInputDialog, QMessageBox, 
                            QFileDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                            QShortcut, QComboBox, QDialog, QFrame, QMenu)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QSize, QRect, QPoint, QTimer
from PIL import Image
import piexif
from io import BytesIO
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import subprocess

from image_cell import ImageCell
from loading_overlay import LoadingOverlay
from image_details_popup import ImageDetailsPopup
from image_gallery import ImageGallery

from config import APP_CONFIG, EXPORT_PATHS, EXPORT_CONFIG, FORMAT_CONFIG
# config.APP_CONFIG = {"default_folder":path_str}
# config.EXPORT_PATHS = {file_path_str: tags_str ("& tag1, tag2" means AND while '|' prefix means OR, default AND)}
# config.EXPORT_CONFIG = {'heading': heading_str, 'item_format': "![$fn]($fp/$fn.$fe)\n", "group_by": 5}
# config.FORMAT_CONFIG = {'.ext': '-(Exif/XMP):(Property)', 'extensions': ['.ext', '.extension'], ...}

# Helper to get all supported extensions
SUPPORTED_EXTENSIONS = [ext for format_info in FORMAT_CONFIG.values() 
                       for ext in format_info['extensions']]

def natural_sort_key(s):
    parts = re.split('([0-9]+)', os.path.basename(s))
    return [int(part) if part.isdigit() else part.lower() for part in parts]

def check_exiftool():
    """Check if exiftool is available in the system"""
    exiftool_cmd = 'exiftool.exe' if sys.platform == "win32" else 'exiftool'
    if not shutil.which(exiftool_cmd):
        msg = """ExifTool is not found in your system PATH. 
Please install ExifTool and make sure it's accessible from the command line.
Download from: https://exiftool.org/"""
        QMessageBox.critical(None, "ExifTool Not Found", msg)
        sys.exit(1)

def get_short_path_name(long_name):
    """Get short path name, with cross-platform fallback"""
    if sys.platform == "win32":
        try:
            buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if windll.kernel32.GetShortPathNameW(long_name, buffer, wintypes.MAX_PATH) > 0:
                return buffer.value
        except Exception as e:
            print(f"Error getting short path: {e}")
    return long_name

# Helper to get metadata field for a file
def get_metadata_field(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    for format_info in FORMAT_CONFIG.values():
        if ext in format_info['extensions']:
            return format_info['field']
    return None

def parse_tags(tag_string):
    """Helper function to parse tag string into a set of cleaned tags"""
    if not tag_string:
        return set()
    return {tag.strip().lower() for tag in tag_string.split(',') if tag.strip()}

if __name__ == "__main__":
    app = QApplication(sys.argv)
    check_exiftool()
    
    window = ImageGallery()
    window.show()
    sys.exit(app.exec_())
