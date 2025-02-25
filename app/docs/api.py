# Dokumentacja Swagger/OpenAPI dla endpointów statystyk 

from flask_restx import Api, Resource, fields, Namespace
from datetime import datetime
from flask_wtf.csrf import generate_csrf
from app.middleware import csrf_protect

api = Api(
    title='Jira Analysis API',
    version='1.0',
    description='API documentation for Jira Analysis'
)

stats_ns = Namespace('stats', description='Operacje na statystykach zespołu')
api.add_namespace(stats_ns)

# Modele danych
date_range = stats_ns.model('DateRange', {
    'start_date': fields.Date(required=True, description='Data początkowa'),
    'end_date': fields.Date(required=True, description='Data końcowa')
})

workload_user = stats_ns.model('WorkloadUser', {
    'hours': fields.Float(description='Liczba przepracowanych godzin'),
    'percentage': fields.Float(description='Procentowe obciążenie'),
    'status': fields.String(description='Status obciążenia')
})

workload_response = stats_ns.model('WorkloadResponse', {
    'users': fields.Nested(workload_user),
    'expected_hours': fields.Float(description='Oczekiwana liczba godzin'),
    'avg_workload': fields.Float(description='Średnie obciążenie zespołu')
})

activity_response = stats_ns.model('ActivityResponse', {
    'daily_activity': fields.Raw(description='Aktywność dzienna'),
    'total_hours': fields.Float(description='Łączna liczba godzin'),
    'total_tasks': fields.Integer(description='Łączna liczba zadań'),
    'avg_daily_hours': fields.Float(description='Średnia dzienna aktywność')
})

efficiency_user = stats_ns.model('EfficiencyUser', {
    'hours': fields.Float(description='Liczba przepracowanych godzin'),
    'percentage': fields.Float(description='Procentowe obciążenie'),
    'status': fields.String(description='Status obciążenia')
})

efficiency_response = stats_ns.model('EfficiencyResponse', {
    'users': fields.Nested(efficiency_user),
    'avg_efficiency': fields.Float(description='Średnia efektywność zespołu')
})

@stats_ns.route('/teams/<int:team_id>/workload')
class TeamWorkload(Resource):
    @stats_ns.expect(date_range)
    @stats_ns.marshal_with(workload_response)
    @stats_ns.doc(
        description='Pobiera raport obciążenia zespołu',
        params={
            'team_id': 'ID zespołu',
            'start_date': 'Data początkowa (YYYY-MM-DD)',
            'end_date': 'Data końcowa (YYYY-MM-DD)',
            'group_by': 'Grupowanie (day, week, month)',
            'status': 'Filtrowanie po statusie'
        },
        responses={
            200: 'Success',
            400: 'Validation Error',
            404: 'Team not found',
            500: 'Server Error'
        }
    )
    def get(self, team_id):
        """Pobiera raport obciążenia zespołu."""
        pass

@stats_ns.route('/teams/<int:team_id>/activity')
class TeamActivity(Resource):
    @stats_ns.expect(date_range)
    @stats_ns.marshal_with(activity_response)
    @stats_ns.doc(
        description='Pobiera raport aktywności zespołu',
        params={
            'team_id': 'ID zespołu',
            'start_date': 'Data początkowa (YYYY-MM-DD)',
            'end_date': 'Data końcowa (YYYY-MM-DD)',
            'group_by': 'Grupowanie (day, week, month)',
            'min_hours': 'Minimalna liczba godzin'
        },
        responses={
            200: 'Success',
            400: 'Validation Error',
            404: 'Team not found',
            500: 'Server Error'
        }
    )
    def get(self, team_id):
        """Pobiera raport aktywności zespołu."""
        pass

@stats_ns.route('/teams/<int:team_id>/export/<report_type>')
class ExportStats(Resource):
    @stats_ns.expect(date_range)
    @stats_ns.doc(
        description='Eksportuje raport statystyk',
        params={
            'team_id': 'ID zespołu',
            'report_type': 'Typ raportu (workload, activity, efficiency)',
            'format': 'Format eksportu (csv, pdf)',
            'start_date': 'Data początkowa (YYYY-MM-DD)',
            'end_date': 'Data końcowa (YYYY-MM-DD)',
            'group_by': 'Grupowanie (day, week, month)'
        },
        security='csrf',
        responses={
            200: 'Success',
            400: 'Validation Error',
            404: 'Team not found',
            415: 'Unsupported Media Type',
            500: 'Server Error'
        }
    )
    @csrf_protect()
    def post(self, team_id, report_type):
        """Eksportuje raport statystyk."""
        pass

@stats_ns.route('/teams/<int:team_id>/efficiency')
class TeamEfficiency(Resource):
    @stats_ns.expect(date_range)
    @stats_ns.marshal_with(efficiency_response)
    @stats_ns.doc(
        description='Pobiera raport efektywności zespołu',
        params={
            'team_id': 'ID zespołu',
            'start_date': 'Data początkowa (YYYY-MM-DD)',
            'end_date': 'Data końcowa (YYYY-MM-DD)',
            'group_by': 'Grupowanie (day, week, month)',
            'min_efficiency': 'Minimalny poziom efektywności (%)'
        },
        responses={
            200: 'Success',
            400: 'Validation Error',
            404: 'Team not found',
            500: 'Server Error'
        }
    )
    def get(self, team_id):
        """Pobiera raport efektywności zespołu."""
        pass

@stats_ns.route('/csrf-token')
class CSRFToken(Resource):
    def get(self):
        """Pobiera token CSRF."""
        token = generate_csrf()
        return {'csrf_token': token} 