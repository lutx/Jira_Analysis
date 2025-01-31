document.addEventListener('DOMContentLoaded', function() {
    loadJiraConfig();
    
    document.getElementById('jiraConfigForm').addEventListener('submit', saveJiraConfig);
    document.getElementById('testConnection').addEventListener('click', testJiraConnection);
});

async function loadJiraConfig() {
    try {
        const response = await fetch('/api/admin/jira/config');
        const config = await response.json();
        
        document.getElementById('jiraUrl').value = config.jira_url || '';
        document.getElementById('jiraUser').value = config.jira_user || '';
        document.getElementById('jiraToken').value = config.jira_token || '';
    } catch (error) {
        console.error('Error loading Jira config:', error);
        showError('Błąd podczas ładowania konfiguracji Jiry');
    }
}

async function saveJiraConfig(event) {
    event.preventDefault();
    
    const config = {
        jira_url: document.getElementById('jiraUrl').value,
        jira_user: document.getElementById('jiraUser').value,
        jira_token: document.getElementById('jiraToken').value
    };
    
    try {
        const response = await fetch('/api/admin/jira/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Błąd podczas zapisywania konfiguracji');
        }
        
        showSuccess('Konfiguracja została zapisana');
    } catch (error) {
        console.error('Error saving Jira config:', error);
        showError(error.message);
    }
}

async function testJiraConnection() {
    try {
        const response = await fetch('/api/admin/jira/test', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess('Połączenie z Jirą działa poprawnie');
            document.getElementById('testResults').textContent = JSON.stringify(data, null, 2);
        } else {
            throw new Error(data.error || 'Błąd podczas testowania połączenia');
        }
    } catch (error) {
        console.error('Error testing Jira connection:', error);
        showError(error.message);
    }
}

async function testJiraProjects() {
    try {
        const response = await fetch('/api/admin/jira/test/projects');
        const data = await response.json();
        document.getElementById('testResults').textContent = JSON.stringify(data, null, 2);
    } catch (error) {
        console.error('Error testing Jira projects:', error);
        showError('Błąd podczas pobierania projektów');
    }
}

async function testJiraUsers() {
    try {
        const response = await fetch('/api/admin/jira/test/users');
        const data = await response.json();
        document.getElementById('testResults').textContent = JSON.stringify(data, null, 2);
    } catch (error) {
        console.error('Error testing Jira users:', error);
        showError('Błąd podczas pobierania użytkowników');
    }
}

async function testJiraWorklogs() {
    try {
        const response = await fetch('/api/admin/jira/test/worklogs');
        const data = await response.json();
        document.getElementById('testResults').textContent = JSON.stringify(data, null, 2);
    } catch (error) {
        console.error('Error testing Jira worklogs:', error);
        showError('Błąd podczas pobierania worklogów');
    }
}

function showSuccess(message) {
    alert(message); // Tymczasowo używamy alert
}

function showError(message) {
    alert(message); // Tymczasowo używamy alert
} 