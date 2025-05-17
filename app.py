import sys
from PyQt5.QtWidgets import QApplication
from ui.gallery import ImageGallery
from core.metadata import check_exiftool
from config import APP_CONFIG

def main():
    app = QApplication(sys.argv)
    check_exiftool()
    
    window = ImageGallery()
    window.show()
    
    # Load default folder if configured
    if APP_CONFIG['default_folder']:
        window.load_images(APP_CONFIG['default_folder'])
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
