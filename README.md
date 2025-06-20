# GalleryTags

Intuitive and speedy bulk image tagging tool with Markdown gallery export capabilities.
- Built with Obsidian integration but usable generally
- Supports JPG, PNG, and WebP formats

## Quick Start

1. Install dependencies:
   ```bash
   pip install PyQt5 Pillow
   ```
2. Install [ExifTool](https://exiftool.org/) and ensure it's in your system PATH
3. Rename `config.py.example` to `config.py` and customize settings if desired
4. Run the app:
   ```bash
   python main.py
   ```

## Basic Usage

- **Open Folder**: Click "Open Folder" or press Ctrl+O
- **Select Images**: Click and drag to select multiple images
- **Add Tags**: Press Enter to add tags to selected images
- **Quick Edit**: Double-click an image to edit its tags directly
- **Search**: Use the search box to filter by tags (comma-separated)
- **Refresh**: Use Quick Refresh (Ctrl+R) to update modified files

## Features in Detail

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
- Export Markdown format gallery files (customizable)
- Support for relative paths in exports
- Grid formatting support for Obsidian Media Grid plugin

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