from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.exceptions import ValidationError

def validate_date_range(start_date: datetime, end_date: datetime, 
                       max_days: int = 365) -> None:
    """Waliduje zakres dat."""
    if start_date > end_date:
        raise ValidationError(
            "Data końcowa nie może być wcześniejsza niż początkowa",
            {"start_date": start_date, "end_date": end_date}
        )
    
    date_range = (end_date - start_date).days
    if date_range > max_days:
        raise ValidationError(
            f"Maksymalny zakres dat to {max_days} dni",
            {"max_days": max_days, "requested_days": date_range}
        )
    
    if end_date > datetime.now():
        raise ValidationError(
            "Data końcowa nie może być w przyszłości",
            {"end_date": end_date}
        )

def validate_stats_filters(filters: Dict[str, Any]) -> None:
    """Waliduje filtry statystyk."""
    required_fields = ['start_date', 'end_date']
    for field in required_fields:
        if field not in filters:
            raise ValidationError(
                f"Brak wymaganego pola: {field}",
                {"missing_field": field}
            )
    
    if 'group_by' in filters:
        valid_groups = ['day', 'week', 'month']
        if filters['group_by'] not in valid_groups:
            raise ValidationError(
                "Nieprawidłowy format grupowania",
                {"valid_groups": valid_groups, "provided": filters['group_by']}
            )

def validate_export_options(options: Dict[str, Any]) -> None:
    """Waliduje opcje eksportu."""
    if 'format' not in options:
        raise ValidationError("Nie określono formatu eksportu")
    
    valid_formats = ['csv', 'pdf']
    if options['format'] not in valid_formats:
        raise ValidationError(
            "Nieobsługiwany format eksportu",
            {"valid_formats": valid_formats, "provided": options['format']}
        )

def validate_worklog_data(worklog: Dict[str, Any]) -> None:
    """Waliduje dane worklogu."""
    required_fields = ['time_spent', 'work_date', 'issue_key']
    for field in required_fields:
        if field not in worklog:
            raise ValidationError(
                f"Brak wymaganego pola: {field}",
                {"missing_field": field}
            )
    
    if worklog['time_spent'] <= 0:
        raise ValidationError(
            "Liczba godzin musi być większa od 0",
            {"time_spent": worklog['time_spent']}
        )
    
    try:
        datetime.strptime(worklog['work_date'], '%Y-%m-%d')
    except ValueError:
        raise ValidationError(
            "Nieprawidłowy format daty",
            {"work_date": worklog['work_date'], "expected_format": "YYYY-MM-DD"}
        )

def validate_team_member(team_id: int, user_name: str) -> None:
    """Waliduje członka zespołu."""
    from app.models.team import Team
    
    team = Team.get_by_id(team_id)
    if not team:
        raise ResourceNotFoundError(
            "Zespół nie istnieje",
            {"team_id": team_id}
        )
    
    member = team.get_member(user_name)
    if not member:
        raise ValidationError(
            "Użytkownik nie jest członkiem zespołu",
            {"team_id": team_id, "user_name": user_name}
        )
    
    if not member.is_active:
        raise ValidationError(
            "Użytkownik jest nieaktywny",
            {"team_id": team_id, "user_name": user_name}
        )

def validate_project_access(team_id: int, project_key: str) -> None:
    """Waliduje dostęp do projektu."""
    from app.models.team import Team
    
    team = Team.get_by_id(team_id)
    if not team:
        raise ResourceNotFoundError(
            "Zespół nie istnieje",
            {"team_id": team_id}
        )
    
    if not team.has_project_access(project_key):
        raise ValidationError(
            "Projekt nie jest przypisany do zespołu",
            {"team_id": team_id, "project_key": project_key}
        )

def validate_concurrent_access(team_id: int) -> None:
    """Waliduje równoczesny dostęp do zasobów zespołu."""
    from app.models.team import Team
    from app.cache import cache
    
    lock_key = f"team_lock_{team_id}"
    if cache.get(lock_key):
        raise ValidationError(
            "Zasób jest aktualnie używany przez inny proces",
            {"team_id": team_id}
        )
    
    # Ustaw blokadę na 30 sekund
    cache.set(lock_key, True, timeout=30)

def validate_export_format(format: str) -> None:
    """Waliduje format eksportu."""
    valid_formats = ['csv', 'pdf']
    if format not in valid_formats:
        raise ValidationError(
            "Nieobsługiwany format eksportu",
            {"valid_formats": valid_formats, "provided": format}
        ) 