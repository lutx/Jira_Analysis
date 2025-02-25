def get_activity_level(hours: float, avg_hours: float) -> str:
    """Zwraca poziom aktywności."""
    if hours > avg_hours * 1.2:
        return 'high'
    if hours < avg_hours * 0.8:
        return 'low'
    return 'normal'

def get_efficiency_level(efficiency: float) -> str:
    """Zwraca poziom efektywności."""
    if efficiency > 90:
        return 'high'
    if efficiency < 70:
        return 'low'
    return 'medium' 