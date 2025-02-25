import os
import requests
from pathlib import Path
import logging
from flask import current_app

logger = logging.getLogger(__name__)

STATIC_FILES = {
    'js/bootstrap.bundle.min.js': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
    'css/bootstrap.min.css': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'css/bootstrap.min.css.map': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css.map'
}

def check_static_files():
    """Check if all required static files exist."""
    static_files = [
        # CSS
        'css/style.css',
        'css/admin.css',
        'css/administration.css',
        
        # Core JS
        'js/error-handler.js',
        'js/csrf.js',
        'js/main.js',
        
        # Admin JS
        'js/admin/config.js',
        'js/admin/modules.js',
        'js/admin/forms.js',
        'js/admin/modals.js',
        'js/admin/datatables.js',
        'js/admin/sidebar.js',
        'js/admin/worklogs.js'
    ]
    
    missing_files = []
    for file in static_files:
        full_path = os.path.join(current_app.static_folder, file)
        if not os.path.exists(full_path):
            missing_files.append(file)
            
    if missing_files:
        logger.error(f"Missing static files: {missing_files}")
        raise RuntimeError(f"Missing static files: {missing_files}")

def ensure_static_files(app):
    """Ensure all required static files exist."""
    static_dir = Path(app.static_folder)
    
    for file_path, url in STATIC_FILES.items():
        full_path = static_dir / file_path
        
        # Create directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not full_path.exists():
            try:
                logger.info(f"Downloading {file_path} from {url}")
                response = requests.get(url)
                response.raise_for_status()
                
                with open(full_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Successfully downloaded {file_path}")
                
            except Exception as e:
                logger.error(f"Error downloading {file_path}: {e}") 