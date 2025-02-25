from flask import flash

def notify_success(message):
    flash(message, 'success')

def notify_error(message):
    flash(message, 'error')

def notify_info(message):
    flash(message, 'info') 