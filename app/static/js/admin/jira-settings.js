document.addEventListener('DOMContentLoaded', function() {
    const testButton = document.getElementById('testJiraConnection');
    if (testButton) {
        testButton.addEventListener('click', testJiraConnection);
    }
});

async function testJiraConnection() {
    const url = document.getElementById('jira_url').value;
    const username = document.getElementById('jira_username').value;
    const apiToken = document.getElementById('jira_token').value;

    if (!url || !username || !apiToken) {
        Swal.fire({
            title: 'Błąd',
            text: 'Wszystkie pola są wymagane',
            icon: 'error'
        });
        return;
    }

    try {
        const response = await fetch('/api/jira/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: JSON.stringify({
                url: url,
                username: username,
                api_token: apiToken
            })
        });

        const data = await response.json();
        
        Swal.fire({
            title: data.status === 'success' ? 'Sukces' : 'Błąd',
            text: data.message,
            icon: data.status === 'success' ? 'success' : 'error'
        });

    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            title: 'Błąd',
            text: 'Wystąpił błąd podczas testowania połączenia',
            icon: 'error'
        });
    }
} 