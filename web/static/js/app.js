// GalleryTags Web UI - Main Application Logic

// Global State
let currentFolder = null;
let allImages = [];
let selectedImages = new Set();
let isDragging = false;
let dragStartIndex = null;
let currentImageForEdit = null;

// API Base URL
const API_BASE = '';

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadDefaultFolder();
});

// Initialize all event listeners
function initializeEventListeners() {
    // Toolbar buttons
    document.getElementById('openFolderBtn').addEventListener('click', showFolderModal);
    document.getElementById('selectAllBtn').addEventListener('click', toggleSelectAll);
    document.getElementById('refreshBtn').addEventListener('click', () => refreshImages(false));
    document.getElementById('rescanBtn').addEventListener('click', () => refreshImages(true));
    document.getElementById('exportBtn').addEventListener('click', showExportModal);
    document.getElementById('statsBtn').addEventListener('click', showStatsModal);

    // Search controls
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    document.getElementById('searchMode').addEventListener('change', applyFilters);
    document.getElementById('clearSearchBtn').addEventListener('click', clearSearch);

    // Sort control
    document.getElementById('sortBy').addEventListener('change', applySorting);

    // Batch tag editor
    document.getElementById('applyTagsBtn').addEventListener('click', applyBatchTags);
    document.getElementById('cancelBatchBtn').addEventListener('click', cancelBatchEdit);
    document.getElementById('batchTagInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyBatchTags();
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // Click outside gallery to deselect
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('gallery-container')) {
            clearSelection();
        }
    });
}

// Keyboard shortcuts
function handleKeyboardShortcuts(e) {
    // Ctrl+O: Open folder
    if (e.ctrlKey && e.key === 'o') {
        e.preventDefault();
        showFolderModal();
    }
    // Ctrl+A: Select all
    else if (e.ctrlKey && e.key === 'a') {
        e.preventDefault();
        toggleSelectAll();
    }
    // Ctrl+F: Focus search
    else if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        document.getElementById('searchInput').focus();
    }
    // Ctrl+R: Refresh
    else if (e.ctrlKey && e.key === 'r' && !e.shiftKey) {
        e.preventDefault();
        refreshImages(false);
    }
    // Ctrl+Shift+R: Rescan
    else if (e.ctrlKey && e.shiftKey && e.key === 'R') {
        e.preventDefault();
        refreshImages(true);
    }
    // Ctrl+E: Export
    else if (e.ctrlKey && e.key === 'e') {
        e.preventDefault();
        showExportModal();
    }
    // Escape: Clear selection or close modals
    else if (e.key === 'Escape') {
        if (document.querySelector('.modal[style*="display: block"]')) {
            closeAllModals();
        } else {
            clearSelection();
        }
    }
    // Enter: Edit tags for selected images
    else if (e.key === 'Enter' && selectedImages.size > 0 && !e.target.closest('.modal')) {
        e.preventDefault();
        showBatchTagEditor();
    }
}

// Load default folder from config
async function loadDefaultFolder() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);
        const config = await response.json();

        if (config.default_folder && config.default_folder.trim() !== '') {
            await openFolderByPath(config.default_folder);
        }
    } catch (error) {
        console.error('Error loading default folder:', error);
    }
}

// Show folder selection modal
function showFolderModal() {
    document.getElementById('folderModal').style.display = 'flex';
    document.getElementById('folderPathInput').focus();

    // Enter key in folder input
    document.getElementById('folderPathInput').onkeypress = (e) => {
        if (e.key === 'Enter') {
            openFolder();
        }
    };
}

// Close folder modal
function closeFolderModal() {
    document.getElementById('folderModal').style.display = 'none';
}

// Open folder
async function openFolder() {
    const folderPath = document.getElementById('folderPathInput').value.trim();

    if (!folderPath) {
        alert('Please enter a folder path');
        return;
    }

    closeFolderModal();
    await openFolderByPath(folderPath);
}

// Open folder by path
async function openFolderByPath(folderPath) {
    showLoading('Opening folder...');

    try {
        const response = await fetch(`${API_BASE}/api/folder/open`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: folderPath })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to open folder');
        }

        const data = await response.json();
        currentFolder = data.folder;
        document.getElementById('currentFolder').textContent = currentFolder;

        // Load images with metadata
        await loadImages();
    } catch (error) {
        hideLoading();
        alert(`Error opening folder: ${error.message}`);
    }
}

// Load images with metadata
async function loadImages(forceRefresh = false) {
    if (!currentFolder) return;

    showLoading('Loading images...');

    try {
        const response = await fetch(`${API_BASE}/api/images/list`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force_refresh: forceRefresh })
        });

        if (!response.ok) {
            throw new Error('Failed to load images');
        }

        const data = await response.json();
        allImages = data.images;

        renderGallery();
        updateImageCount();
        hideLoading();
    } catch (error) {
        hideLoading();
        alert(`Error loading images: ${error.message}`);
    }
}

// Render gallery grid
function renderGallery() {
    const grid = document.getElementById('galleryGrid');

    if (allImages.length === 0) {
        grid.innerHTML = '<div class="empty-state"><p>📂 No images found in this folder</p></div>';
        return;
    }

    grid.innerHTML = '';

    allImages.forEach((image, index) => {
        const cell = createImageCell(image, index);
        grid.appendChild(cell);
    });

    applySorting();
    applyFilters();
}

// Create image cell element
function createImageCell(image, index) {
    const cell = document.createElement('div');
    cell.className = 'image-cell';
    cell.dataset.index = index;
    cell.dataset.path = image.path;

    // Thumbnail URL
    const thumbnailUrl = `${API_BASE}/api/image/thumbnail/${encodeURIComponent(image.path)}?size=300`;

    // Tags display
    const tagsHtml = image.tags
        ? image.tags.split(',').map(tag => `<span class="tag">${tag.trim()}</span>`).join('')
        : '<span style="color: #999;">No tags</span>';

    cell.innerHTML = `
        <div class="selection-indicator">✓</div>
        <div class="image-wrapper">
            <img src="${thumbnailUrl}" alt="${image.name}" loading="lazy">
        </div>
        <div class="image-info">
            <div class="image-name" title="${image.name}">${image.name}</div>
            <div class="image-tags">${tagsHtml}</div>
        </div>
    `;

    // Event listeners
    cell.addEventListener('click', (e) => handleCellClick(e, index));
    cell.addEventListener('dblclick', () => showImageDetails(image));
    cell.addEventListener('mousedown', (e) => handleDragStart(e, index));
    cell.addEventListener('mouseenter', (e) => handleDragEnter(e, index));
    cell.addEventListener('mouseup', handleDragEnd);

    return cell;
}

// Handle cell click (selection)
function handleCellClick(e, index) {
    e.stopPropagation();

    if (e.ctrlKey || e.metaKey) {
        // Toggle selection
        toggleImageSelection(index);
    } else if (e.shiftKey && selectedImages.size > 0) {
        // Range selection
        const lastSelected = Math.max(...Array.from(selectedImages));
        const start = Math.min(lastSelected, index);
        const end = Math.max(lastSelected, index);

        for (let i = start; i <= end; i++) {
            addImageSelection(i);
        }
    } else {
        // Single selection
        clearSelection();
        addImageSelection(index);
    }

    updateBatchTagEditor();
}

// Handle drag selection start
function handleDragStart(e, index) {
    if (e.button !== 0) return; // Only left click

    isDragging = true;
    dragStartIndex = index;

    if (!e.ctrlKey && !e.metaKey && !e.shiftKey) {
        clearSelection();
    }

    addImageSelection(index);
    updateBatchTagEditor();
}

// Handle drag enter
function handleDragEnter(e, index) {
    if (!isDragging) return;

    const start = Math.min(dragStartIndex, index);
    const end = Math.max(dragStartIndex, index);

    // Clear previous drag selection
    if (!e.ctrlKey) {
        clearSelection();
    }

    // Select range
    for (let i = start; i <= end; i++) {
        addImageSelection(i);
    }

    updateBatchTagEditor();
}

// Handle drag end
function handleDragEnd() {
    isDragging = false;
    dragStartIndex = null;
}

// Add mouseup listener to document
document.addEventListener('mouseup', handleDragEnd);

// Toggle image selection
function toggleImageSelection(index) {
    if (selectedImages.has(index)) {
        removeImageSelection(index);
    } else {
        addImageSelection(index);
    }
}

// Add image to selection
function addImageSelection(index) {
    selectedImages.add(index);
    const cell = document.querySelector(`.image-cell[data-index="${index}"]`);
    if (cell) cell.classList.add('selected');
    updateSelectedCount();
}

// Remove image from selection
function removeImageSelection(index) {
    selectedImages.delete(index);
    const cell = document.querySelector(`.image-cell[data-index="${index}"]`);
    if (cell) cell.classList.remove('selected');
    updateSelectedCount();
}

// Clear all selections
function clearSelection() {
    selectedImages.forEach(index => {
        const cell = document.querySelector(`.image-cell[data-index="${index}"]`);
        if (cell) cell.classList.remove('selected');
    });
    selectedImages.clear();
    updateSelectedCount();
    hideBatchTagEditor();
}

// Toggle select all
function toggleSelectAll() {
    if (selectedImages.size === allImages.length) {
        clearSelection();
    } else {
        allImages.forEach((_, index) => addImageSelection(index));
        updateBatchTagEditor();
    }
}

// Update image count display
function updateImageCount() {
    const visibleImages = document.querySelectorAll('.image-cell:not(.hidden)').length;
    document.getElementById('imageCount').textContent = `${visibleImages} image${visibleImages !== 1 ? 's' : ''}`;
}

// Update selected count display
function updateSelectedCount() {
    const count = selectedImages.size;
    const elem = document.getElementById('selectedCount');
    elem.textContent = `${count} selected`;
    elem.style.display = count > 0 ? 'inline-block' : 'none';
}

// Show batch tag editor
function showBatchTagEditor() {
    if (selectedImages.size === 0) return;

    const editor = document.getElementById('batchTagEditor');
    editor.style.display = 'block';
    document.getElementById('batchTagInput').focus();
}

// Hide batch tag editor
function hideBatchTagEditor() {
    document.getElementById('batchTagEditor').style.display = 'none';
    document.getElementById('batchTagInput').value = '';
}

// Update batch tag editor visibility
function updateBatchTagEditor() {
    if (selectedImages.size > 0) {
        showBatchTagEditor();
    } else {
        hideBatchTagEditor();
    }
}

// Apply batch tags
async function applyBatchTags() {
    const tagsInput = document.getElementById('batchTagInput').value.trim();

    if (!tagsInput) {
        alert('Please enter tags');
        return;
    }

    const imagePaths = Array.from(selectedImages).map(index => allImages[index].path);

    showLoading('Applying tags...');

    try {
        const response = await fetch(`${API_BASE}/api/image/tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                images: imagePaths,
                tags: tagsInput
            })
        });

        if (!response.ok) {
            throw new Error('Failed to apply tags');
        }

        const data = await response.json();

        // Update local image data
        data.results.forEach(result => {
            if (result.success) {
                const image = allImages.find(img => img.path === result.path);
                if (image) {
                    image.tags = result.tags;
                }
            }
        });

        // Re-render gallery
        renderGallery();
        hideBatchTagEditor();
        clearSelection();
        hideLoading();
    } catch (error) {
        hideLoading();
        alert(`Error applying tags: ${error.message}`);
    }
}

// Cancel batch edit
function cancelBatchEdit() {
    hideBatchTagEditor();
    clearSelection();
}

// Show image details modal
function showImageDetails(image) {
    currentImageForEdit = image;

    document.getElementById('imageModalTitle').textContent = image.name;
    document.getElementById('imageFileName').textContent = image.name;
    document.getElementById('imageFilePath').textContent = image.path;
    document.getElementById('imageFileSize').textContent = formatFileSize(image.size);
    document.getElementById('imageFileModified').textContent = new Date(image.modified * 1000).toLocaleString();
    document.getElementById('imageTagsInput').value = image.tags || '';

    // Set preview image
    const fullImageUrl = `${API_BASE}/api/image/full/${encodeURIComponent(image.path)}`;
    document.getElementById('imageModalPreview').src = fullImageUrl;

    document.getElementById('imageModal').style.display = 'flex';
}

// Close image details modal
function closeImageModal() {
    document.getElementById('imageModal').style.display = 'none';
    currentImageForEdit = null;
}

// Save image tags
async function saveImageTags() {
    if (!currentImageForEdit) return;

    const tagsInput = document.getElementById('imageTagsInput').value.trim();

    showLoading('Saving tags...');

    try {
        const response = await fetch(`${API_BASE}/api/image/tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                images: [currentImageForEdit.path],
                tags: tagsInput
            })
        });

        if (!response.ok) {
            throw new Error('Failed to save tags');
        }

        const data = await response.json();

        if (data.results[0].success) {
            currentImageForEdit.tags = data.results[0].tags;
            renderGallery();
            closeImageModal();
        } else {
            throw new Error(data.results[0].error);
        }

        hideLoading();
    } catch (error) {
        hideLoading();
        alert(`Error saving tags: ${error.message}`);
    }
}

// Apply search filters
function applyFilters() {
    const searchInput = document.getElementById('searchInput').value.trim().toLowerCase();
    const searchMode = document.getElementById('searchMode').value;

    if (!searchInput) {
        // Show all images
        document.querySelectorAll('.image-cell').forEach(cell => {
            cell.classList.remove('hidden');
        });
        updateImageCount();
        return;
    }

    const searchTags = searchInput.split(',').map(tag => tag.trim()).filter(tag => tag);

    document.querySelectorAll('.image-cell').forEach(cell => {
        const index = parseInt(cell.dataset.index);
        const image = allImages[index];
        const imageTags = (image.tags || '').toLowerCase().split(',').map(tag => tag.trim());

        let matches = false;

        if (searchMode === 'AND') {
            // All search tags must be present
            matches = searchTags.every(searchTag =>
                imageTags.some(imageTag => imageTag.includes(searchTag))
            );
        } else {
            // Any search tag must be present
            matches = searchTags.some(searchTag =>
                imageTags.some(imageTag => imageTag.includes(searchTag))
            );
        }

        if (matches) {
            cell.classList.remove('hidden');
        } else {
            cell.classList.add('hidden');
        }
    });

    updateImageCount();
}

// Clear search
function clearSearch() {
    document.getElementById('searchInput').value = '';
    applyFilters();
}

// Apply sorting
function applySorting() {
    const sortBy = document.getElementById('sortBy').value;
    const grid = document.getElementById('galleryGrid');
    const cells = Array.from(grid.querySelectorAll('.image-cell'));

    cells.sort((a, b) => {
        const indexA = parseInt(a.dataset.index);
        const indexB = parseInt(b.dataset.index);
        const imageA = allImages[indexA];
        const imageB = allImages[indexB];

        switch (sortBy) {
            case 'name-asc':
                return imageA.name.localeCompare(imageB.name);
            case 'name-desc':
                return imageB.name.localeCompare(imageA.name);
            case 'date-asc':
                return imageA.modified - imageB.modified;
            case 'date-desc':
                return imageB.modified - imageA.modified;
            case 'tags-asc':
                return (imageA.tags || '').localeCompare(imageB.tags || '');
            case 'tags-desc':
                return (imageB.tags || '').localeCompare(imageA.tags || '');
            default:
                return 0;
        }
    });

    // Re-append cells in sorted order
    cells.forEach(cell => grid.appendChild(cell));
}

// Refresh images
async function refreshImages(fullRescan = false) {
    if (!currentFolder) {
        alert('No folder opened');
        return;
    }

    showLoading(fullRescan ? 'Rescanning all images...' : 'Refreshing...');

    try {
        // Refresh cache
        await fetch(`${API_BASE}/api/cache/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_rescan: fullRescan })
        });

        // Reload images
        await loadImages(fullRescan);
    } catch (error) {
        hideLoading();
        alert(`Error refreshing: ${error.message}`);
    }
}

// Show export modal
async function showExportModal() {
    if (!currentFolder) {
        alert('No folder opened');
        return;
    }

    showLoading('Loading export config...');

    try {
        const response = await fetch(`${API_BASE}/api/export/config`);
        const data = await response.json();

        const exportConfig = data.config || {};
        renderExportConfig(exportConfig);

        hideLoading();
        document.getElementById('exportModal').style.display = 'flex';
    } catch (error) {
        hideLoading();
        alert(`Error loading export config: ${error.message}`);
    }
}

// Close export modal
function closeExportModal() {
    document.getElementById('exportModal').style.display = 'none';
}

// Render export config
function renderExportConfig(config) {
    const container = document.getElementById('exportConfigList');
    container.innerHTML = '';

    Object.entries(config).forEach(([outputPath, tagQuery]) => {
        const rule = createExportRule(outputPath, tagQuery);
        container.appendChild(rule);
    });

    if (Object.keys(config).length === 0) {
        addExportRule();
    }
}

// Create export rule element
function createExportRule(outputPath = '', tagQuery = '') {
    const rule = document.createElement('div');
    rule.className = 'export-rule';

    rule.innerHTML = `
        <input type="text" placeholder="Output path (e.g., gallery.md)" value="${outputPath}" class="export-output">
        <input type="text" placeholder="Tag query (e.g., portrait, character)" value="${tagQuery}" class="export-query">
        <button onclick="removeExportRule(this)">✕</button>
    `;

    return rule;
}

// Add export rule
function addExportRule() {
    const container = document.getElementById('exportConfigList');
    const rule = createExportRule();
    container.appendChild(rule);
}

// Remove export rule
function removeExportRule(button) {
    button.parentElement.remove();
}

// Save export config
async function saveExportConfig() {
    const rules = document.querySelectorAll('.export-rule');
    const config = {};

    rules.forEach(rule => {
        const outputPath = rule.querySelector('.export-output').value.trim();
        const tagQuery = rule.querySelector('.export-query').value.trim();

        if (outputPath && tagQuery) {
            config[outputPath] = tagQuery;
        }
    });

    showLoading('Saving export config...');

    try {
        const response = await fetch(`${API_BASE}/api/export/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config })
        });

        if (!response.ok) {
            throw new Error('Failed to save export config');
        }

        hideLoading();
        alert('Export configuration saved!');
    } catch (error) {
        hideLoading();
        alert(`Error saving config: ${error.message}`);
    }
}

// Save and export
async function saveAndExport() {
    await saveExportConfig();

    showLoading('Running export...');

    try {
        const response = await fetch(`${API_BASE}/api/export/run`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Export failed');
        }

        hideLoading();
        closeExportModal();
        alert('Export completed successfully!');
    } catch (error) {
        hideLoading();
        alert(`Error running export: ${error.message}`);
    }
}

// Show stats modal
async function showStatsModal() {
    if (!currentFolder) {
        alert('No folder opened');
        return;
    }

    showLoading('Loading statistics...');

    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        const data = await response.json();

        document.getElementById('statTotalImages').textContent = data.total_images;
        document.getElementById('statTotalSize').textContent = formatFileSize(data.total_size);
        document.getElementById('statUniqueTags').textContent = data.unique_tags;

        // Render tags cloud
        const tagsCloud = document.getElementById('tagsCloud');
        tagsCloud.innerHTML = '';

        data.all_tags.forEach(tag => {
            const tagElem = document.createElement('span');
            tagElem.className = 'tag';
            tagElem.textContent = tag;
            tagElem.onclick = () => {
                document.getElementById('searchInput').value = tag;
                applyFilters();
                closeStatsModal();
            };
            tagsCloud.appendChild(tagElem);
        });

        hideLoading();
        document.getElementById('statsModal').style.display = 'flex';
    } catch (error) {
        hideLoading();
        alert(`Error loading stats: ${error.message}`);
    }
}

// Close stats modal
function closeStatsModal() {
    document.getElementById('statsModal').style.display = 'none';
}

// Close all modals
function closeAllModals() {
    closeFolderModal();
    closeImageModal();
    closeExportModal();
    closeStatsModal();
}

// Show loading overlay
function showLoading(message = 'Loading...') {
    document.getElementById('loadingText').textContent = message;
    document.getElementById('loadingOverlay').style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Utility: Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}
