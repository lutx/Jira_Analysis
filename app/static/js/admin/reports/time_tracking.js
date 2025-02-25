// Time Tracking Report Management
const TimeTrackingReport = {
    charts: {},
    table: null,

    init() {
        this.initializeCharts();
        this.initializeTable();
        this.bindEvents();
        this.loadData();
    },

    initializeCharts() {
        // Time Distribution Chart
        this.charts.distribution = new Chart(document.getElementById('timeDistribution'), {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgb(255, 99, 132)',
                        'rgb(54, 162, 235)',
                        'rgb(255, 205, 86)',
                        'rgb(75, 192, 192)'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });

        // Hours Trend Chart
        this.charts.hours = new Chart(document.getElementById('hoursChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Total Hours',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: 'Billable Hours',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Hours'
                        }
                    }
                }
            }
        });
    },

    initializeTable() {
        this.table = $('#timeTable').DataTable({
            pageLength: 25,
            order: [[1, 'desc']],
            dom: 'Bfrtip',
            buttons: [
                'copy', 'csv', 'excel', 'pdf'
            ],
            footerCallback: function(row, data, start, end, display) {
                const api = this.api();
                const total = api
                    .column(4)
                    .data()
                    .reduce((a, b) => a + parseFloat(b), 0);
                
                $(api.column(4).footer()).html(total.toFixed(2));
            }
        });
    },

    bindEvents() {
        $('#dateRange').on('change', this.loadData.bind(this));
        $('#teamFilter').on('change', this.loadData.bind(this));
        $('#activityType').on('change', this.loadData.bind(this));
        $('#exportReport').on('click', this.exportReport.bind(this));
    },

    async loadData() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            activity_type: $('#activityType').val()
        };

        try {
            const response = await fetch('/api/admin/reports/time-tracking?' + new URLSearchParams(filters));
            const data = await response.json();

            if (response.ok) {
                this.updateCharts(data);
                this.updateTable(data.details);
                this.updateSummary(data.summary);
            } else {
                toastr.error(data.message || 'Error loading time tracking data');
            }
        } catch (error) {
            console.error('Error loading time tracking data:', error);
            toastr.error('Error loading time tracking data');
        }
    },

    updateCharts(data) {
        // Update Distribution Chart
        this.charts.distribution.data.labels = data.distribution.labels;
        this.charts.distribution.data.datasets[0].data = data.distribution.values;
        this.charts.distribution.update();

        // Update Hours Chart
        this.charts.hours.data.labels = data.trend.labels;
        this.charts.hours.data.datasets[0].data = data.trend.total_hours;
        this.charts.hours.data.datasets[1].data = data.trend.billable_hours;
        this.charts.hours.update();
    },

    updateTable(data) {
        this.table.clear();
        this.table.rows.add(data);
        this.table.draw();
    },

    updateSummary(data) {
        $('#totalHours').text(data.total_hours.toFixed(2));
        $('#billableHours').text(data.billable_hours.toFixed(2));
        $('#billableRate').text(data.billable_rate.toFixed(1) + '%');
        $('#avgDailyHours').text(data.avg_daily_hours.toFixed(2));
    },

    async exportReport() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            activity_type: $('#activityType').val(),
            format: 'excel'
        };

        try {
            const response = await fetch('/api/admin/reports/time-tracking/export?' + new URLSearchParams(filters));
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'time_tracking_report.xlsx';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            } else {
                const data = await response.json();
                toastr.error(data.message || 'Error exporting report');
            }
        } catch (error) {
            console.error('Error exporting report:', error);
            toastr.error('Error exporting report');
        }
    }
};

// Initialize on document ready
$(document).ready(() => {
    TimeTrackingReport.init();
}); 