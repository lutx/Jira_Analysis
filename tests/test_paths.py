import os

def test_static_paths(app):
    assert app.static_folder == 'static'
    assert app.template_folder == 'templates'
    assert os.path.exists(os.path.join(app.root_path, app.static_folder))
    assert os.path.exists(os.path.join(app.root_path, app.template_folder)) 