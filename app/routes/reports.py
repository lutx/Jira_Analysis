from flask import Blueprint, jsonify, request, send_file, current_app, render_template, g
from app.utils.decorators import auth_required
from app.services.jira_service import get_jira_service
from datetime import datetime, timedelta
import io
from app.extensions import cache
from app.services.report_service import ReportService, generate_report, analyze_role_distribution, analyze_shadow_work, get_workload_report
import csv
from flask_wtf import FlaskForm
import logging
from flask_login import login_required, current_user
from app.decorators import admin_required
from app.models import Project, Report, ReportResult
from app.forms.report_forms import (
    RoleDistributionForm, 
    ShadowWorkForm, 
    AvailabilityForm
)
from app.models.portfolio import Portfolio
from app.models.team import Team
from app.extensions import db
from app.utils.auth import requires_auth, requires_admin
from typing import Dict

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')
logger = logging.getLogger(__name__)

def generate_report_data(start_date, end_date, report_type):
    # Tutaj implementacja logiki generowania danych raportu
    return {
        'start_date': start_date,
        'end_date': end_date,
        'type': report_type,
        'data': []  # Tu dodaj rzeczywiste dane
    }

def create_pdf_report(report_data):
    # Tutaj implementacja generowania PDF
    # To jest przykład - należy zaimplementować rzeczywistą logikę
    return b"Sample PDF content"

@reports_bp.route('/')
@login_required
def index():
    """Lista dostępnych raportów."""
    reports = Report.query.filter_by(is_active=True).all()
    return render_template('reports/index.html', reports=reports)

@reports_bp.route('/workload')
@login_required
def workload():
    """Raport obciążenia pracowników."""
    return render_template('reports/workload.html')

@reports_bp.route('/role-distribution')
@auth_required(['admin'])
def role_distribution():
    """Show role distribution report."""
    try:
        form = RoleDistributionForm()
        form.portfolio.choices = [(0, 'Wszystkie')] + [
            (p.id, p.name) for p in Portfolio.query.all()
        ]
        
        if form.validate_on_submit():
            data = analyze_role_distribution(
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                portfolio_id=form.portfolio.data if form.portfolio.data != 0 else None
            )
        else:
            data = analyze_role_distribution()
            
        return render_template('reports/role_distribution.html', form=form, data=data)
    except Exception as e:
        current_app.logger.error(f"Error analyzing role distribution: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@reports_bp.route('/shadow-work')
@auth_required(['admin'])
def shadow_work():
    """Show shadow work report."""
    try:
        form = ShadowWorkForm()
        if form.validate_on_submit():
            data = analyze_shadow_work(
                start_date=form.start_date.data,
                end_date=form.end_date.data
            )
        else:
            data = analyze_shadow_work()
            
        return render_template('reports/shadow_work.html', form=form, data=data)
    except Exception as e:
        current_app.logger.error(f"Error analyzing shadow work: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@reports_bp.route('/availability')
@login_required
def availability():
    """Raport dostępności pracowników."""
    try:
        form = AvailabilityForm()
        form.team.choices = [(0, 'Wszystkie')] + [
            (t.id, t.name) for t in Team.query.all()
        ]
        return render_template('reports/availability.html', form=form)
    except Exception as e:
        current_app.logger.error(f"Error loading availability report: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@reports_bp.route('/summary')
@auth_required()
@cache.cached(timeout=300)  # Cache na 5 minut
def reports_summary():
    return jsonify({"message": "Reports summary"})

@reports_bp.route('/generate', methods=['POST'])
@auth_required()
def generate_report():
    data = request.get_json()
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        report_type = data['report_type']
        
        report_data = generate_report_data(start_date, end_date, report_type)
        pdf = create_pdf_report(report_data)
        
        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'report_{start_date.date()}_{end_date.date()}.pdf'
        )
    except Exception as e:
        current_app.logger.error(f"Report generation error: {str(e)}")
        return jsonify({"error": "Błąd generowania raportu"}), 500

@reports_bp.route('/project/<project_key>', methods=['GET'])
@auth_required()
def get_project_report(project_key):
    try:
        # Pobierz parametry z query string
        days = int(request.args.get('days', 30))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        jira = get_jira_service()
        metrics = jira.get_project_metrics(project_key, start_date, end_date)
        return jsonify(metrics)
    except Exception as e:
        current_app.logger.error(f"Error getting project report: {str(e)}")
        return jsonify({"error": "Błąd podczas generowania raportu"}), 500

@reports_bp.route('/user/<user_name>', methods=['GET'])
@auth_required()
def get_user_report(user_name):
    try:
        # Pobierz parametry z query string
        days = int(request.args.get('days', 30))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        jira = get_jira_service()
        workload = jira.get_user_workload(user_name, start_date, end_date)
        return jsonify(workload)
    except Exception as e:
        current_app.logger.error(f"Error getting user report: {str(e)}")
        return jsonify({"error": "Błąd podczas generowania raportu"}), 500

@reports_bp.route('/projects', methods=['GET'])
@auth_required()
def get_available_projects():
    try:
        # Implementacja pobierania dostępnych projektów
        jira = get_jira_service()
        projects = jira.get_projects()
        return jsonify(projects)
    except Exception as e:
        current_app.logger.error(f"Error getting projects: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania projektów"}), 500

@reports_bp.route('/worklog')
@login_required
def worklog():
    """Raport czasu pracy"""
    return render_template('reports/worklog.html')

@reports_bp.route('/projects')
@login_required
def projects():
    """Raport projektowy"""
    try:
        # Użyj lokalnych projektów zamiast JIRA gdy integracja jest wyłączona
        projects = Project.query.all()
        return render_template('reports/projects.html', projects=projects)
    except Exception as e:
        current_app.logger.error(f"Error loading projects report: {str(e)}")
        return render_template('reports/error.html', error=str(e))

@reports_bp.route('/users')
@login_required
def users():
    """Raport użytkowników"""
    try:
        return render_template('reports/users.html')
    except Exception as e:
        current_app.logger.error(f"Error loading users report: {str(e)}")
        return render_template('reports/error.html', error=str(e))

@reports_bp.route('/admin')
@login_required
@admin_required
def admin():
    """Raport administracyjny"""
    try:
        return render_template('reports/admin.html')
    except Exception as e:
        current_app.logger.error(f"Error loading admin report: {str(e)}")
        return render_template('reports/error.html', error=str(e))

@reports_bp.route('/activity', methods=['GET'])
@auth_required()
def activity_report():
    """Generuje raport aktywności."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        report = ReportService.generate_activity_report(start_date, end_date)
        return jsonify(report)
        
    except Exception as e:
        current_app.logger.error(f"Error generating activity report: {str(e)}")
        return jsonify({"error": "Błąd podczas generowania raportu"}), 500

@reports_bp.route('/teams')
@login_required
def teams():
    """Raport zespołów."""
    return render_template('reports/teams.html')

@reports_bp.route('/export/activity', methods=['GET'])
@auth_required()
def export_activity_report():
    """Eksportuje raport aktywności do CSV."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        report = ReportService.generate_activity_report(start_date, end_date)
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Date', 'User', 'Hours', 'Tasks'])
        
        # Write data
        for date in report['daily_activity']:
            for user, data in report['daily_activity'][date]['users'].items():
                writer.writerow([
                    date,
                    user,
                    data['hours'],
                    data['tasks']
                ])
        
        # Prepare response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'activity_report_{start_date.strftime("%Y%m%d")}-{end_date.strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting activity report: {str(e)}")
        return jsonify({"error": "Błąd podczas eksportu raportu"}), 500

@reports_bp.route('/export')
@login_required
def export_report():
    """Export report view."""
    return render_template('reports/export.html')

@reports_bp.route('/api/reports', methods=['GET'])
@requires_auth
def get_reports():
    """Get all reports."""
    try:
        reports = Report.query.filter_by(is_active=True).all()
        return jsonify({
            'status': 'success',
            'data': [r.to_dict() for r in reports]
        }), 200
    except Exception as e:
        logger.error(f"Error getting reports: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@reports_bp.route('/api/reports', methods=['POST'])
@requires_admin
def create_report():
    """Create a new report."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'report_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        report = Report(
            name=data['name'],
            description=data.get('description'),
            report_type=data['report_type'],
            schedule=data.get('schedule'),
            created_by_id=request.user.id
        )
        
        if 'parameters' in data:
            report.set_parameters(data['parameters'])
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Report created successfully',
            'data': report.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating report: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@reports_bp.route('/api/reports/<int:report_id>', methods=['GET'])
@requires_auth
def get_report(report_id: int):
    """Get report details and latest results."""
    try:
        report = Report.query.get_or_404(report_id)
        latest_result = report.results.order_by(ReportResult.execution_date.desc()).first()
        
        return jsonify({
            'status': 'success',
            'data': {
                'report': report.to_dict(),
                'latest_result': latest_result.to_dict() if latest_result else None
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting report: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@reports_bp.route('/api/reports/<int:report_id>', methods=['PUT'])
@requires_admin
def update_report(report_id: int):
    """Update an existing report."""
    try:
        report = Report.query.get_or_404(report_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            report.name = data['name']
        if 'description' in data:
            report.description = data['description']
        if 'report_type' in data:
            report.report_type = data['report_type']
        if 'schedule' in data:
            report.schedule = data['schedule']
        if 'parameters' in data:
            report.set_parameters(data['parameters'])
        if 'is_active' in data:
            report.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Report updated successfully',
            'data': report.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating report: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@reports_bp.route('/api/reports/<int:report_id>/run', methods=['POST'])
@requires_auth
def run_report(report_id: int):
    """Run a report manually."""
    try:
        report = Report.query.get_or_404(report_id)
        result = report.run()
        
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Report executed successfully',
                'data': result.to_dict()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to execute report'
            }), 500
    except Exception as e:
        logger.error(f"Error running report: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@reports_bp.route('/api/reports/<int:report_id>/results', methods=['GET'])
@requires_auth
def get_report_results(report_id: int):
    """Get all results for a specific report."""
    try:
        report = Report.query.get_or_404(report_id)
        results = report.results.order_by(ReportResult.execution_date.desc()).all()
        
        return jsonify({
            'status': 'success',
            'data': [r.to_dict() for r in results]
        }), 200
    except Exception as e:
        logger.error(f"Error getting report results: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@reports_bp.route('/api/reports/types', methods=['GET'])
@requires_auth
def get_report_types():
    """Get available report types and their parameters."""
    return jsonify({
        'status': 'success',
        'data': {
            'leave_usage': {
                'name': 'Leave Usage Report',
                'parameters': ['start_date', 'end_date', 'team_id']
            },
            'team_availability': {
                'name': 'Team Availability Report',
                'parameters': ['start_date', 'end_date', 'team_id']
            },
            'cost_tracking': {
                'name': 'Cost Tracking Report',
                'parameters': ['start_date', 'end_date', 'project_id']
            },
            'project_allocation': {
                'name': 'Project Allocation Report',
                'parameters': ['start_date', 'end_date', 'portfolio_id']
            }
        }
    }), 200

@reports_bp.route('/reports/<int:report_id>')
@requires_auth
def report_details(report_id: int):
    """Render report details page."""
    report = Report.query.get_or_404(report_id)
    latest_result = report.results.order_by(ReportResult.execution_date.desc()).first()
    return render_template('reports/details.html', report=report, latest_result=latest_result) 