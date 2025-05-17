import os
import json
import sys
import time

class CacheManager:
    """Handles caching of image metadata to improve application startup performance"""
    
    def __init__(self):
        self.cache_dir = self._get_cache_dir()
        self.cache_file = os.path.join(self.cache_dir, "gallery_cache.json")
        self.cache_data = {}
        self._load_cache()
        print(f"[Cache] Initialized cache at {self.cache_file}")
    
    def _get_cache_dir(self):
        """Get platform-specific cache directory"""
        if sys.platform == "win32":
            cache_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "GalleryTags")
        else:  # Linux, macOS
            cache_dir = os.path.join(os.path.expanduser("~"), ".config", "gallerytags")
        
        # Create directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            print(f"[Cache] Created cache directory: {cache_dir}")
        
        return cache_dir
    
    def _load_cache(self):
        """Load cache data from file if it exists"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                print(f"[Cache] Loaded {len(self.cache_data)} items from cache")
            except Exception as e:
                print(f"[Cache] Error loading cache: {e}")
                self.cache_data = {}
        else:
            print("[Cache] No existing cache file found")
    
    def save_cache(self):
        """Save cache data to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            print(f"[Cache] Saved {len(self.cache_data)} items to cache")
        except Exception as e:
            print(f"[Cache] Error saving cache: {e}")
    
    def get_cached_metadata(self, file_path):
        """Get cached metadata for a file if available and up to date"""
        norm_path = os.path.normpath(file_path)
        
        if norm_path in self.cache_data:
            cached_item = self.cache_data[norm_path]
            file_mtime = os.path.getmtime(file_path)
            
            # Check if file has been modified since last cache
            if abs(cached_item['mtime'] - file_mtime) < 0.1:  # Allow small time difference (0.1s)
                return cached_item['tags']
            else:
                print(f"[Cache] File modified since cache: {os.path.basename(file_path)}")
        
        return None
    
    def update_cache(self, file_path, tags):
        """Update cache with new metadata for a file"""
        norm_path = os.path.normpath(file_path)
        
        self.cache_data[norm_path] = {
            'mtime': os.path.getmtime(file_path),
            'tags': tags
        }
        
    def get_cached_files_in_dir(self, dir_path):
        """Get a list of all cached files in the given directory"""
        dir_path = os.path.normpath(dir_path)
        return [path for path in self.cache_data.keys() 
                if os.path.dirname(path) == dir_path]
    
    def clean_missing_files(self):
        """Remove entries from cache that no longer exist in the filesystem"""
        before_count = len(self.cache_data)
        self.cache_data = {path: data for path, data in self.cache_data.items() 
                          if os.path.exists(path)}
        removed = before_count - len(self.cache_data)
        if removed > 0:
            print(f"[Cache] Removed {removed} missing files from cache")
    
    def get_mtime(self, file_path):
        """Get cached modification time for a file if available"""
        norm_path = os.path.normpath(file_path)
        
        if norm_path in self.cache_data:
            return self.cache_data[norm_path]['mtime']
        
        return None
