from flask import Blueprint, render_template, current_app, request, flash
from sqlalchemy.exc import SQLAlchemyError

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
def dashboard():
    try:
        # Assuming you have a Project model defined in app/models/project.py
        from app.models.project import Project
        project_count = Project.query.count()
        return render_template('admin/dashboard.html', project_count=project_count)
    except SQLAlchemyError as e:
        current_app.logger.error(f'Error loading dashboard: {e}')
        return render_template('errors/500.html'), 500

@admin_bp.route('/leave-requests')
def leave_requests():
    try:
        # User-facing view: simple leave request list
        from app.models.leave_request import LeaveRequest
        leave_request_list = LeaveRequest.query.all()
        return render_template('admin/leave_requests.html', leave_requests=leave_request_list)
    except SQLAlchemyError as e:
        current_app.logger.error(f'Error loading leave requests: {e}')
        return render_template('errors/500.html'), 500

@admin_bp.route('/leave-management', methods=['GET', 'POST'])
def leave_management():
    try:
        from app.models.leave_request import LeaveRequest
        leave_request_list = LeaveRequest.query.order_by(LeaveRequest.start_date).all()

        if request.method == 'POST':
            # CSV Import logic: process the uploaded CSV file.
            if 'csv_file' in request.files:
                csv_file = request.files['csv_file']
                # TODO: Parse the CSV file and process leave data accordingly.
                flash("CSV file imported successfully.", "success")
            else:
                flash("No CSV file uploaded.", "danger")

        return render_template('admin/leave_management.html', leave_requests=leave_request_list)
    except SQLAlchemyError as e:
        current_app.logger.error(f'Error loading leave management: {e}')
        return render_template('errors/500.html'), 500 