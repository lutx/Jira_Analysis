document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
});

async function loadSettings() {
    try {
        const response = await fetch('/api/teams/settings');
        const settings = await response.json();
        
        if (!response.ok) {
            throw new Error(settings.error || 'Błąd podczas ładowania ustawień');
        }
        
        // Podstawowe informacje
        document.getElementById('defaultWorkHours').value = settings.default_work_hours;
        
        // Dni pracy
        settings.work_days.forEach(day => {
            document.getElementById(`workDay${day}`).checked = true;
        });
        
        // Powiadomienia
        document.getElementById('notifyOverwork').checked = settings.notifications.overwork;
        document.getElementById('notifyUnderwork').checked = settings.notifications.underwork;
        document.getElementById('notifyTeamLeader').checked = settings.notifications.team_leader;
        
        // Integracje
        document.getElementById('slackChannel').value = settings.integrations.slack_channel || '';
        document.getElementById('teamEmail').value = settings.integrations.team_email || '';
        
    } catch (error) {
        console.error('Error loading settings:', error);
        showError('Błąd podczas ładowania ustawień');
    }
}

async function saveSettings() {
    try {
        const workDays = [];
        for (let i = 1; i <= 7; i++) {
            if (document.getElementById(`workDay${i}`).checked) {
                workDays.push(i);
            }
        }
        
        const settings = {
            default_work_hours: parseFloat(document.getElementById('defaultWorkHours').value),
            work_days: workDays,
            notifications: {
                overwork: document.getElementById('notifyOverwork').checked,
                underwork: document.getElementById('notifyUnderwork').checked,
                team_leader: document.getElementById('notifyTeamLeader').checked
            },
            integrations: {
                slack_channel: document.getElementById('slackChannel').value,
                team_email: document.getElementById('teamEmail').value
            }
        };
        
        const response = await fetch('/api/teams/settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Błąd podczas zapisywania ustawień');
        }
        
        showSuccess('Ustawienia zostały zapisane');
        
    } catch (error) {
        console.error('Error saving settings:', error);
        showError(error.message);
    }
}

function resetSettings() {
    if (!confirm('Czy na pewno chcesz zresetować wszystkie ustawienia?')) return;
    
    // Podstawowe informacje
    document.getElementById('defaultWorkHours').value = 8;
    
    // Dni pracy
    for (let i = 1; i <= 7; i++) {
        document.getElementById(`workDay${i}`).checked = i <= 5;
    }
    
    // Powiadomienia
    document.getElementById('notifyOverwork').checked = true;
    document.getElementById('notifyUnderwork').checked = true;
    document.getElementById('notifyTeamLeader').checked = true;
    
    // Integracje
    document.getElementById('slackChannel').value = '';
    document.getElementById('teamEmail').value = '';
    
    showSuccess('Ustawienia zostały zresetowane');
}

function showSuccess(message) {
    // Implementacja wyświetlania sukcesu
    alert(message);
}

function showError(message) {
    // Implementacja wyświetlania błędu
    alert(message);
} 