# Gallery Tags - Web Version

A simple web-based image gallery with tag search functionality using Bottle.py.

## Features

- **Folder Selection**: Browse and select subfolders from a configured BASE_PATH
- **Recursive Mode**: Toggle to include images from subfolders recursively
- **Smart Tag Caching**: Tags are cached globally with last-modified timestamp validation
- **Search with AND/OR**: Search images by tags using AND (default) or OR logic
- **Refresh Cache**: Refresh only modified files in the current folder with a single button

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure BASE_PATH in `config.py`:
   ```python
   BASE_PATH = "/path/to/your/images"
   ```

3. Ensure `exiftool` is installed and available in your PATH:
   - **Linux/Mac**: `brew install exiftool` or `apt-get install libimage-exiftool-perl`
   - **Windows**: Download from https://exiftool.org/

## Running the Web App

```bash
python bottle_app.py
```

Then open your browser to: http://localhost:8080

## Usage

1. **Select a Folder**: Use the dropdown to select a subfolder from BASE_PATH
2. **Toggle Recursive**: Check the "Recursive" checkbox to include images from all subfolders
3. **Search Tags**:
   - Default (AND mode): `cat, dog` - finds images with BOTH tags
   - OR mode: `| cat, dog` - finds images with EITHER tag
   - AND mode (explicit): `& cat, dog` - finds images with BOTH tags
4. **Load**: Click "Load" to display the images
5. **Refresh All**: Click "Refresh All" to refresh tags for modified files in the current folder (respects recursive toggle)

## Tag Caching

- **Global Cache**: All tags are cached in a single global cache file (not per-folder)
- **Automatic Validation**: Cache automatically checks file modification time (mtime) when loading
- **Smart Refresh**: The "Refresh All" button only refreshes files that have been modified since caching
- **Folder-Specific Refresh**: Refresh only affects the currently selected folder (with recursive option)
- **Cache Location**:
  - Linux/Mac: `~/.config/gallerytags/gallery_cache.json`
  - Windows: `%LOCALAPPDATA%\GalleryTags\gallery_cache.json`

## Configuration

Edit `config.py` to customize:

- `BASE_PATH`: Root directory for your images
- `WEB_CONFIG`: Host, port, and debug settings
- `FORMAT_CONFIG`: Metadata fields for different image formats

## API Endpoints

- `GET /` - Main web interface
- `GET /api/folders` - Get folder tree
- `GET /api/images?folder=...&recursive=0&search=...` - Get images with optional search
- `GET /image?path=...` - Serve image file
- `POST /api/refresh?folder=...&recursive=0` - Refresh modified files in specified folder
