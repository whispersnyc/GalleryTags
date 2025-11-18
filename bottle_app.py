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
            justify-content: space-between;
        }
        .toolbar-left {
            display: flex;
            gap: 10px;
            align-items: center;
            flex: 1;
        }
        .toolbar-center {
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: center;
            flex: 1;
        }
        .toolbar-right {
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: flex-end;
            flex: 1;
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
        .toolbar button.select-btn {
            background: #95a5a6;
            transition: background 0.2s;
        }
        .toolbar button.select-btn:hover {
            background: #7f8c8d;
        }
        .toolbar button.select-btn.active {
            background: #3498db;
        }
        .toolbar button.select-btn.active:hover {
            background: #2980b9;
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
        .folder-popup-footer {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 2px solid #ecf0f1;
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: flex-end;
        }
        .folder-popup-footer label {
            display: flex;
            align-items: center;
            gap: 5px;
            color: #2c3e50;
        }
        .folder-popup-footer button {
            background: #27ae60;
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }
        .folder-popup-footer button:hover {
            background: #229954;
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
        /* Tag Bar */
        .tag-bar {
            background: white;
            padding: 15px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: none;
        }
        .tag-bar.visible {
            display: block;
        }
        .tag-bar-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .tag-bar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .tag-bar-header h3 {
            font-size: 14px;
            color: #2c3e50;
            margin: 0;
        }
        .tag-bar-controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .tag-bar-controls select {
            padding: 5px 10px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            font-size: 12px;
            background: white;
            cursor: pointer;
        }
        .tag-bar-clear {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 5px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .tag-bar-clear:hover {
            background: #c0392b;
        }
        .tag-bar-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            max-height: 200px;
            overflow-y: auto;
        }
        .tag-button {
            background: #ecf0f1;
            color: #2c3e50;
            border: 2px solid #bdc3c7;
            padding: 6px 12px;
            border-radius: 16px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
            user-select: none;
        }
        .tag-button:hover {
            background: #d5dbdb;
        }
        .tag-button.active {
            background: #3498db;
            color: white;
            border-color: #2980b9;
        }
        /* Image Modal */
        .image-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 2000;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            padding: 20px;
        }
        .image-modal.active {
            display: flex;
        }
        .image-modal-content {
            display: flex;
            flex-direction: column;
            max-width: 90vw;
            max-height: 90vh;
            gap: 15px;
        }
        .image-modal-image {
            max-width: 100%;
            max-height: 70vh;
            object-fit: contain;
            border-radius: 8px;
        }
        .image-modal-editor {
            background: white;
            padding: 15px;
            border-radius: 8px;
            min-width: 500px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .image-modal-editor label {
            font-weight: 500;
            color: #2c3e50;
            font-size: 14px;
        }
        .modal-tags-container {
            max-height: 150px;
            overflow-y: auto;
            border: 2px solid #bdc3c7;
            border-radius: 4px;
            padding: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            min-height: 50px;
        }
        .modal-tags-container.empty {
            align-items: center;
            justify-content: center;
            color: #95a5a6;
            font-style: italic;
            font-size: 13px;
        }
        .modal-tag-button {
            background: #ecf0f1;
            color: #2c3e50;
            border: 2px solid #bdc3c7;
            padding: 4px 10px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
            user-select: none;
        }
        .modal-tag-button:hover {
            background: #d5dbdb;
        }
        .modal-tag-button.active {
            background: #e8f5e9;
            color: #2e7d32;
            border-color: #81c784;
        }
        .modal-tag-button.partial {
            background: #e3f2fd;
            color: #1565c0;
            border-color: #64b5f6;
        }
        .image-modal-input {
            width: 100%;
            padding: 10px;
            border: 2px solid #bdc3c7;
            border-radius: 4px;
            font-family: inherit;
            font-size: 14px;
            box-sizing: border-box;
        }
        .image-modal-input:focus {
            outline: none;
            border-color: #3498db;
        }
        .image-modal-hint {
            font-size: 12px;
            color: #7f8c8d;
        }
        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #2c3e50;
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.3s, transform 0.3s;
            z-index: 3000;
            pointer-events: none;
        }
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        .toast.success {
            background: #27ae60;
        }
        .toast.info {
            background: #3498db;
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
        .image-card.selected {
            box-shadow: 0 0 0 3px #3498db;
            transform: translateY(-2px);
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
        /* Floating Edit Button */
        .floating-edit-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #3498db;
            color: white;
            border: none;
            padding: 15px 25px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
            display: none;
            align-items: center;
            gap: 8px;
            z-index: 999;
            transition: all 0.3s;
        }
        .floating-edit-btn.visible {
            display: flex;
        }
        .floating-edit-btn:hover {
            background: #2980b9;
            transform: scale(1.05);
            box-shadow: 0 6px 16px rgba(52, 152, 219, 0.5);
        }
        .floating-edit-btn .count-badge {
            background: rgba(255, 255, 255, 0.3);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 14px;
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
            <div class="folder-popup-footer">
                <label>
                    <input type="checkbox" id="recursiveToggle">
                    Recursive
                </label>
                <button onclick="loadImagesAndClose()">Load</button>
            </div>
        </div>
    </div>

    <!-- Image Modal -->
    <div class="image-modal" id="imageModal">
        <div class="image-modal-content">
            <img class="image-modal-image" id="modalImage" src="" alt="">
            <div class="image-modal-editor">
                <label>Tags (click to toggle):</label>
                <div class="modal-tags-container" id="modalTagsContainer">
                    <span>No tags available</span>
                </div>
                <label for="modalTagInput">Add New Tag:</label>
                <input type="text" id="modalTagInput" class="image-modal-input" placeholder="Type new tag name and press Enter...">
                <div class="image-modal-hint">Click tags to toggle • Type to add new • Enter to save • Escape to cancel</div>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toast"></div>

    <!-- Floating Edit Button -->
    <button class="floating-edit-btn" id="floatingEditBtn" onclick="openMultiEditModal()">
        ✏️ Edit <span class="count-badge" id="editBtnCount">0</span>
    </button>

    <div class="toolbar">
        <div class="toolbar-content">
            <div class="toolbar-left">
                <button class="select-btn" id="selectBtn" onclick="toggleSelectionMode()">Select</button>
                <select id="sortSelect" onchange="applySorting()">
                    <option value="name_asc">Name (ascending)</option>
                    <option value="name_desc">Name (descending)</option>
                    <option value="modified_asc">Modified Date (ascending)</option>
                    <option value="modified_desc">Modified Date (descending)</option>
                    <option value="tags_asc">Tags (ascending)</option>
                    <option value="tags_desc">Tags (descending)</option>
                </select>
            </div>
            <div class="toolbar-center">
                <button class="folder-btn" id="folderBtn" onclick="openFolderPopup()">
                    📁 <span id="selectedFolderText">Select a folder...</span>
                </button>
            </div>
            <div class="toolbar-right">
                <button onclick="toggleTagBar()">🏷️ Tags</button>
                <button onclick="refreshAll()" title="Refresh All">🔄</button>
            </div>
        </div>
    </div>

    <!-- Tag Bar -->
    <div class="tag-bar" id="tagBar">
        <div class="tag-bar-content">
            <div class="tag-bar-header">
                <h3>Filter by Tags (<span id="tagCount">0</span> tags found):</h3>
                <div class="tag-bar-controls">
                    <select id="searchMode" onchange="filterImages()">
                        <option value="AND">AND</option>
                        <option value="OR">OR</option>
                    </select>
                    <button class="tag-bar-clear" onclick="clearSelectedTags()">Clear Selection</button>
                </div>
            </div>
            <div class="tag-bar-tags" id="tagBarTags">
                <span style="color: #95a5a6; font-style: italic;">Load a folder to see tags...</span>
            </div>
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
        let allImages = [];
        let selectedTags = new Set();
        let allTags = new Set();
        let selectedImageCards = new Set();
        let isMultiEditMode = false;
        let multiEditImages = [];
        let isSelectionMode = false;

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

        function loadImagesAndClose() {
            loadImages();
            closeFolderPopup();
        }

        // Close popup when clicking outside
        document.getElementById('folderPopup').addEventListener('click', (e) => {
            if (e.target.id === 'folderPopup') {
                closeFolderPopup();
            }
        });

        function toggleTagBar() {
            const tagBar = document.getElementById('tagBar');
            tagBar.classList.toggle('visible');
        }

        function clearSelectedTags() {
            selectedTags.clear();
            document.querySelectorAll('.tag-button').forEach(btn => {
                btn.classList.remove('active');
            });
            filterImages();
        }

        function loadImages() {
            const folder = selectedFolder;
            const recursive = document.getElementById('recursiveToggle').checked;
            const sort = document.getElementById('sortSelect').value;

            if (!folder) {
                alert('Please select a folder first');
                return;
            }

            // Clear selected tags
            selectedTags.clear();

            document.getElementById('stats').style.display = 'block';
            document.getElementById('statusText').textContent = 'Loading...';
            document.getElementById('gallery').innerHTML = '<div class="loading">Loading images...</div>';

            // Load images without search filter to get all images and tags
            const params = new URLSearchParams({
                folder: folder,
                recursive: recursive ? '1' : '0',
                sort: sort
            });

            fetch('/api/images?' + params)
                .then(res => res.json())
                .then(data => {
                    allImages = data.images;

                    // Extract all unique tags
                    allTags.clear();
                    allImages.forEach(img => {
                        if (img.tags) {
                            const tags = img.tags.split(',').map(t => t.trim().toLowerCase()).filter(t => t);
                            tags.forEach(tag => allTags.add(tag));
                        }
                    });

                    // Update tag bar
                    buildTagBar();

                    document.getElementById('statusText').textContent =
                        `Found ${allImages.length} image(s) in ${folder}`;

                    // Display all images initially
                    displayImages(allImages);
                })
                .catch(err => {
                    console.error('Error loading images:', err);
                    document.getElementById('gallery').innerHTML =
                        '<div class="loading">Error loading images</div>';
                });
        }

        function buildTagBar() {
            const tagBarTags = document.getElementById('tagBarTags');
            const tagCount = document.getElementById('tagCount');

            tagBarTags.innerHTML = '';
            tagCount.textContent = allTags.size;

            if (allTags.size === 0) {
                tagBarTags.innerHTML = '<span style="color: #95a5a6; font-style: italic;">No tags found</span>';
                return;
            }

            // Sort tags alphabetically
            const sortedTags = Array.from(allTags).sort();

            sortedTags.forEach(tag => {
                const btn = document.createElement('button');
                btn.className = 'tag-button';
                btn.textContent = tag;
                btn.onclick = () => toggleTag(tag, btn);
                tagBarTags.appendChild(btn);
            });
        }

        function toggleTag(tag, button) {
            if (selectedTags.has(tag)) {
                selectedTags.delete(tag);
                button.classList.remove('active');
            } else {
                selectedTags.add(tag);
                button.classList.add('active');
            }
            filterImages();
        }

        function filterImages() {
            if (selectedTags.size === 0) {
                // Show all images
                displayImages(allImages);
                return;
            }

            const searchMode = document.getElementById('searchMode').value;
            const filtered = allImages.filter(img => {
                if (!img.tags) return false;

                const imageTags = new Set(
                    img.tags.split(',').map(t => t.trim().toLowerCase()).filter(t => t)
                );

                if (searchMode === 'OR') {
                    // OR: Match if any selected tag is present
                    return Array.from(selectedTags).some(tag => imageTags.has(tag));
                } else {
                    // AND: Match if all selected tags are present
                    return Array.from(selectedTags).every(tag => imageTags.has(tag));
                }
            });

            displayImages(filtered);
            document.getElementById('statusText').textContent =
                `Found ${filtered.length} of ${allImages.length} image(s) matching filter`;
        }

        function applySorting() {
            const sortOption = document.getElementById('sortSelect').value;

            // Get currently displayed images (respecting filters)
            const gallery = document.getElementById('gallery');
            const cards = Array.from(gallery.querySelectorAll('.image-card'));

            if (cards.length === 0) return;

            // Extract image data from cards
            let imagesToSort = cards.map(card => ({
                path: card.dataset.path,
                name: card.dataset.name,
                tags: card.dataset.tags || ''
            }));

            // Sort the images
            if (sortOption.startsWith('name_')) {
                const reverse = sortOption.endsWith('_desc');
                imagesToSort.sort((a, b) => {
                    const comparison = a.name.toLowerCase().localeCompare(b.name.toLowerCase());
                    return reverse ? -comparison : comparison;
                });
            } else if (sortOption.startsWith('modified_')) {
                // For client-side sorting, we need mtime from allImages
                const reverse = sortOption.endsWith('_desc');
                const pathToImage = new Map(allImages.map(img => [img.path, img]));
                imagesToSort.sort((a, b) => {
                    const imgA = pathToImage.get(a.path);
                    const imgB = pathToImage.get(b.path);
                    // We don't have mtime on client, so reload from server
                    return 0; // Will trigger server reload
                });
                // Reload with server-side sorting for modified date
                loadImages();
                return;
            } else if (sortOption.startsWith('tags_')) {
                const reverse = sortOption.endsWith('_desc');
                const tagged = imagesToSort.filter(img => img.tags);
                const untagged = imagesToSort.filter(img => !img.tags);

                tagged.sort((a, b) => {
                    const comparison = a.tags.toLowerCase().localeCompare(b.tags.toLowerCase());
                    return reverse ? -comparison : comparison;
                });

                imagesToSort = [...tagged, ...untagged];
            }

            // Re-display with new order
            displayImages(imagesToSort);
        }

        function displayImages(images) {
            const gallery = document.getElementById('gallery');

            if (images.length === 0) {
                gallery.innerHTML = '<div class="loading">No images found</div>';
                return;
            }

            gallery.innerHTML = '';
            selectedImageCards.clear();

            images.forEach(img => {
                const card = document.createElement('div');
                card.className = 'image-card';
                card.style.cursor = 'pointer';
                card.dataset.path = img.path;
                card.dataset.name = img.name;
                card.dataset.tags = img.tags || '';

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

                // Left-click handler
                card.addEventListener('click', (e) => {
                    handleImageLeftClick(card);
                });

                // Right-click handler
                card.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    handleImageRightClick(card);
                });

                gallery.appendChild(card);
            });
        }

        function handleImageLeftClick(card) {
            if (isSelectionMode) {
                // In selection mode: toggle selection
                toggleCardSelection(card);
            } else {
                // Not in selection mode: open modal normally
                openImageModal(card.dataset.path, card.dataset.name, card.dataset.tags);
            }
        }

        function handleImageRightClick(card) {
            // Right-click is disabled in new design
            // Could be used for future features
        }

        function toggleCardSelection(card) {
            if (selectedImageCards.has(card)) {
                // Unselect
                selectedImageCards.delete(card);
                card.classList.remove('selected');
            } else {
                // Select
                selectedImageCards.add(card);
                card.classList.add('selected');
            }
            updateFloatingEditButton();
        }

        function clearImageSelections() {
            selectedImageCards.forEach(card => {
                card.classList.remove('selected');
            });
            selectedImageCards.clear();
            updateFloatingEditButton();
        }

        function toggleSelectionMode() {
            isSelectionMode = !isSelectionMode;
            const selectBtn = document.getElementById('selectBtn');

            if (isSelectionMode) {
                selectBtn.classList.add('active');
                showToast('Selection mode enabled', 'info');
            } else {
                selectBtn.classList.remove('active');
                // Clear selections when exiting selection mode
                clearImageSelections();
                showToast('Selection mode disabled', 'info');
            }
        }

        function updateFloatingEditButton() {
            const floatingBtn = document.getElementById('floatingEditBtn');
            const countBadge = document.getElementById('editBtnCount');

            if (selectedImageCards.size > 0) {
                floatingBtn.classList.add('visible');
                countBadge.textContent = selectedImageCards.size;
            } else {
                floatingBtn.classList.remove('visible');
            }
        }

        function refreshAll() {
            const folder = selectedFolder;
            const recursive = document.getElementById('recursiveToggle').checked;

            if (!folder) {
                alert('Please select a folder first');
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
                    const total = data.refreshed + data.skipped;
                    const toastMessage = `Refreshed updated files (${data.refreshed}/${total})`;
                    document.getElementById('statusText').textContent = data.message;
                    showToast(toastMessage, 'success');
                    // Reload images to show updated tags
                    loadImages();
                })
                .catch(err => {
                    console.error('Error refreshing:', err);
                    showToast('Error refreshing cache', 'error');
                });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Image Modal Functions
        let currentImagePath = '';
        let currentImageTags = new Set();
        let originalTagsString = '';
        let originalImageTags = new Set();
        let tagStates = new Map(); // For multi-edit: 'all', 'some', 'none'

        function openImageModal(path, name, tags) {
            isMultiEditMode = false;
            currentImagePath = path;
            originalTagsString = tags || '';

            // Parse current tags
            currentImageTags.clear();
            originalImageTags.clear();
            if (tags) {
                tags.split(',').map(t => t.trim().toLowerCase()).filter(t => t).forEach(tag => {
                    currentImageTags.add(tag);
                    originalImageTags.add(tag);
                });
            }

            // Set image source
            document.getElementById('modalImage').src = '/image?path=' + encodeURIComponent(path);
            document.getElementById('modalImage').alt = name;

            // Render tags
            renderModalTags();

            // Clear and focus input
            const input = document.getElementById('modalTagInput');
            input.value = '';

            // Show modal
            document.getElementById('imageModal').classList.add('active');

            // Focus on input after a short delay
            setTimeout(() => {
                input.focus();
            }, 100);
        }

        function openMultiEditModal() {
            if (selectedImageCards.size === 0) {
                showToast('No images selected', 'info');
                return;
            }

            isMultiEditMode = true;
            multiEditImages = Array.from(selectedImageCards).map(card => ({
                path: card.dataset.path,
                name: card.dataset.name,
                tags: card.dataset.tags || '',
                originalTags: new Set((card.dataset.tags || '').split(',').map(t => t.trim().toLowerCase()).filter(t => t)),
                currentTags: new Set((card.dataset.tags || '').split(',').map(t => t.trim().toLowerCase()).filter(t => t))
            }));

            // Calculate tag states (all/some/none)
            tagStates.clear();
            allTags.forEach(tag => {
                let count = 0;
                multiEditImages.forEach(img => {
                    if (img.currentTags.has(tag)) count++;
                });

                if (count === multiEditImages.length) {
                    tagStates.set(tag, 'all');
                } else if (count > 0) {
                    tagStates.set(tag, 'some');
                } else {
                    tagStates.set(tag, 'none');
                }
            });

            // Set modal image to first selected
            document.getElementById('modalImage').src = '/image?path=' + encodeURIComponent(multiEditImages[0].path);
            document.getElementById('modalImage').alt = `Multi-edit (${multiEditImages.length} images)`;

            // Render tags
            renderModalTags();

            // Clear and focus input
            const input = document.getElementById('modalTagInput');
            input.value = '';

            // Show modal
            document.getElementById('imageModal').classList.add('active');

            // Focus on input after a short delay
            setTimeout(() => {
                input.focus();
            }, 100);
        }

        function renderModalTags() {
            const container = document.getElementById('modalTagsContainer');
            container.innerHTML = '';

            if (allTags.size === 0) {
                container.classList.add('empty');
                container.innerHTML = '<span>No tags available</span>';
                return;
            }

            container.classList.remove('empty');

            // Sort all tags alphabetically
            const sortedTags = Array.from(allTags).sort();

            sortedTags.forEach(tag => {
                const btn = document.createElement('button');
                btn.className = 'modal-tag-button';
                btn.dataset.tag = tag;

                if (isMultiEditMode) {
                    // Multi-edit mode: show all/some/none states
                    const state = tagStates.get(tag) || 'none';
                    if (state === 'all') {
                        btn.classList.add('active');
                    } else if (state === 'some') {
                        btn.classList.add('partial');
                    }
                } else {
                    // Single edit mode: show active/inactive
                    const isActive = currentImageTags.has(tag);
                    if (isActive) {
                        btn.classList.add('active');
                    }
                }

                btn.textContent = tag;

                // Left-click to toggle
                btn.onclick = (e) => {
                    e.preventDefault();
                    toggleModalTag(tag, btn);
                    // Refocus input
                    document.getElementById('modalTagInput').focus();
                };

                // Right-click to reset
                btn.oncontextmenu = (e) => {
                    e.preventDefault();
                    resetModalTag(tag, btn);
                    // Refocus input
                    document.getElementById('modalTagInput').focus();
                };

                container.appendChild(btn);
            });
        }

        function toggleModalTag(tag, button) {
            if (isMultiEditMode) {
                // Multi-edit mode
                const currentState = tagStates.get(tag) || 'none';

                if (currentState === 'all') {
                    // Remove from all images
                    multiEditImages.forEach(img => img.currentTags.delete(tag));
                    tagStates.set(tag, 'none');
                    button.classList.remove('active');
                } else if (currentState === 'some') {
                    // Add to all images
                    multiEditImages.forEach(img => img.currentTags.add(tag));
                    tagStates.set(tag, 'all');
                    button.classList.remove('partial');
                    button.classList.add('active');
                } else {
                    // Add to all images
                    multiEditImages.forEach(img => img.currentTags.add(tag));
                    tagStates.set(tag, 'all');
                    button.classList.add('active');
                }
            } else {
                // Single edit mode
                if (currentImageTags.has(tag)) {
                    currentImageTags.delete(tag);
                    button.classList.remove('active');
                } else {
                    currentImageTags.add(tag);
                    button.classList.add('active');
                }
            }
        }

        function resetModalTag(tag, button) {
            if (isMultiEditMode) {
                // Multi-edit mode: reset to original state
                multiEditImages.forEach(img => {
                    if (img.originalTags.has(tag)) {
                        img.currentTags.add(tag);
                    } else {
                        img.currentTags.delete(tag);
                    }
                });

                // Recalculate state for this tag
                let count = 0;
                multiEditImages.forEach(img => {
                    if (img.currentTags.has(tag)) count++;
                });

                button.classList.remove('active', 'partial');

                if (count === multiEditImages.length) {
                    tagStates.set(tag, 'all');
                    button.classList.add('active');
                } else if (count > 0) {
                    tagStates.set(tag, 'some');
                    button.classList.add('partial');
                } else {
                    tagStates.set(tag, 'none');
                }
            } else {
                // Single edit mode: reset to original
                if (originalImageTags.has(tag)) {
                    currentImageTags.add(tag);
                    button.classList.add('active');
                } else {
                    currentImageTags.delete(tag);
                    button.classList.remove('active');
                }
            }
        }

        function addModalTag(tag) {
            tag = tag.trim().toLowerCase();
            if (tag) {
                if (isMultiEditMode) {
                    // Add to all images in multi-edit
                    multiEditImages.forEach(img => img.currentTags.add(tag));
                    tagStates.set(tag, 'all');
                } else {
                    // Add to current image tags
                    currentImageTags.add(tag);
                }

                // Add to all tags if new
                allTags.add(tag);

                // Re-render to show the new tag
                renderModalTags();
            }
        }

        function closeImageModal(saved = false) {
            document.getElementById('imageModal').classList.remove('active');
            currentImagePath = '';
            currentImageTags.clear();
            originalTagsString = '';

            // If we saved in multi-edit mode, clear selections and exit selection mode
            if (saved && isMultiEditMode) {
                clearImageSelections();
                if (isSelectionMode) {
                    isSelectionMode = false;
                    document.getElementById('selectBtn').classList.remove('active');
                }
            }

            if (saved) {
                showToast('Edited', 'success');
            } else {
                showToast('Cancelled', 'info');
            }
        }

        async function saveImageTags() {
            if (isMultiEditMode) {
                // Multi-edit mode: save all images
                let allSuccess = true;
                let savedCount = 0;

                for (const img of multiEditImages) {
                    const newTags = Array.from(img.currentTags).join(', ');
                    const originalTags = Array.from(img.originalTags).join(', ');

                    // Skip if no changes
                    if (newTags === originalTags) {
                        continue;
                    }

                    try {
                        const response = await fetch('/api/tags', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                path: img.path,
                                tags: newTags
                            })
                        });

                        const data = await response.json();

                        if (response.ok && data.success) {
                            savedCount++;
                        } else {
                            allSuccess = false;
                            console.error('Error saving tags for', img.path, data.error);
                        }
                    } catch (err) {
                        allSuccess = false;
                        console.error('Error saving tags for', img.path, err);
                    }
                }

                closeImageModal(savedCount > 0);

                if (savedCount > 0) {
                    // Reload images to show updated tags
                    loadImages();
                }

                if (!allSuccess) {
                    alert(`Some images failed to save. ${savedCount} of ${multiEditImages.length} saved successfully.`);
                }
            } else {
                // Single edit mode
                const newTags = Array.from(currentImageTags).join(', ');

                // Check if tags changed
                if (newTags === originalTagsString) {
                    closeImageModal(false);
                    return;
                }

                try {
                    const response = await fetch('/api/tags', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            path: currentImagePath,
                            tags: newTags
                        })
                    });

                    const data = await response.json();

                    if (response.ok && data.success) {
                        closeImageModal(true);
                        // Reload images to show updated tags
                        loadImages();
                    } else {
                        alert('Error saving tags: ' + (data.error || 'Unknown error'));
                    }
                } catch (err) {
                    console.error('Error saving tags:', err);
                    alert('Error saving tags: ' + err.message);
                }
            }
        }

        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type;

            // Show toast
            setTimeout(() => {
                toast.classList.add('show');
            }, 10);

            // Hide toast after 2 seconds
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2000);
        }

        // Modal input handlers
        const modalInput = document.getElementById('modalTagInput');

        modalInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const value = this.value.trim();
                if (value) {
                    // Add tag
                    addModalTag(value);
                    this.value = '';
                } else {
                    // Empty input, save and close
                    saveImageTags();
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                closeImageModal(false);
            }
        });

        // Prevent clicks on modal content from bubbling
        document.querySelector('.image-modal-content').addEventListener('click', function(e) {
            e.stopPropagation();
            // Refocus input if it's not already focused
            if (document.activeElement !== modalInput) {
                modalInput.focus();
            }
        });

        // Close modal when clicking outside
        document.getElementById('imageModal').addEventListener('click', function(e) {
            if (e.target.id === 'imageModal') {
                closeImageModal(false);
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

@app.route('/api/tags', method='POST')
def api_update_tags():
    """Update tags for an image"""
    response.content_type = 'application/json'

    try:
        # Get JSON data from request body
        data = request.json
        if not data:
            response.status = 400
            return json.dumps({'error': 'No data provided'})

        image_path = data.get('path', '')
        new_tags = data.get('tags', '')

        if not image_path:
            response.status = 400
            return json.dumps({'error': 'No image path specified'})

        if not os.path.exists(image_path):
            response.status = 404
            return json.dumps({'error': 'Image not found'})

        # Security check: ensure the path is within BASE_PATH
        real_path = os.path.realpath(image_path)
        real_base = os.path.realpath(BASE_PATH)

        if not real_path.startswith(real_base):
            response.status = 403
            return json.dumps({'error': 'Access denied'})

        # Write tags using metadata module
        from core.metadata import write_tag_metadata

        if write_tag_metadata(image_path, new_tags):
            # Update cache with new tags
            cache_manager.update_cache(image_path, new_tags)
            cache_manager.save_cache()

            return json.dumps({'success': True, 'message': 'Tags updated successfully'})
        else:
            response.status = 500
            return json.dumps({'error': 'Failed to write tags'})

    except Exception as e:
        response.status = 500
        return json.dumps({'error': str(e)})

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
