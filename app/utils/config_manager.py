from typing import Dict, Optional
from flask import current_app
import json
from pathlib import Path

CONFIG_FILE = 'jira_config.json'

def get_config_path() -> Path:
    """Get the path to the config file."""
    instance_path = Path(current_app.instance_path)
    instance_path.mkdir(exist_ok=True)
    return instance_path / CONFIG_FILE

def save_jira_config(config_data: Dict) -> None:
    """Save JIRA configuration to a file."""
    try:
        config_path = get_config_path()
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        current_app.logger.info("JIRA configuration saved successfully")
    except Exception as e:
        current_app.logger.error(f"Error saving JIRA config: {str(e)}")
        raise

def load_jira_config() -> Optional[Dict]:
    """Load JIRA configuration from file."""
    try:
        config_path = get_config_path()
        if not config_path.exists():
            current_app.logger.warning("No JIRA configuration file found")
            return None
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        current_app.logger.info("JIRA configuration loaded successfully")
        return config
    except Exception as e:
        current_app.logger.error(f"Error loading JIRA config: {str(e)}")
        return None 