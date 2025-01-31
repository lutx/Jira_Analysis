document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/reports/workload')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#workloadTable tbody');
            data.forEach(row => {
                const tr = document.createElement('tr');
                const status = getWorkloadStatus(row.overload_percentage);
                
                tr.innerHTML = `
                    <td>${row.user_name}</td>
                    <td>${row.month}</td>
                    <td>${row.actual_hours.toFixed(1)}</td>
                    <td>${row.planned_hours.toFixed(1)}</td>
                    <td class="${status.class}">${row.overload_percentage}%</td>
                    <td><span class="badge ${status.badgeClass}">${status.text}</span></td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(error => {
            console.error('Error loading workload data:', error);
            alert('Błąd podczas ładowania danych o obciążeniu');
        });
});

function getWorkloadStatus(percentage) {
    if (percentage > 20) {
        return {
            text: 'Znaczne przeciążenie',
            class: 'text-danger',
            badgeClass: 'bg-danger'
        };
    } else if (percentage > 10) {
        return {
            text: 'Umiarkowane przeciążenie',
            class: 'text-warning',
            badgeClass: 'bg-warning'
        };
    } else if (percentage < -10) {
        return {
            text: 'Niedociążenie',
            class: 'text-info',
            badgeClass: 'bg-info'
        };
    } else {
        return {
            text: 'Optymalne',
            class: 'text-success',
            badgeClass: 'bg-success'
        };
    }
} 