#!/usr/bin/env python3
"""
Simple web-based image gallery with tag search functionality
"""
import os
import json
from bottle import Bottle, request, response, static_file, template
from config import BASE_PATH, WEB_CONFIG, FORMAT_CONFIG
from core.cache import CacheManager
from core.metadata import read_tag_metadata, SUPPORTED_EXTENSIONS

app = Bottle()
cache_manager = CacheManager()

# Helper to get supported extensions
SUPPORTED_EXTENSIONS_SET = set(SUPPORTED_EXTENSIONS)

def get_subdirectories(path):
    """Get all subdirectories in a path"""
    try:
        subdirs = []
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                subdirs.append({
                    'name': item,
                    'path': item_path,
                    'relative': os.path.relpath(item_path, BASE_PATH)
                })
        return subdirs
    except Exception as e:
        print(f"Error reading directory {path}: {e}")
        return []

def get_folder_tree(path, prefix=""):
    """Build a nested folder tree structure"""
    tree = []
    try:
        subdirs = get_subdirectories(path)
        for subdir in subdirs:
            item = {
                'name': subdir['name'],
                'path': subdir['path'],
                'relative': subdir['relative'],
                'display_name': prefix + subdir['name'],
                'children': []
            }
            # Recursively get subfolders
            item['children'] = get_folder_tree_nested(subdir['path'])
            tree.append(item)
    except Exception as e:
        print(f"Error building tree for {path}: {e}")
    return tree

def get_folder_tree_nested(path):
    """Build a hierarchical nested folder tree"""
    children = []
    try:
        subdirs = get_subdirectories(path)
        for subdir in subdirs:
            item = {
                'name': subdir['name'],
                'path': subdir['path'],
                'relative': subdir['relative'],
                'children': []
            }
            # Recursively get subfolders
            item['children'] = get_folder_tree_nested(subdir['path'])
            children.append(item)
    except Exception as e:
        print(f"Error building tree for {path}: {e}")
    return children

def get_images_in_folder(folder_path, recursive=False):
    """Get all supported images in a folder"""
    images = []
    try:
        if recursive:
            for root, _, files in os.walk(folder_path):
                for filename in sorted(files):
                    if any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS_SET):
                        full_path = os.path.join(root, filename)
                        images.append(full_path)
        else:
            for filename in sorted(os.listdir(folder_path)):
                full_path = os.path.join(folder_path, filename)
                if os.path.isfile(full_path) and any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS_SET):
                    images.append(full_path)
    except Exception as e:
        print(f"Error reading images from {folder_path}: {e}")
    return images

def get_tags_for_image(image_path):
    """Get tags for an image, using cache if available and up-to-date"""
    # Check cache first
    cached_tags = cache_manager.get_cached_metadata(image_path)
    if cached_tags is not None:
        return cached_tags

    # Cache miss or outdated - read from file
    tags = read_tag_metadata(image_path)
    cache_manager.update_cache(image_path, tags)
    return tags

def parse_tags(tag_string):
    """Parse comma-separated tags into a set"""
    if not tag_string:
        return set()
    return {tag.strip().lower() for tag in tag_string.split(',') if tag.strip()}

def filter_images_by_tags(images, search_query, search_mode='AND'):
    """Filter images based on tag search query with AND/OR logic"""
    if not search_query or not search_query.strip():
        return images

    query = search_query.strip()
    required_tags = parse_tags(query)
    if not required_tags:
        return images

    is_or_mode = (search_mode == 'OR')

    filtered = []
    for image_path in images:
        tags = get_tags_for_image(image_path)
        image_tags = parse_tags(tags)

        if is_or_mode:
            # OR: Match if any required tag is present
            if any(tag in image_tags for tag in required_tags):
                filtered.append(image_path)
        else:
            # AND: Match if all required tags are present
            if all(tag in image_tags for tag in required_tags):
                filtered.append(image_path)

    return filtered

def sort_images(images, sort_option):
    """Sort images based on sort option"""
    if not images or not sort_option:
        return images

    # Extract sort criteria and direction
    if sort_option.startswith('name_'):
        # Sort by name
        reverse = sort_option.endswith('_desc')
        return sorted(images, key=lambda x: os.path.basename(x).lower(), reverse=reverse)
    elif sort_option.startswith('modified_'):
        # Sort by modification date
        reverse = sort_option.endswith('_desc')
        return sorted(images, key=lambda x: os.path.getmtime(x), reverse=reverse)
    elif sort_option.startswith('tags_'):
        # Sort by tags
        reverse = sort_option.endswith('_desc')
        # Split into tagged and untagged
        tagged = [(img, get_tags_for_image(img)) for img in images if get_tags_for_image(img)]
        untagged = [img for img in images if not get_tags_for_image(img)]

        # Sort tagged items by tag text
        tagged.sort(key=lambda x: x[1].lower(), reverse=reverse)

        # Return combined list (untagged always at end)
        return [img for img, _ in tagged] + untagged
    else:
        return images

@app.route('/')
def index():
    """Main page"""
    html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Gallery Tags</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        .toolbar {
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .toolbar-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        .toolbar h1 {
            font-size: 20px;
            margin-right: 20px;
        }
        .toolbar select, .toolbar input, .toolbar button {
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
        }
        .toolbar select {
            background: white;
        }
        .toolbar input[type="text"] {
            flex: 1;
            min-width: 200px;
        }
        .toolbar input[type="checkbox"] {
            width: auto;
            margin: 0 5px;
        }
        .toolbar button {
            background: #27ae60;
            color: white;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
        }
        .toolbar button:hover {
            background: #229954;
        }
        .toolbar button.folder-btn {
            background: #3498db;
            min-width: 200px;
            text-align: left;
            position: relative;
        }
        .toolbar button.folder-btn:hover {
            background: #2980b9;
        }
        .toolbar label {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        /* Folder Tree Popup */
        .folder-popup {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .folder-popup.active {
            display: flex;
        }
        .folder-popup-content {
            background: white;
            border-radius: 8px;
            padding: 20px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .folder-popup-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }
        .folder-popup-header h2 {
            font-size: 18px;
            color: #2c3e50;
        }
        .folder-popup-close {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 4px;
            cursor: pointer;
        }
        .folder-popup-close:hover {
            background: #c0392b;
        }
        .folder-tree {
            list-style: none;
            padding-left: 0;
        }
        .folder-tree ul {
            list-style: none;
            padding-left: 20px;
            display: none;
        }
        .folder-tree ul.expanded {
            display: block;
        }
        .folder-item {
            padding: 8px;
            margin: 2px 0;
            cursor: pointer;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .folder-item:hover {
            background: #ecf0f1;
        }
        .folder-item.selected {
            background: #3498db;
            color: white;
        }
        .folder-toggle {
            cursor: pointer;
            user-select: none;
            font-size: 12px;
            width: 16px;
            display: inline-block;
        }
        .folder-icon {
            font-size: 16px;
        }
        .container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 0 20px;
        }
        .stats {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .image-card {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .image-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }
        .image-wrapper {
            width: 100%;
            height: 250px;
            overflow: hidden;
            background: #ecf0f1;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .image-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .image-info {
            padding: 12px;
        }
        .image-name {
            font-weight: 500;
            margin-bottom: 8px;
            word-break: break-word;
            font-size: 14px;
        }
        .image-tags {
            font-size: 12px;
            color: #7f8c8d;
            line-height: 1.5;
        }
        .tag {
            display: inline-block;
            background: #e8f5e9;
            color: #2e7d32;
            padding: 2px 8px;
            border-radius: 12px;
            margin: 2px;
            font-size: 11px;
        }
        .no-tags {
            color: #95a5a6;
            font-style: italic;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <!-- Folder Tree Popup -->
    <div class="folder-popup" id="folderPopup">
        <div class="folder-popup-content">
            <div class="folder-popup-header">
                <h2>Select Folder</h2>
                <button class="folder-popup-close" onclick="closeFolderPopup()">Close</button>
            </div>
            <ul class="folder-tree" id="folderTree"></ul>
        </div>
    </div>

    <div class="toolbar">
        <div class="toolbar-content">
            <h1>Gallery Tags</h1>
            <button class="folder-btn" id="folderBtn" onclick="openFolderPopup()">
                📁 <span id="selectedFolderText">Select a folder...</span>
            </button>
            <label>
                <input type="checkbox" id="recursiveToggle">
                Recursive
            </label>
            <select id="searchMode">
                <option value="AND">AND</option>
                <option value="OR">OR</option>
            </select>
            <input type="text" id="searchInput" placeholder="Search tags (comma separated)">
            <select id="sortSelect">
                <option value="name_asc">Name (ascending)</option>
                <option value="name_desc">Name (descending)</option>
                <option value="modified_asc">Modified Date (ascending)</option>
                <option value="modified_desc">Modified Date (descending)</option>
                <option value="tags_asc">Tags (ascending)</option>
                <option value="tags_desc">Tags (descending)</option>
            </select>
            <button onclick="loadImages()">Load</button>
            <button onclick="refreshAll()">Refresh All</button>
        </div>
    </div>

    <div class="container">
        <div class="stats" id="stats" style="display: none;">
            <strong>Status:</strong> <span id="statusText">Ready</span>
        </div>

        <div class="gallery" id="gallery"></div>
    </div>

    <script>
        let selectedFolder = '';
        let folderData = [];

        // Load folder tree on page load
        fetch('/api/folders')
            .then(res => res.json())
            .then(data => {
                folderData = data.folders;
                buildFolderTree(data.folders);
            })
            .catch(err => console.error('Error loading folders:', err));

        function buildFolderTree(folders) {
            const tree = document.getElementById('folderTree');
            tree.innerHTML = '';

            folders.forEach(folder => {
                const li = createFolderItem(folder);
                tree.appendChild(li);
            });
        }

        function createFolderItem(folder) {
            const li = document.createElement('li');

            const itemDiv = document.createElement('div');
            itemDiv.className = 'folder-item';
            itemDiv.dataset.relative = folder.relative;

            // Add toggle arrow if has children
            const toggle = document.createElement('span');
            toggle.className = 'folder-toggle';
            if (folder.children && folder.children.length > 0) {
                toggle.textContent = '▶';
                toggle.onclick = (e) => {
                    e.stopPropagation();
                    const ul = li.querySelector('ul');
                    if (ul) {
                        ul.classList.toggle('expanded');
                        toggle.textContent = ul.classList.contains('expanded') ? '▼' : '▶';
                    }
                };
            } else {
                toggle.textContent = ' ';
            }
            itemDiv.appendChild(toggle);

            // Add folder icon and name
            const icon = document.createElement('span');
            icon.className = 'folder-icon';
            icon.textContent = '📁';
            itemDiv.appendChild(icon);

            const name = document.createElement('span');
            name.textContent = folder.name;
            itemDiv.appendChild(name);

            // Add click handler for selection
            itemDiv.onclick = () => selectFolder(folder.relative, folder.name, itemDiv);

            li.appendChild(itemDiv);

            // Add children if present
            if (folder.children && folder.children.length > 0) {
                const ul = document.createElement('ul');
                folder.children.forEach(child => {
                    ul.appendChild(createFolderItem(child));
                });
                li.appendChild(ul);
            }

            return li;
        }

        function selectFolder(relative, name, element) {
            // Remove previous selection
            document.querySelectorAll('.folder-item').forEach(item => {
                item.classList.remove('selected');
            });

            // Set new selection
            element.classList.add('selected');
            selectedFolder = relative;

            // Update button text
            document.getElementById('selectedFolderText').textContent = name;
        }

        function openFolderPopup() {
            document.getElementById('folderPopup').classList.add('active');
        }

        function closeFolderPopup() {
            document.getElementById('folderPopup').classList.remove('active');
        }

        // Close popup when clicking outside
        document.getElementById('folderPopup').addEventListener('click', (e) => {
            if (e.target.id === 'folderPopup') {
                closeFolderPopup();
            }
        });

        function loadImages() {
            const folder = selectedFolder;
            const recursive = document.getElementById('recursiveToggle').checked;
            const search = document.getElementById('searchInput').value;
            const searchMode = document.getElementById('searchMode').value;
            const sort = document.getElementById('sortSelect').value;

            if (!folder) {
                alert('Please select a folder first');
                return;
            }

            document.getElementById('stats').style.display = 'block';
            document.getElementById('statusText').textContent = 'Loading...';
            document.getElementById('gallery').innerHTML = '<div class="loading">Loading images...</div>';

            const params = new URLSearchParams({
                folder: folder,
                recursive: recursive ? '1' : '0',
                search: search,
                search_mode: searchMode,
                sort: sort
            });

            fetch('/api/images?' + params)
                .then(res => res.json())
                .then(data => {
                    document.getElementById('statusText').textContent =
                        `Found ${data.images.length} image(s) in ${folder}`;
                    displayImages(data.images);
                })
                .catch(err => {
                    console.error('Error loading images:', err);
                    document.getElementById('gallery').innerHTML =
                        '<div class="loading">Error loading images</div>';
                });
        }

        function displayImages(images) {
            const gallery = document.getElementById('gallery');

            if (images.length === 0) {
                gallery.innerHTML = '<div class="loading">No images found</div>';
                return;
            }

            gallery.innerHTML = '';
            images.forEach(img => {
                const card = document.createElement('div');
                card.className = 'image-card';

                const tags = img.tags ? img.tags.split(',').map(t => t.trim()).filter(t => t) : [];
                const tagsHtml = tags.length > 0
                    ? tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')
                    : '<span class="no-tags">No tags</span>';

                card.innerHTML = `
                    <div class="image-wrapper">
                        <img src="/image?path=${encodeURIComponent(img.path)}"
                             alt="${escapeHtml(img.name)}"
                             loading="lazy">
                    </div>
                    <div class="image-info">
                        <div class="image-name">${escapeHtml(img.name)}</div>
                        <div class="image-tags">${tagsHtml}</div>
                    </div>
                `;

                gallery.appendChild(card);
            });
        }

        function refreshAll() {
            const folder = selectedFolder;
            const recursive = document.getElementById('recursiveToggle').checked;

            if (!folder) {
                alert('Please select a folder first');
                return;
            }

            const recursiveText = recursive ? ' (recursively)' : '';
            if (!confirm(`This will refresh modified files in the current folder${recursiveText}. Continue?`)) {
                return;
            }

            document.getElementById('statusText').textContent = 'Refreshing cache...';

            const params = new URLSearchParams({
                folder: folder,
                recursive: recursive ? '1' : '0'
            });

            fetch('/api/refresh?' + params, { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('statusText').textContent = data.message;
                    alert(data.message);
                    // Reload images to show updated tags
                    loadImages();
                })
                .catch(err => {
                    console.error('Error refreshing:', err);
                    alert('Error refreshing cache');
                });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Allow Enter key to trigger search
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                loadImages();
            }
        });
    </script>
</body>
</html>
    '''
    return html

@app.route('/api/folders')
def api_folders():
    """Get folder tree"""
    response.content_type = 'application/json'

    if not os.path.exists(BASE_PATH):
        return json.dumps({'error': 'BASE_PATH does not exist', 'folders': []})

    folders = get_folder_tree(BASE_PATH)
    return json.dumps({'folders': folders})

@app.route('/api/images')
def api_images():
    """Get images in a folder with optional search and sorting"""
    response.content_type = 'application/json'

    folder_rel = request.query.get('folder', '')
    recursive = request.query.get('recursive', '0') == '1'
    search_query = request.query.get('search', '')
    search_mode = request.query.get('search_mode', 'AND')
    sort_option = request.query.get('sort', '')

    if not folder_rel:
        return json.dumps({'error': 'No folder specified', 'images': []})

    folder_path = os.path.join(BASE_PATH, folder_rel)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return json.dumps({'error': 'Invalid folder', 'images': []})

    # Get all images
    images = get_images_in_folder(folder_path, recursive)

    # Filter by search query if provided
    if search_query:
        images = filter_images_by_tags(images, search_query, search_mode)

    # Sort images if sort option provided
    if sort_option:
        images = sort_images(images, sort_option)

    # Build response with image info
    result = []
    for img_path in images:
        tags = get_tags_for_image(img_path)
        result.append({
            'path': img_path,
            'name': os.path.basename(img_path),
            'tags': tags
        })

    # Save cache after processing
    cache_manager.save_cache()

    return json.dumps({'images': result})

@app.route('/image')
def serve_image():
    """Serve an image file"""
    image_path = request.query.get('path', '')

    if not image_path or not os.path.exists(image_path):
        response.status = 404
        return 'Image not found'

    # Security check: ensure the path is within BASE_PATH
    real_path = os.path.realpath(image_path)
    real_base = os.path.realpath(BASE_PATH)

    if not real_path.startswith(real_base):
        response.status = 403
        return 'Access denied'

    directory = os.path.dirname(image_path)
    filename = os.path.basename(image_path)

    return static_file(filename, root=directory)

@app.route('/api/refresh', method='POST')
def api_refresh():
    """Refresh cache for modified files in specified folder"""
    response.content_type = 'application/json'

    folder_rel = request.query.get('folder', '')
    recursive = request.query.get('recursive', '0') == '1'

    if not folder_rel:
        response.status = 400
        return json.dumps({'error': 'No folder specified'})

    folder_path = os.path.join(BASE_PATH, folder_rel)
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        response.status = 400
        return json.dumps({'error': 'Invalid folder'})

    try:
        # Get all images in folder
        images = get_images_in_folder(folder_path, recursive)

        refreshed_count = 0
        skipped_count = 0

        for img_path in images:
            norm_path = os.path.normpath(img_path)
            current_mtime = os.path.getmtime(img_path)

            # Check if file needs refresh
            needs_refresh = False

            if norm_path in cache_manager.cache_data:
                cached_mtime = cache_manager.cache_data[norm_path]['mtime']
                # Refresh if file is newer than cache (allowing 0.1s tolerance)
                if current_mtime - cached_mtime > 0.1:
                    needs_refresh = True
                else:
                    skipped_count += 1
            else:
                # Not in cache, needs refresh
                needs_refresh = True

            if needs_refresh:
                # Force re-read from file
                tags = read_tag_metadata(img_path)
                cache_manager.update_cache(img_path, tags)
                refreshed_count += 1

        # Save updated cache
        cache_manager.save_cache()

        message = f'Refreshed {refreshed_count} modified file(s), skipped {skipped_count} up-to-date file(s)'
        return json.dumps({'message': message, 'refreshed': refreshed_count, 'skipped': skipped_count})

    except Exception as e:
        response.status = 500
        return json.dumps({'error': str(e)})

if __name__ == '__main__':
    # Verify BASE_PATH exists
    if not os.path.exists(BASE_PATH):
        print(f"ERROR: BASE_PATH does not exist: {BASE_PATH}")
        print("Please update BASE_PATH in config.py to point to your image directory")
        exit(1)

    print(f"Starting Gallery Tags web server...")
    print(f"BASE_PATH: {BASE_PATH}")
    print(f"Access the gallery at: http://{WEB_CONFIG['host']}:{WEB_CONFIG['port']}")

    app.run(
        host=WEB_CONFIG['host'],
        port=WEB_CONFIG['port'],
        debug=WEB_CONFIG['debug']
    )
