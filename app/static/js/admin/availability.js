document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const availabilityTable = $('#availabilityTable').DataTable({
        pageLength: 25,
        order: [[3, 'desc']]
    });
    
    // Initialize DateRangePicker
    $('.daterange').daterangepicker({
        opens: 'left',
        locale: {
            format: 'YYYY-MM-DD'
        },
        ranges: {
            'Next 7 Days': [moment(), moment().add(6, 'days')],
            'Next 30 Days': [moment(), moment().add(29, 'days')],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Next Month': [moment().add(1, 'month').startOf('month'), moment().add(1, 'month').endOf('month')]
        }
    });
    
    // Initialize FullCalendar
    const calendarEl = document.getElementById('availabilityCalendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        events: '/admin/reports/availability/calendar-data',
        eventClick: function(info) {
            showEventDetails(info.event);
        }
    });
    calendar.render();
    
    // Handle filter form submit
    $('#availabilityFilters').on('submit', function(e) {
        e.preventDefault();
        updateAvailabilityData();
    });
});

function updateAvailabilityData() {
    const filters = {
        team_id: $('[name=team_id]').val(),
        date_range: $('[name=date_range]').val(),
        status: $('[name=status]').val()
    };
    
    fetch('/admin/reports/availability/data?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            // Update daily availability chart
            updateChart(
                document.querySelector('[data-chart-type="availability"]:first-child'),
                data.daily_availability
            );
            
            // Update team availability chart
            updateChart(
                document.querySelector('[data-chart-type="availability"]:last-child'),
                data.team_availability
            );
            
            // Update calendar events
            const calendar = document.querySelector('#availabilityCalendar');
            if (calendar) {
                const fc = calendar.fullCalendar('getCalendar');
                fc.removeAllEvents();
                fc.addEventSource(data.calendar_events);
            }
            
            // Update detailed table
            updateTable(data.availability_details);
        })
        .catch(error => {
            console.error('Error updating availability data:', error);
            showNotification('Error updating availability data', 'error');
        });
}

function updateChart(container, data) {
    const chart = Chart.getChart(container.querySelector('canvas'));
    if (chart) {
        chart.data = data;
        chart.update();
    } else {
        createAvailabilityChart(container, data);
    }
}

function updateTable(data) {
    const table = $('#availabilityTable').DataTable();
    table.clear();
    
    data.forEach(entry => {
        table.row.add([
            entry.user.display_name,
            entry.team.name,
            `<span class="badge bg-${entry.status_class}">${entry.status}</span>`,
            entry.from_date,
            entry.to_date,
            entry.notes
        ]);
    });
    
    table.draw();
}

function showEventDetails(event) {
    // Show event details in a modal or tooltip
    const title = event.title;
    const start = event.start.toLocaleDateString();
    const end = event.end ? event.end.toLocaleDateString() : start;
    const description = event.extendedProps.description || '';
    
    Swal.fire({
        title: title,
        html: `
            <p><strong>From:</strong> ${start}</p>
            <p><strong>To:</strong> ${end}</p>
            <p>${description}</p>
        `,
        icon: 'info'
    });
} 