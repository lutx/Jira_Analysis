import pytest
import time
from flask import url_for

def test_dashboard_load_time(client, auth):
    auth.login()
    
    start_time = time.time()
    response = client.get(url_for('views.dashboard'))
    end_time = time.time()
    
    load_time = end_time - start_time
    assert load_time < 0.5  # Dashboard should load in less than 500ms
    assert response.status_code == 200

def test_project_list_performance(client, auth):
    auth.login()
    
    start_time = time.time()
    response = client.get(url_for('views.projects'))
    end_time = time.time()
    
    load_time = end_time - start_time
    assert load_time < 1.0  # Project list should load in less than 1 second
    assert response.status_code == 200 