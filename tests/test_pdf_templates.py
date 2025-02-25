import pytest
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

@pytest.fixture
def jinja_env():
    """Fixture tworzący środowisko Jinja2."""
    return Environment(loader=FileSystemLoader('templates/reports'))

def test_member_stats_pdf_template(jinja_env, test_team, sample_member_stats):
    """Test szablonu PDF dla statystyk członka zespołu."""
    template = jinja_env.get_template('member_stats_pdf.html')
    
    html = template.render(
        team=test_team,
        user_name='test_user',
        stats=sample_member_stats,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 1, 2),
        datetime=datetime
    )
    
    # Sprawdź czy wymagane elementy są w HTML
    assert 'Statystyki Członka Zespołu' in html
    assert 'test_user' in html
    assert '2023-01-01' in html
    assert '2023-01-02' in html
    assert 'Łączna liczba godzin: 14.0' in html
    assert 'PROJ-1' in html
    assert 'PROJ-2' in html

def test_project_stats_pdf_template(jinja_env, test_team, sample_project_stats):
    """Test szablonu PDF dla statystyk projektu."""
    template = jinja_env.get_template('project_stats_pdf.html')
    
    html = template.render(
        team=test_team,
        project_key='TEST-1',
        stats=sample_project_stats,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 1, 2),
        datetime=datetime
    )
    
    # Sprawdź czy wymagane elementy są w HTML
    assert 'Statystyki Projektu' in html
    assert 'TEST-1' in html
    assert '2023-01-01' in html
    assert '2023-01-02' in html
    assert 'Łączna liczba godzin: 24.0' in html
    assert 'user1' in html
    assert 'user2' in html
    assert '66.7%' in html
    assert '33.3%' in html

def test_pdf_template_styles(jinja_env):
    """Test stylów CSS w szablonach PDF."""
    for template_name in ['member_stats_pdf.html', 'project_stats_pdf.html']:
        template = jinja_env.get_template(template_name)
        html = template.render(
            team=None,
            stats={},
            start_date=datetime.now(),
            end_date=datetime.now(),
            datetime=datetime
        )
        
        # Sprawdź czy wymagane style CSS są obecne
        assert 'font-family: Arial, sans-serif' in html
        assert 'border-collapse: collapse' in html
        assert 'text-align: center' in html 