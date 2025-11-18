import os, re, shutil, ctypes, sys
from ctypes import wintypes, windll

def natural_sort_key(s):
    """
    Helper function for natural sorting of strings containing numbers.
    For example: ["img1.jpg", "img10.jpg", "img2.jpg"] will be sorted as 
    ["img1.jpg", "img2.jpg", "img10.jpg"]
    """
    parts = re.split('([0-9]+)', os.path.basename(s))
    return [int(part) if part.isdigit() else part.lower() for part in parts]

def check_exiftool():
    """Check if exiftool is available in the system"""
    exiftool_cmd = 'exiftool.exe' if sys.platform == "win32" else 'exiftool'
    if not shutil.which(exiftool_cmd):
        from PyQt5.QtWidgets import QMessageBox
        msg = """ExifTool is not found in your system PATH. 
Please install ExifTool and make sure it's accessible from the command line.
Download from: https://exiftool.org/"""
        QMessageBox.critical(None, "ExifTool Not Found", msg)
        sys.exit(1)

def get_short_path_name(long_name):
    """
    Get short path name on Windows systems, with cross-platform fallback.
    This helps handle paths with non-ASCII characters which might cause issues with some tools.
    """
    if sys.platform == "win32":
        try:
            buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if windll.kernel32.GetShortPathNameW(long_name, buffer, wintypes.MAX_PATH) > 0:
                return buffer.value
        except Exception as e:
            print(f"Error getting short path: {e}")
    return long_name

def parse_tags(tag_string):
    """
    Parse a comma-separated tag string into a set of cleaned tags.
    Strips whitespace and converts to lowercase for consistency.
    
    Args:
        tag_string: String containing comma-separated tags
        
    Returns:
        Set of cleaned tag strings
    """
    if not tag_string:
        return set()
    return {tag.strip().lower() for tag in tag_string.split(',') if tag.strip()}
