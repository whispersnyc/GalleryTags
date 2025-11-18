# GalleryTags - Web UI

A modern, intuitive bulk image tagging tool with a browser-based interface. Perfect for organizing images that belong to multiple categories without the hassle of folder hierarchies. Export your tagged galleries as markdown files!

- Built with Obsidian integration in mind, usable generally
- Supports JPG, PNG, and WebP formats
- Tag recalculation ensures only used tags are shown
- Multi-image navigation in modal editor
- Mobile-friendly with touch-hold support
- Headless CLI mode for automation

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install flask flask-cors pillow
   ```

2. **Install ExifTool:**
   Download from [exiftool.org](https://exiftool.org/) and ensure it's in your system PATH

3. **Configure (optional):**
   ```bash
   cp config.py.example config.py
   # Edit config.py to set default folder and export settings
   ```

4. **Launch the web UI:**
   ```bash
   python app.py
   ```

   Or use the launcher scripts:
   - Linux/Mac: `./run_web.sh`
   - Windows: `run_web.bat`

5. **Open in browser:**
   Navigate to `http://127.0.0.1:5000`

## Web UI Features

### Modern Modal Editor
- Refined tag panel with vertical scrolling
- **Tag buttons**: Click to toggle tags on/off
- **Right-click or long-press** (750ms) on tags to remove from all images in modal
- **"+ Add New" button**: Opens browser prompt to create new tags
- **Tag recalculation**: Only shows tags currently in use across your gallery
- Unused tags are automatically removed when modal closes

### Multi-Image Navigation
- **Left/Right arrows**: Navigate through selected images in the modal
- **Dot indicators**: Show which image you're viewing in the sequence
- **Gallery-style browsing**: Edit tags for multiple images without closing the modal

### Image Selection & Management
- **Drag to select**: Click and drag across images to select multiple
- **Ctrl+Click**: Toggle individual images
- **Shift+Click**: Range selection
- **Double-click**: Open image in modal editor
- **Batch tagging**: Apply tags to all selected images at once

### Search & Filter
- **Search box**: Enter comma-separated tags to filter images
- **AND/OR modes**:
  - AND: Show images with all specified tags
  - OR: Show images with any specified tag
- **Live filtering**: Results update as you type

### Sorting Options
- Name (A-Z or Z-A)
- Date (Newest or Oldest)
- Tags (A-Z or Z-A)

### Export System
- **Directory-specific configs**: Each folder can have its own `.gallery_export.json`
- **Tag-based exports**: Generate markdown galleries filtered by tags
- **Grid support**: Compatible with Obsidian Media Grid plugin
- **Relative paths**: Exports use relative paths for portability
- **OR/AND logic**: Prefix tags with `|` for OR mode, `&` for AND (default)

### Statistics
- View total images, file sizes, and unique tags
- **Tag cloud**: Click any tag to filter the gallery
- Track your tagging progress

### Performance
- **Smart caching**: Metadata is cached for fast loading
- **Quick refresh**: Only updates modified files
- **Full rescan**: Force re-read of all metadata when needed

## Gallery Export

Create a `.gallery_export.json` file in your image directory:

```json
{
  "notes/characters.md": "character, portrait",
  "notes/locations/index.md": "| location, landmark",
  "reference/weapons.md": "weapon"
}
```

- **Relative paths**: Files are created relative to the image directory
- **OR mode**: Prefix with `|` (e.g., `"| tag1, tag2"`)
- **AND mode**: Default or prefix with `&`

Configure export format in `config.py`:
```python
EXPORT_CONFIG = {
    'item_format': '![]($fp/$fn.$fe)\n',  # Image format
    'heading': '# Gallery\n\n',            # File header
    'group_by': 0                           # Images per row (0 = no grouping)
}
```

## CLI / Headless Mode

Run exports without the web UI for automation:

```bash
# Use directory's .gallery_export.json
python app.py path/to/images

# Use specific config file
python app.py path/to/custom_export.json
```

Perfect for scripts, cron jobs, or CI/CD pipelines.

## Keyboard Shortcuts

- **Ctrl+O**: Open folder
- **Ctrl+A**: Select all / Deselect all
- **Ctrl+R**: Quick refresh (modified files only)
- **Ctrl+Shift+R**: Full rescan (all files)
- **Ctrl+F**: Focus search box
- **Ctrl+E**: Open export dialog
- **Enter**: Apply tags to selected images
- **Escape**: Clear selection or close modals

## Mobile Support

- **Touch-friendly**: All UI elements are optimized for touch
- **Responsive layout**: Adapts to mobile screens
- **Touch-hold**: Press and hold a tag for 750ms to reset it (same as right-click)
- **Haptic feedback**: Vibration on supported devices

## Configuration

The `config.py` file contains all customization options:

```python
# App settings
APP_CONFIG = {
    'default_folder': '/path/to/your/images'  # Auto-load on startup
}

# Export format
EXPORT_CONFIG = {
    'item_format': '![]($fp/$fn.$fe)\n',     # Obsidian-style image links
    'heading': '# Gallery\n\n',
    'group_by': 0                             # Grid layout (0 = list)
}

# Metadata fields per format
FORMAT_CONFIG = {
    'jpeg': {
        'extensions': ['.jpg', '.jpeg'],
        'field': '-ImageDescription'          # EXIF field
    },
    'png': {
        'extensions': ['.png'],
        'field': '-Description'               # PNG field
    },
    # ...
}
```

## Technical Details

### Architecture
- **Backend**: Flask REST API
- **Frontend**: Vanilla JavaScript (no framework bloat)
- **Storage**: ExifTool for metadata, JSON for cache
- **Cache**: Platform-specific cache directory for fast loads

### Tag Recalculation
Tags are recalculated when:
- Gallery loads
- Modal opens
- Tags are saved
- Batch tags are applied

This ensures the tag list only shows tags actually in use.

### Cache System
- Automatic caching in platform-specific directories:
  - Windows: `%LOCALAPPDATA%\GalleryTags`
  - Linux/Mac: `~/.config/gallerytags`
- Only updates when files are modified
- Survives app restarts

## Advanced Options

### Custom Metadata Fields
Edit `FORMAT_CONFIG` in `config.py` to use different metadata fields:

```python
FORMAT_CONFIG = {
    'jpeg': {
        'extensions': ['.jpg', '.jpeg'],
        'field': '-Subject'  # Use Subject instead of ImageDescription
    }
}
```

### Command Line Arguments
```bash
python app.py --host 0.0.0.0 --port 8080 --debug
```

Options:
- `--host`: Bind address (default: 127.0.0.1)
- `--port`: Port number (default: 5000)
- `--debug`: Enable Flask debug mode

## Troubleshooting

**ExifTool not found:**
- Make sure ExifTool is installed and in your PATH
- Test by running `exiftool -ver` in terminal

**Images not loading:**
- Check file permissions
- Verify image formats are supported (.jpg, .jpeg, .png, .webp)
- Try a full rescan (Ctrl+Shift+R)

**Tags not saving:**
- Ensure write permissions on image files
- Check ExifTool supports the file format
- Look for error messages in the terminal

**Cache issues:**
- Delete the cache file manually:
  - Windows: `%LOCALAPPDATA%\GalleryTags\gallery_cache.json`
  - Linux/Mac: `~/.config/gallerytags/gallery_cache.json`

## Development

The project structure is simple and hackable:

```
GalleryTags/
├── app.py              # Main entry point (Flask app)
├── web_app.py          # Same as app.py (kept for compatibility)
├── core/
│   ├── metadata.py     # ExifTool integration
│   └── cache.py        # Cache management
├── utils/
│   └── helpers.py      # Utility functions
├── web/
│   ├── templates/
│   │   └── index.html  # Single-page application
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js  # Frontend logic
└── config.py           # Configuration
```

## Obsidian Integration

Works great with:
- [Image Metadata Plugin](https://github.com/alexeiskachykhin/obsidian-image-metadata-plugin) - Display tags in Obsidian
- [Media Grid Plugin](https://github.com/IshikuraPC/Media-Grid-plugin) - Grid layouts for galleries

Default config is compatible with these plugins out of the box.

## License

Use freely, modify as needed, no warranties provided.

## Acknowledgments

Built as a vibe-coding experiment. Rewritten from desktop (PyQt5) to modern web UI.

---

**Note:** The old desktop UI has been archived in `.archive/desktop-ui/` if you need it.
