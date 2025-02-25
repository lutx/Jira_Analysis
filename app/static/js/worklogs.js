document.addEventListener('DOMContentLoaded', function() {
    initializeDateRangePicker();
    loadProjects();
    loadWorklogs();
    
    // Event listeners
    document.getElementById('projectSelect').addEventListener('change', loadIssues);
});

function initializeDateRangePicker() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);

    $('#dateRange').daterangepicker({
        startDate: thirtyDaysAgo,
        endDate: today,
        ranges: {
           'Dzisiaj': [moment(), moment()],
           'Wczoraj': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
           'Ostatnie 7 dni': [moment().subtract(6, 'days'), moment()],
           'Ostatnie 30 dni': [moment().subtract(29, 'days'), moment()],
           'Ten miesiąc': [moment().startOf('month'), moment().endOf('month')],
           'Poprzedni miesiąc': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        },
        locale: {
            format: 'YYYY-MM-DD',
            separator: ' - ',
            applyLabel: 'Zastosuj',
            cancelLabel: 'Anuluj',
            fromLabel: 'Od',
            toLabel: 'Do',
            customRangeLabel: 'Własny zakres',
            weekLabel: 'T',
            daysOfWeek: ['Nd', 'Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So'],
            monthNames: ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec', 'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'],
            firstDay: 1
        }
    }, function(start, end) {
        document.getElementById('startDate').value = start.format('YYYY-MM-DD');
        document.getElementById('endDate').value = end.format('YYYY-MM-DD');
        loadWorklogs();
    });

    // Set initial values
    document.getElementById('startDate').value = thirtyDaysAgo.toISOString().split('T')[0];
    document.getElementById('endDate').value = today.toISOString().split('T')[0];
}

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        
        const projectSelect = document.getElementById('projectSelect');
        const projectFilter = document.getElementById('projectFilter');
        
        projects.forEach(project => {
            projectSelect.add(new Option(project.name, project.key));
            projectFilter.add(new Option(project.name, project.key));
        });
    } catch (error) {
        console.error('Error loading projects:', error);
        showError('Błąd podczas ładowania projektów');
    }
}

async function loadIssues() {
    try {
        const projectKey = document.getElementById('projectSelect').value;
        if (!projectKey) return;
        
        const response = await fetch(`/api/issues?jql=project=${projectKey}`);
        const issues = await response.json();
        
        const issueSelect = document.getElementById('issueSelect');
        issueSelect.innerHTML = '<option value="">Wybierz zadanie</option>';
        
        issues.forEach(issue => {
            issueSelect.add(new Option(`${issue.key}: ${issue.summary}`, issue.key));
        });
    } catch (error) {
        console.error('Error loading issues:', error);
        showError('Błąd podczas ładowania zadań');
    }
}

async function loadWorklogs() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const projectKey = document.getElementById('projectFilter').value;
        
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (projectKey) params.append('project_key', projectKey);
        
        const response = await fetch(`/api/worklogs?${params}`);
        const data = await response.json();
        
        // Update statistics
        document.getElementById('totalHours').textContent = data.stats.total_hours.toFixed(2);
        document.getElementById('totalWorklogs').textContent = data.stats.total_count;
        document.getElementById('activeUsers').textContent = data.stats.active_users;
        document.getElementById('avgHoursPerDay').textContent = data.stats.avg_daily_hours.toFixed(2);

        // Update table
        const tbody = document.querySelector('#worklogsTable tbody');
        tbody.innerHTML = '';
        
        data.worklogs.forEach(worklog => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${worklog.work_date}</td>
                <td>${worklog.project.name} (${worklog.project.key})</td>
                <td>${worklog.issue.key}: ${worklog.issue.summary}</td>
                <td>${worklog.time_spent_hours}</td>
                <td>${worklog.description || ''}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteWorklog(${worklog.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading worklogs:', error);
        showError('Błąd podczas ładowania worklogów');
    }
}

async function saveWorklog() {
    try {
        const data = {
            project_key: document.getElementById('projectSelect').value,
            issue_key: document.getElementById('issueSelect').value,
            work_date: document.getElementById('workDate').value,
            time_spent: parseFloat(document.getElementById('timeSpent').value),
            description: document.getElementById('description').value
        };
        
        const response = await fetch('/api/worklogs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('addWorklogModal')).hide();
            document.getElementById('worklogForm').reset();
            loadWorklogs();
            showSuccess('Worklog został dodany');
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Błąd podczas dodawania worklogu');
        }
    } catch (error) {
        console.error('Error saving worklog:', error);
        showError(error.message);
    }
}

async function deleteWorklog(id) {
    if (!confirm('Czy na pewno chcesz usunąć ten worklog?')) {
        return;
    }

    try {
        const response = await fetch(`/api/worklogs/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadWorklogs();
            showSuccess('Worklog został usunięty');
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Błąd podczas usuwania worklogu');
        }
    } catch (error) {
        console.error('Error deleting worklog:', error);
        showError(error.message);
    }
}

async function syncWorklogs() {
    try {
        const response = await fetch('/api/worklogs/sync', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            loadWorklogs();
            showSuccess(`Synchronizacja zakończona: Dodano ${data.added}, Zaktualizowano ${data.updated}`);
        } else {
            throw new Error(data.error || 'Błąd podczas synchronizacji');
        }
    } catch (error) {
        console.error('Error syncing worklogs:', error);
        showError(error.message);
    }
}

function applyFilters() {
    loadWorklogs();
}

function showSuccess(message) {
    // Implementacja wyświetlania sukcesu
    alert(message);
}

function showError(message) {
    // Implementacja wyświetlania błędu
    alert(message);
} 