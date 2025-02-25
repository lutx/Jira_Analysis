from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.services.availability_service import get_user_availability, calculate_working_days
from datetime import datetime

availability_bp = Blueprint('availability', __name__, url_prefix='/availability')

@availability_bp.route('/')
@login_required
def index():
    """User availability overview."""
    month_year = request.args.get('month_year', datetime.now().strftime('%Y-%m'))
    availability = get_user_availability(current_user.id, month_year)
    return render_template('availability/index.html', availability=availability) 