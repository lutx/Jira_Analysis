import pytest
import pkg_resources
import sys

def test_python_version():
    """Test if Python version is correct."""
    assert sys.version_info >= (3, 8), "Python version should be 3.8 or higher"

def test_dependencies():
    """Test if all dependencies are installed with correct versions."""
    with open('requirements.txt') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]
    
    for req in requirements:
        try:
            pkg_resources.require(req)
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
            pytest.fail(f"Dependency issue: {str(e)}")

def test_flask_compatibility():
    """Test if Flask and its extensions are compatible."""
    import flask
    import flask_sqlalchemy
    import flask_migrate
    import flask_login
    
    assert flask.__version__.startswith('2.0'), "Flask version should be 2.0.x"
    assert flask_sqlalchemy.__version__.startswith('2.5'), "Flask-SQLAlchemy should be 2.5.x" 