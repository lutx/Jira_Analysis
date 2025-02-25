// Productivity Report Management
const ProductivityReport = {
    charts: {},
    table: null,

    init() {
        this.initializeCharts();
        this.initializeTable();
        this.bindEvents();
        this.loadData();
    },

    initializeCharts() {
        // Productivity Trend Chart
        this.charts.trend = new Chart(document.getElementById('productivityTrend'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Productivity Score',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Productivity Score'
                        }
                    }
                }
            }
        });

        // Team Comparison Chart
        this.charts.team = new Chart(document.getElementById('teamComparison'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Team Productivity',
                    data: [],
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgb(75, 192, 192)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Average Productivity Score'
                        }
                    }
                }
            }
        });
    },

    initializeTable() {
        this.table = $('#productivityTable').DataTable({
            pageLength: 25,
            order: [[4, 'desc']],
            columns: [
                { data: 'name' },
                { data: 'project' },
                { data: 'tasks_completed' },
                { data: 'time_spent' },
                { data: 'productivity_score' },
                { data: 'trend' }
            ]
        });
    },

    bindEvents() {
        $('#dateRange').on('change', this.loadData.bind(this));
        $('#teamFilter').on('change', this.loadData.bind(this));
        $('#projectFilter').on('change', this.loadData.bind(this));
        $('#exportReport').on('click', this.exportReport.bind(this));
    },

    async loadData() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            project_id: $('#projectFilter').val()
        };

        try {
            const response = await fetch('/api/admin/reports/productivity?' + new URLSearchParams(filters));
            const data = await response.json();

            if (response.ok) {
                this.updateCharts(data);
                this.updateTable(data.details);
            } else {
                toastr.error(data.message || 'Error loading productivity data');
            }
        } catch (error) {
            console.error('Error loading productivity data:', error);
            toastr.error('Error loading productivity data');
        }
    },

    updateCharts(data) {
        // Update Trend Chart
        this.charts.trend.data.labels = data.trend.labels;
        this.charts.trend.data.datasets[0].data = data.trend.values;
        this.charts.trend.update();

        // Update Team Chart
        this.charts.team.data.labels = data.team_comparison.labels;
        this.charts.team.data.datasets[0].data = data.team_comparison.values;
        this.charts.team.update();
    },

    updateTable(data) {
        this.table.clear();
        this.table.rows.add(data);
        this.table.draw();
    },

    async exportReport() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            project_id: $('#projectFilter').val(),
            format: 'excel'
        };

        try {
            const response = await fetch('/api/admin/reports/productivity/export?' + new URLSearchParams(filters));
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'productivity_report.xlsx';
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
    ProductivityReport.init();
}); 