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
    return True

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

def process_exports_headless(working_dir, config_path):
    """Process exports in headless mode"""
    from core.cache import CacheManager
    from utils.helpers import parse_tags
    from config import EXPORT_CONFIG
    import json, os
    
    try:
        # Load export config
        with open(config_path, 'r', encoding='utf-8') as f:
            export_paths = json.load(f)
        
        if not export_paths:
            print("No export paths configured - nothing to export")
            return True
        
        # Initialize cache
        cache_manager = CacheManager()
        
        # Get all supported images in directory
        image_files = []
        for root, _, files in os.walk(working_dir):
            for filename in files:
                if any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    image_files.append(os.path.join(root, filename))
        
        if not image_files:
            print("No supported images found in directory")
            return False
        
        print(f"Found {len(image_files)} images to process")
        
        # Process each export path
        for file_path, tags_str in export_paths.items():
            try:
                # Convert file_path to absolute if relative
                if not os.path.isabs(file_path):
                    file_path = os.path.join(working_dir, file_path)
                
                print(f"Processing export: {file_path}")
                
                # Create directory if needed
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Parse tag query
                tags_str = tags_str.strip()
                is_or_mode = tags_str.startswith('|')
                if tags_str.startswith('|') or tags_str.startswith('&'):
                    tags_str = tags_str[1:].strip()
                required_tags = parse_tags(tags_str)
                
                # Match images
                matched_images = []
                for img_path in image_files:
                    # Get tags from cache or read fresh
                    tags = cache_manager.get_cached_metadata(img_path)
                    if tags is None:
                        tags = get_metadata_field(img_path)
                        cache_manager.update_cache(img_path, tags)
                    
                    img_tags = parse_tags(tags)
                    
                    if is_or_mode:
                        if any(tag in img_tags for tag in required_tags):
                            matched_images.append(img_path)
                    else:
                        if all(tag in img_tags for tag in required_tags):
                            matched_images.append(img_path)
                
                print(f"Found {len(matched_images)} matching images")
                
                # Generate content
                content = EXPORT_CONFIG['heading'] + '\n'
                export_dir = os.path.dirname(os.path.abspath(file_path))
                
                for i, img_path in enumerate(matched_images, 1):
                    filename = os.path.basename(img_path)
                    filename_no_ext = os.path.splitext(filename)[0]
                    file_ext = os.path.splitext(filename)[1][1:]
                    img_dir = os.path.dirname(img_path)
                    
                    try:
                        rel_path = os.path.relpath(img_dir, export_dir)
                        short_path = '.' if rel_path == '.' else './' + rel_path.replace(os.path.sep, '/')
                    except ValueError:
                        short_path = img_dir
                    
                    item = EXPORT_CONFIG['item_format']
                    item = item.replace('$fn', filename_no_ext)
                    item = item.replace('$fe', file_ext)
                    item = item.replace('$fp', short_path)
                    item = item.replace('$ffp', img_dir)
                    content += item
                    
                    if EXPORT_CONFIG['group_by'] > 0 and i % EXPORT_CONFIG['group_by'] == 0:
                        content += '\n'
                
                # Write file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Exported to: {file_path}")
                
            except Exception as e:
                print(f"Error exporting to {file_path}: {str(e)}")
                return False
        
        # Save updated cache
        cache_manager.save_cache()
        return True
        
    except Exception as e:
        print(f"Export processing error: {str(e)}")
        return False
