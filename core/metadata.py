import os
import re
import shutil
import sys
import subprocess
import ctypes
from ctypes import wintypes, windll
from config import FORMAT_CONFIG

# Helper to get all supported extensions
SUPPORTED_EXTENSIONS = [ext for format_info in FORMAT_CONFIG.values() 
                       for ext in format_info['extensions']]

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
    """Get short path name, with cross-platform fallback"""
    if sys.platform == "win32":
        try:
            buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if windll.kernel32.GetShortPathNameW(long_name, buffer, wintypes.MAX_PATH) > 0:
                return buffer.value
        except Exception as e:
            print(f"Error getting short path: {e}")
    return long_name

def get_metadata_field(file_path):
    """Helper to get the appropriate metadata field for a file"""
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

def natural_sort_key(s):
    """Sort file paths naturally (numbers in order)"""
    parts = re.split('([0-9]+)', os.path.basename(s))
    return [int(part) if part.isdigit() else part.lower() for part in parts]

def read_tag_metadata(image_path, short_path=None):
    """Read tag metadata using exiftool"""
    try:
        field = get_metadata_field(image_path)
        if not field:
            print(f"Unsupported file format: {image_path}")
            return ""
            
        # Use short path if available for Unicode path issues on Windows
        path_to_use = short_path if short_path else image_path
            
        result = subprocess.run(
            ['exiftool', field, '-b', path_to_use], 
            capture_output=True, text=True, check=True,
            encoding='utf-8'
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"ExifTool error for {image_path}: {e.stderr}")
        return ""
    except Exception as e:
        print(f"Error reading metadata from {image_path}: {e}")
        return ""

def write_tag_metadata(image_path, tag_text, short_path=None):
    """Write tag metadata using exiftool"""
    try:
        field = get_metadata_field(image_path)
        if not field:
            print(f"Unsupported file format: {image_path}")
            return False
            
        # Use short path if available for Unicode path issues on Windows
        path_to_use = short_path if short_path else image_path
            
        # ExifTool command to write metadata
        result = subprocess.run(
            ['exiftool', f'{field}={tag_text}', '-overwrite_original', path_to_use],
            capture_output=True, text=True, check=False
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"ExifTool error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error writing metadata to {image_path}: {e}")
        return False
