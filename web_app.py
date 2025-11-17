#!/usr/bin/env python3
"""
GalleryTags Web UI - Flask Backend
Provides REST API for image tagging, search, and export functionality
"""

import os
import json
import mimetypes
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory, render_template
from flask_cors import CORS
from PIL import Image
import io

# Import existing core modules
from core.metadata import read_tag_metadata, write_tag_metadata, get_short_path_name
from core.cache import CacheManager
from utils.helpers import natural_sort_key, parse_tags, get_config

# Wrapper functions for compatibility
def get_tags(image_path):
    """Get tags from image metadata"""
    short_path = get_short_path_name(image_path)
    return read_tag_metadata(image_path, short_path)

def set_tags(image_path, tags):
    """Set tags to image metadata"""
    short_path = get_short_path_name(image_path)
    tag_text = ', '.join(sorted(tags)) if isinstance(tags, (set, list)) else tags
    return write_tag_metadata(image_path, tag_text, short_path)

app = Flask(__name__,
            static_folder='web/static',
            template_folder='web/templates')
CORS(app)

# Global state
current_folder = None
cache_manager = None
config = get_config()

@app.route('/')
def index():
    """Serve the main web UI"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_app_config():
    """Get application configuration"""
    return jsonify({
        'default_folder': config['APP_CONFIG'].get('default_folder', ''),
        'export_config': config['EXPORT_CONFIG'],
        'format_config': config['FORMAT_CONFIG']
    })

@app.route('/api/folder/open', methods=['POST'])
def open_folder():
    """Open a folder and load images"""
    global current_folder, cache_manager

    data = request.json
    folder_path = data.get('path', '')

    if not folder_path or not os.path.isdir(folder_path):
        return jsonify({'error': 'Invalid folder path'}), 400

    current_folder = folder_path
    cache_manager = CacheManager()

    # Get all supported image files
    supported_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    images = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_extensions:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, folder_path)
                images.append({
                    'path': rel_path,
                    'full_path': full_path,
                    'name': file
                })

    # Sort naturally
    images.sort(key=lambda x: natural_sort_key(x['name']))

    return jsonify({
        'folder': folder_path,
        'images': images,
        'count': len(images)
    })

@app.route('/api/folder/current', methods=['GET'])
def get_current_folder():
    """Get currently opened folder"""
    if current_folder:
        return jsonify({'folder': current_folder})
    return jsonify({'folder': None})

@app.route('/api/images/list', methods=['POST'])
def list_images():
    """List all images in current folder with metadata"""
    global cache_manager

    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    data = request.json or {}
    force_refresh = data.get('force_refresh', False)

    supported_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    images = []

    for root, dirs, files in os.walk(current_folder):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_extensions:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, current_folder)

                # Get tags from cache or metadata
                tags = None
                if cache_manager and not force_refresh:
                    tags = cache_manager.get_cached_metadata(full_path)

                if tags is None:
                    tags = get_tags(full_path)
                    if cache_manager:
                        cache_manager.update_cache(full_path, tags)

                stat = os.stat(full_path)
                images.append({
                    'path': rel_path,
                    'full_path': full_path,
                    'name': file,
                    'tags': tags,
                    'modified': stat.st_mtime,
                    'size': stat.st_size
                })

    # Save cache
    if cache_manager:
        cache_manager.save_cache()

    return jsonify({'images': images})

@app.route('/api/image/thumbnail/<path:image_path>')
def get_thumbnail(image_path):
    """Generate and serve image thumbnail"""
    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    full_path = os.path.join(current_folder, image_path)

    if not os.path.exists(full_path):
        return jsonify({'error': 'Image not found'}), 404

    # Generate thumbnail
    try:
        size = int(request.args.get('size', 300))
        img = Image.open(full_path)
        img.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Convert to bytes
        img_io = io.BytesIO()
        img_format = img.format or 'JPEG'
        img.save(img_io, img_format, quality=85)
        img_io.seek(0)

        mimetype = mimetypes.guess_type(full_path)[0] or 'image/jpeg'
        return send_file(img_io, mimetype=mimetype)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/full/<path:image_path>')
def get_full_image(image_path):
    """Serve full resolution image"""
    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    full_path = os.path.join(current_folder, image_path)

    if not os.path.exists(full_path):
        return jsonify({'error': 'Image not found'}), 404

    return send_file(full_path)

@app.route('/api/image/tags', methods=['GET'])
def get_image_tags():
    """Get tags for a specific image"""
    image_path = request.args.get('path')

    if not image_path:
        return jsonify({'error': 'No path provided'}), 400

    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    full_path = os.path.join(current_folder, image_path)

    if not os.path.exists(full_path):
        return jsonify({'error': 'Image not found'}), 404

    tags = get_tags(full_path)
    return jsonify({'path': image_path, 'tags': tags})

@app.route('/api/image/tags', methods=['POST'])
def update_image_tags():
    """Update tags for one or more images"""
    global cache_manager

    data = request.json
    images = data.get('images', [])
    tags_input = data.get('tags', '')

    if not images:
        return jsonify({'error': 'No images specified'}), 400

    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    # Tags can be a string or already parsed
    if isinstance(tags_input, str):
        tag_text = tags_input
    else:
        tag_text = ', '.join(sorted(tags_input))

    results = []
    for image_path in images:
        full_path = os.path.join(current_folder, image_path)

        if not os.path.exists(full_path):
            results.append({
                'path': image_path,
                'success': False,
                'error': 'File not found'
            })
            continue

        try:
            success = set_tags(full_path, tag_text)

            if success:
                # Update cache
                if cache_manager:
                    cache_manager.update_cache(full_path, tag_text)

                results.append({
                    'path': image_path,
                    'success': True,
                    'tags': tag_text
                })
            else:
                results.append({
                    'path': image_path,
                    'success': False,
                    'error': 'Failed to write tags'
                })
        except Exception as e:
            results.append({
                'path': image_path,
                'success': False,
                'error': str(e)
            })

    # Save cache
    if cache_manager:
        cache_manager.save_cache()

    return jsonify({'results': results})

@app.route('/api/cache/refresh', methods=['POST'])
def refresh_cache():
    """Refresh cache for all images"""
    global cache_manager

    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    data = request.json or {}
    full_rescan = data.get('full_rescan', False)

    if not cache_manager:
        cache_manager = CacheManager()

    if full_rescan:
        # Force refresh all
        cache_manager.cache_data = {}

    # Quick refresh - only update modified files
    supported_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    updated = 0

    for root, dirs, files in os.walk(current_folder):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_extensions:
                full_path = os.path.join(root, file)

                # Check if needs update
                cached = cache_manager.get_cached_metadata(full_path)
                if full_rescan or cached is None:
                    tags = get_tags(full_path)
                    cache_manager.update_cache(full_path, tags)
                    updated += 1

    cache_manager.save_cache()

    return jsonify({
        'success': True,
        'updated': updated,
        'total': len(cache_manager.cache_data)
    })

@app.route('/api/export/config', methods=['GET'])
def get_export_config():
    """Get export configuration for current folder"""
    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    config_path = os.path.join(current_folder, '.gallery_export.json')

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                export_config = json.load(f)
            return jsonify({'config': export_config})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'config': {}})

@app.route('/api/export/config', methods=['POST'])
def save_export_config():
    """Save export configuration"""
    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    data = request.json
    export_config = data.get('config', {})

    config_path = os.path.join(current_folder, '.gallery_export.json')

    try:
        with open(config_path, 'w') as f:
            json.dump(export_config, f, indent=2)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/run', methods=['POST'])
def run_export():
    """Run export process"""
    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    try:
        # Check if export config exists
        config_path = os.path.join(current_folder, '.gallery_export.json')
        if not os.path.exists(config_path):
            return jsonify({'error': 'No export configuration found'}), 400

        # Import the function
        from core.metadata import process_exports_headless

        # Use existing headless export functionality
        success = process_exports_headless(current_folder, config_path)

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Export failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about current folder"""
    if not current_folder:
        return jsonify({'error': 'No folder opened'}), 400

    supported_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    total_images = 0
    total_size = 0
    all_tags = set()

    for root, dirs, files in os.walk(current_folder):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_extensions:
                full_path = os.path.join(root, file)
                total_images += 1
                total_size += os.path.getsize(full_path)

                # Get tags
                tags = get_tags(full_path)
                all_tags.update(parse_tags(tags))

    return jsonify({
        'total_images': total_images,
        'total_size': total_size,
        'unique_tags': len(all_tags),
        'all_tags': sorted(list(all_tags))
    })

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='GalleryTags Web UI')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    print(f"Starting GalleryTags Web UI on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")

    app.run(host=args.host, port=args.port, debug=args.debug)
