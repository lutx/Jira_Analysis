document.addEventListener('DOMContentLoaded', function() {
    // Inicjalizacja formularza
    initForm();
    
    // Ustaw domyślne daty
    setDefaultDates();
    
    // Załaduj projekty
    loadProjects();
});

function initForm() {
    const form = document.getElementById('worklogReportForm');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        generateReport();
    });
}

function setDefaultDates() {
    const today = new Date();
    const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    document.getElementById('dateStart').valueAsDate = lastWeek;
    document.getElementById('dateEnd').valueAsDate = today;
}

async function loadProjects() {
    try {
        console.log('Loading projects...'); // Debug log
        
        const response = await fetch('/api/projects/list', {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        console.log('Response status:', response.status); // Debug log
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Get the raw response text first
        const responseText = await response.text();
        console.log('Raw response:', responseText); // Debug log
        
        if (!responseText) {
            throw new Error('Empty response from server');
        }
        
        // Try to parse as JSON
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('JSON parse error:', e);
            console.error('Response text:', responseText);
            throw new Error('Invalid JSON response from server');
        }
        
        console.log('Parsed data:', data); // Debug log
        
        if (data.status === 'success') {
            const projectSelect = document.getElementById('projectFilter');
            if (!projectSelect) {
                throw new Error('Project select element not found');
            }
            
            // Zachowaj opcję "Wszystkie projekty"
            const allProjectsOption = projectSelect.options[0];
            projectSelect.innerHTML = '';
            projectSelect.appendChild(allProjectsOption);
            
            // Sprawdź czy projects jest tablicą
            if (!Array.isArray(data.projects)) {
                throw new Error('Projects data is not an array');
            }
            
            // Dodaj projekty
            data.projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.key;
                option.textContent = project.display_name;
                projectSelect.appendChild(option);
            });
            
            console.log('Projects loaded successfully'); // Debug log
        } else {
            throw new Error(data.message || 'Nieprawidłowa odpowiedź serwera');
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        Swal.fire({
            icon: 'error',
            title: 'Błąd!',
            text: 'Nie udało się załadować listy projektów: ' + error.message
        });
    }
}

async function generateReport() {
    const dateStart = document.getElementById('dateStart').value;
    const dateEnd = document.getElementById('dateEnd').value;
    const projectKey = document.getElementById('projectFilter').value;
    
    try {
        const response = await fetch('/api/reports/worklog', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                date_start: dateStart,
                date_end: dateEnd,
                project_key: projectKey
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('reportResults').innerHTML = data.html;
        } else {
            throw new Error(data.message || 'Błąd generowania raportu');
        }
    } catch (error) {
        console.error('Error generating report:', error);
        Swal.fire({
            icon: 'error',
            title: 'Błąd!',
            text: error.message || 'Nie udało się wygenerować raportu'
        });
    }
}

async function exportReport() {
    const dateStart = document.getElementById('dateStart').value;
    const dateEnd = document.getElementById('dateEnd').value;
    const projectKey = document.getElementById('projectFilter').value;
    
    try {
        const response = await fetch(`/api/reports/worklog/export?date_start=${dateStart}&date_end=${dateEnd}&project_key=${projectKey}`, {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `worklog_report_${dateStart}_${dateEnd}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } else {
            throw new Error('Błąd eksportu raportu');
        }
    } catch (error) {
        console.error('Error exporting report:', error);
        Swal.fire({
            icon: 'error',
            title: 'Błąd!',
            text: 'Nie udało się wyeksportować raportu'
        });
    }
} 