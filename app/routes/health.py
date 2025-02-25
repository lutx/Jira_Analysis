from flask import Blueprint, jsonify
from app.extensions import db
import psutil
import os

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """Basic health check endpoint"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    # System metrics
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return jsonify({
        'status': 'ok',
        'database': db_status,
        'memory': {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent
        },
        'disk': {
            'total': disk.total,
            'free': disk.free,
            'percent': disk.percent
        },
        'cpu_percent': psutil.cpu_percent()
    }) 