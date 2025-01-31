document.addEventListener('DOMContentLoaded', function() {
    loadWorklogs();
});

async function loadWorklogs() {
    try {
        const response = await fetch('/get_worklogs');
        const worklogs = await response.json();
        
        const tbody = document.querySelector('#worklogsTable tbody');
        tbody.innerHTML = '';
        
        worklogs.forEach(worklog => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${worklog.user_name}</td>
                <td>${worklog.project}</td>
                <td>${worklog.task_key}</td>
                <td>${worklog.time_logged}</td>
                <td>${worklog.date}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading worklogs:', error);
        showError('Błąd podczas ładowania worklogów');
    }
}

function showError(message) {
    alert(message); // Tymczasowo używamy alert
} 