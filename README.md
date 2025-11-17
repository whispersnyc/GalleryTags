# GalleryTags

This is a fresh take on intuitive and speedy bulk image tagging tool.
It's an alternative to trying to sort images in folders when they could belong to multiple categories. Definitely easier to use than your typical cluttered and overcomplicated photographer software, too.
You can even export search results as markdown galleries!
- Built with Obsidian integration but usable generally
- Supports JPG, PNG, and WebP formats
- Headless mode for advanced users
- **Now available as a Web UI!** (see below)

Disclaimer: This was a vibe-coding experiment that went really well. However, I'm not responsible for any edge case data loss so use Git if thats crucial.

## Choose Your Interface

### 🌐 Web UI (Recommended)

Modern browser-based interface with full functionality:

```bash
# Install dependencies
pip install -r requirements-web.txt

# Run the web server
python web_app.py

# Or use the launcher scripts
./run_web.sh        # Linux/Mac
run_web.bat         # Windows
```

Then open http://127.0.0.1:5000 in your browser.

**See [README_WEB.md](README_WEB.md) for complete web UI documentation.**

### 🖥️ Desktop UI (Classic)

Traditional PyQt5 desktop application:

```bash
# Install dependencies
pip install PyQt5 Pillow

# Run the desktop app
python app.py
```

**Both interfaces share the same core functionality and can be used interchangeably.**

## Quick Start

1. Install [ExifTool](https://exiftool.org/) and ensure it's in your system PATH
2. Choose your preferred interface (Web or Desktop) and install dependencies
3. (Optional) Rename `config.py.example` to `config.py` and customize settings
4. Run the application using the commands above

## Basic Usage

- **Open Folder**: Click "Open Folder" or press Ctrl+O
- **Select Images**: Click and drag to select multiple images
- **Add Tags**: Press Enter to add tags to selected images
- **Quick Edit**: Double-click an image to edit its tags directly
- **Search**: Use the search box to filter by tags (comma-separated)
- **Refresh**: Use Quick Refresh (Ctrl+R) to update modified files

## CLI Usage

Optionally run exports without launching the GUI for advanced users:
```bash
# Use directory's .gallery_export.json
python app.py path/to/images

# Use specific config file
python app.py path/to/custom_export.json
```

The app will:
1. Load the specified config
2. Process all images in the directory
3. Generate markdown files according to the export rules
4. Update the cache
5. Exit with code 0 on success, 1 on error

## Feature Details

### Image Selection
- Click and drag to select multiple images
- Double-click an image for detailed view and tag editing
- Press Escape to clear selection
- Use "Select All" (Ctrl+A) to toggle selection of all visible images

### Tag Management
- Add tags via Enter key or "Add Tag" button when images are selected
- Tags are comma-separated
- Double-click an image for single-image tag editing
- Tags are stored in metadata (configurable)
    - Default settings compatibile with [Obsidian Image Metadata plugin](alexeiskachykhin/obsidian-image-metadata-plugin)

### Export System
- Directory-specific export configurations
- GUI and CLI support for exports
- Export Markdown format gallery files (customizable)
- Support for relative paths in exports
- Grid formatting support for Obsidian Media Grid plugin
- Headless operation for automation/scripts

### Search & Sort
- Search box supports comma-separated tags
- Toggle AND/OR mode for searching:
  - AND: All tags must match
  - OR: Any tag must match
- Sort options:
  - Name (ascending/descending)
  - Modified Date (ascending/descending)
  - Tags (ascending/descending)

### Cache System
- Automatic caching of tag data for fast loading
- Multiple refresh options:
  - Quick Refresh (Ctrl+R): Updates only modified files
  - Full Rescan: Re-reads all metadata
  - Auto-refresh on startup: Only checks modified files

## Gallery Export

Each directory can have its own `.gallery_export.json` file that defines export rules.
The exported files will contain all your images that match the respective tag queries.
This file is generated/edited by an intuitive GUI in the app; same `|` / `&` logic applies.

```json
{
  "notes/characters.md": "character, portrait",
  "notes/locations/index.md": "| location, landmark",
  "reference/weapons.md": "weapon"
}
```

- File paths can be relative to the gallery directory
- Prefix tags with `|` for OR mode, `&` for AND mode (default)
- Configure export format in `config.py`:
  - `item_format`: Template for each image entry
  - `heading`: Text to add at start of file
  - `group_by`: Number of images per row (for grid layouts)

## Configuration

Copy `config.py.example` to `config.py` and customize:

- `APP_CONFIG['default_folder']`: Default folder to open on startup
- `EXPORT_CONFIG`: Export formatting settings
- `FORMAT_CONFIG`: Metadata field configuration per file type

## Keyboard Shortcuts

- `Ctrl+O`: Open folder
- `Ctrl+A`: Select/deselect all
- `Ctrl+R`: Quick refresh
- `Ctrl+Shift+R`: Full rescan
- `Ctrl+F`: Focus search box
- `Ctrl+E`: Show export dialog
- `Ctrl+Shift+E`: Export without refresh
- `Enter`: Add tag to selection
- `Escape`: Clear selection