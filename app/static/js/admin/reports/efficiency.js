// Efficiency Report Management
const EfficiencyReport = {
    charts: {},
    table: null,

    init() {
        this.initializeCharts();
        this.initializeTable();
        this.bindEvents();
        this.loadData();
    },

    initializeCharts() {
        // Efficiency Trend Chart
        this.charts.trend = new Chart(document.getElementById('efficiencyTrend'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Time Efficiency',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: 'Cost Efficiency',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    },
                    {
                        label: 'Resource Efficiency',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
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
                            text: 'Efficiency Score (%)'
                        }
                    }
                }
            }
        });

        // Team Comparison Chart
        this.charts.team = new Chart(document.getElementById('teamComparison'), {
            type: 'radar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Team Efficiency',
                    data: [],
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgb(75, 192, 192)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    },

    initializeTable() {
        this.table = $('#efficiencyTable').DataTable({
            pageLength: 25,
            order: [[4, 'desc']],
            dom: 'Bfrtip',
            buttons: [
                'copy', 'csv', 'excel', 'pdf'
            ]
        });
    },

    bindEvents() {
        $('#dateRange').on('change', this.loadData.bind(this));
        $('#teamFilter').on('change', this.loadData.bind(this));
        $('#metricFilter').on('change', this.loadData.bind(this));
        $('#exportReport').on('click', this.exportReport.bind(this));
    },

    async loadData() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            metric: $('#metricFilter').val()
        };

        try {
            const response = await fetch('/api/admin/reports/efficiency?' + new URLSearchParams(filters));
            const data = await response.json();

            if (response.ok) {
                this.updateCharts(data);
                this.updateTable(data.details);
                this.updateSummary(data.summary);
            } else {
                toastr.error(data.message || 'Error loading efficiency data');
            }
        } catch (error) {
            console.error('Error loading efficiency data:', error);
            toastr.error('Error loading efficiency data');
        }
    },

    updateCharts(data) {
        // Update Trend Chart
        this.charts.trend.data.labels = data.trend.labels;
        data.trend.datasets.forEach((dataset, index) => {
            this.charts.trend.data.datasets[index].data = dataset.values;
        });
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

    updateSummary(data) {
        $('#avgEfficiency').text(data.average + '%');
        $('#topPerformer').text(data.top_performer);
        $('#improvementAreas').text(data.improvement_areas);
    },

    async exportReport() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            metric: $('#metricFilter').val(),
            format: 'excel'
        };

        try {
            const response = await fetch('/api/admin/reports/efficiency/export?' + new URLSearchParams(filters));
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'efficiency_report.xlsx';
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
    EfficiencyReport.init();
}); 