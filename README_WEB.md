# GalleryTags Web UI

A modern, browser-based interface for GalleryTags - the intuitive bulk image tagging tool.

## Features

The web UI provides all the functionality of the desktop application in a responsive, modern web interface:

- **Image Management**: Browse and view images in a responsive grid layout
- **Tag Operations**: Add, edit, and manage tags for individual or multiple images
- **Search & Filter**: Search images by tags with AND/OR mode support
- **Sorting**: Sort by name, date, or tags (ascending/descending)
- **Batch Operations**: Select multiple images and apply tags to all at once
- **Export System**: Configure and run markdown exports with tag-based filtering
- **Statistics**: View gallery statistics and all available tags
- **Caching**: Fast performance with intelligent metadata caching
- **Keyboard Shortcuts**: Full keyboard navigation support

## Installation

### Prerequisites

1. **Python 3.7+**
2. **ExifTool** - Must be installed and available in system PATH
   - Download from: https://exiftool.org/
   - Verify installation: `exiftool -ver`

### Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements-web.txt
   ```

2. Ensure ExifTool is installed and accessible

## Running the Web UI

### Basic Usage

Start the web server:

```bash
python web_app.py
```

Then open your browser to: http://127.0.0.1:5000

### Custom Host/Port

```bash
# Listen on all interfaces
python web_app.py --host 0.0.0.0 --port 8080

# Enable debug mode (development only)
python web_app.py --debug
```

### Command-line Options

- `--host`: Host to bind to (default: 127.0.0.1)
- `--port`: Port to bind to (default: 5000)
- `--debug`: Enable debug mode

## Usage Guide

### Opening a Folder

1. Click the **"Open Folder"** button or press `Ctrl+O`
2. Enter the full path to your image folder
3. Click **"Open"**

The application will load all supported images (JPG, PNG, WebP) from the folder and its subfolders.

### Selecting Images

- **Single Click**: Select a single image (Ctrl+click to toggle)
- **Shift+Click**: Select a range of images
- **Drag**: Click and drag to select multiple images
- **Ctrl+A**: Select/deselect all images

### Tagging Images

#### Individual Image
1. **Double-click** an image to open the details dialog
2. Edit tags in the text area (comma-separated)
3. Click **"Save Tags"**

#### Batch Tagging
1. Select multiple images
2. The batch tag editor will appear at the top
3. Enter tags (comma-separated)
4. Press **Enter** or click **"Apply Tags"**

### Searching Images

1. Enter tags in the search box (comma-separated)
2. Choose search mode:
   - **AND**: Image must have all search tags
   - **OR**: Image must have at least one search tag
3. Click **"Clear"** to reset search

### Sorting Images

Use the **"Sort By"** dropdown to sort images by:
- Name (A-Z or Z-A)
- Date Modified (Oldest or Newest)
- Tags (A-Z or Z-A)

### Cache Management

- **Quick Refresh** (`Ctrl+R`): Updates only modified files
- **Full Rescan** (`Ctrl+Shift+R`): Re-reads all metadata

### Export Configuration

1. Click **"Export"** button or press `Ctrl+E`
2. Add export rules:
   - **Output Path**: Where to save the markdown file
   - **Tag Query**: Tags to filter (use `|` prefix for OR mode)
3. Click **"Save & Export"** to run the export

#### Export Examples

- `gallery.md` with query `portrait, character` → Exports images with both tags
- `landscapes.md` with query `| landscape, nature` → Exports images with either tag

### Statistics

Click the **"Stats"** button to view:
- Total number of images
- Total size of all images
- Number of unique tags
- Clickable tag cloud (click a tag to search for it)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open folder |
| `Ctrl+A` | Select/deselect all |
| `Ctrl+F` | Focus search box |
| `Ctrl+R` | Quick refresh |
| `Ctrl+Shift+R` | Full rescan |
| `Ctrl+E` | Show export dialog |
| `Enter` | Apply tags to selected images |
| `Escape` | Clear selection or close modal |

## Configuration

The web UI uses the same configuration as the desktop app.

### config.py

Create a `config.py` file (or copy from `config.py.example`):

```python
APP_CONFIG = {
    'default_folder': '/path/to/your/images',  # Auto-load on startup
}

EXPORT_CONFIG = {
    'item_format': "![$fn]($fp/$fn.$fe)\n",
    'heading': "",
    'group_by': 0,
}

FORMAT_CONFIG = {
    '.jpg': {'field': '-Exif:ImageDescription', 'extensions': ['.jpg', '.jpeg']},
    '.png': {'field': '-XMP:Description', 'extensions': ['.png']},
    '.webp': {'field': '-XMP:Description', 'extensions': ['.webp']},
}
```

### Export Configuration

Create a `.gallery_export.json` file in your image folder:

```json
{
  "gallery.md": "portrait, character",
  "landscapes.md": "| landscape, nature",
  "reference/all.md": "reference"
}
```

## API Reference

The web UI exposes a REST API for integration with other tools.

### Endpoints

- `GET /api/config` - Get application configuration
- `POST /api/folder/open` - Open a folder
- `GET /api/folder/current` - Get current folder
- `POST /api/images/list` - List images with metadata
- `GET /api/image/thumbnail/<path>` - Get image thumbnail
- `GET /api/image/full/<path>` - Get full resolution image
- `GET /api/image/tags?path=<path>` - Get tags for an image
- `POST /api/image/tags` - Update tags for images
- `POST /api/cache/refresh` - Refresh metadata cache
- `GET /api/export/config` - Get export configuration
- `POST /api/export/config` - Save export configuration
- `POST /api/export/run` - Run export process
- `GET /api/stats` - Get gallery statistics

## Architecture

### Backend (Flask)

- **web_app.py**: Main Flask application with REST API
- **core/**: Reuses existing metadata and cache modules
- **utils/**: Reuses existing helper functions

### Frontend

- **web/templates/index.html**: Single-page application template
- **web/static/css/style.css**: Responsive styling
- **web/static/js/app.js**: Client-side application logic

### Data Flow

1. User opens folder → Backend scans for images
2. Frontend requests image list → Backend returns with cached metadata
3. User selects images and edits tags → API updates metadata via ExifTool
4. Cache is updated and persisted
5. Frontend re-renders with new data

## Troubleshooting

### Images not loading
- Check that the folder path is correct
- Verify images are in supported formats (JPG, PNG, WebP)
- Check console for error messages

### Tags not saving
- Ensure ExifTool is installed and in PATH
- Check file permissions (images must be writable)
- Look for error messages in the browser console

### Slow performance
- Use **Quick Refresh** instead of **Full Rescan**
- Reduce image folder size
- Check cache is being used (should be fast on second load)

### Port already in use
- Change the port: `python web_app.py --port 8080`
- Or stop the other process using the port

## Comparison: Web UI vs Desktop UI

| Feature | Web UI | Desktop UI |
|---------|--------|------------|
| Installation | Lightweight (Flask only) | Requires PyQt5 |
| Access | Any browser | Local only |
| Performance | Good | Excellent |
| Interface | Modern, responsive | Native Qt widgets |
| Mobile Support | Yes | No |
| Headless Export | Yes | Yes |

## Development

### Project Structure

```
GalleryTags/
├── web_app.py              # Flask application
├── web/
│   ├── templates/
│   │   └── index.html      # Main UI template
│   └── static/
│       ├── css/
│       │   └── style.css   # Styling
│       └── js/
│           └── app.js      # Client-side logic
├── core/                   # Shared backend logic
├── utils/                  # Shared utilities
└── requirements-web.txt    # Web dependencies
```

### Adding Features

1. **Backend**: Add API endpoints in `web_app.py`
2. **Frontend**: Update `app.js` for logic, `style.css` for styling
3. **UI**: Modify `index.html` for new components

## License

Same as GalleryTags main application.

## Support

For issues specific to the web UI, please include:
- Browser and version
- Python version
- Error messages from browser console
- Error messages from Flask server

## Future Enhancements

Potential improvements:
- Drag-and-drop file upload
- Image editing capabilities
- User authentication for multi-user setups
- WebSocket support for real-time updates
- Mobile-optimized interface
- PWA (Progressive Web App) support
