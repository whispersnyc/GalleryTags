@echo off
REM GalleryTags Web UI Launcher for Windows

echo Starting GalleryTags Web UI...
echo ================================
echo.
echo Open your browser to: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python web_app.py %*
