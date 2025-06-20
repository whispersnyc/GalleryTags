import sys, os, json
from PyQt5.QtWidgets import QApplication
from ui.gallery import ImageGallery
from core.metadata import check_exiftool, process_exports_headless
from config import APP_CONFIG, EXPORT_CONFIG_FILENAME

def print_usage():
    print("Usage:")
    print("  Normal mode: python app.py")
    print("  Headless mode: python app.py path/to/directory")
    print("  Headless mode (specific config): python app.py path/to/config.json")

def main():
    # Check if running in headless mode
    if len(sys.argv) > 1:
        target_path = os.path.abspath(sys.argv[1])
        
        if not os.path.exists(target_path):
            print(f"Error: Path does not exist: {target_path}")
            sys.exit(1)
        
        # Verify exiftool is available
        if not check_exiftool():
            sys.exit(1)
            
        # Initialize QApplication (required even for headless)
        app = QApplication(sys.argv)
        
        try:
            if os.path.isfile(target_path):
                # Use specified config file
                if not target_path.endswith('.json'):
                    print("Error: Config file must be a .json file")
                    sys.exit(1)
                working_dir = os.path.dirname(target_path)
                config_path = target_path
            else:
                # Use directory's default config file
                working_dir = target_path
                config_path = os.path.join(working_dir, EXPORT_CONFIG_FILENAME)
                if not os.path.exists(config_path):
                    print(f"Error: No export config found at: {config_path}")
                    sys.exit(1)
            
            # Process exports
            success = process_exports_headless(working_dir, config_path)
            sys.exit(0 if success else 1)
            
        except Exception as e:
            print(f"Error during headless export: {str(e)}")
            sys.exit(1)
    
    # Normal GUI mode
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
