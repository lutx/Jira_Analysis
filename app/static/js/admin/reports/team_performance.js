// Team Performance Report Management
const TeamPerformanceReport = {
    charts: {},
    table: null,

    init() {
        this.initializeCharts();
        this.initializeTable();
        this.bindEvents();
        this.loadData();
    },

    initializeCharts() {
        // Metric Chart
        this.charts.metric = new Chart(document.getElementById('metricChart'), {
            type: 'radar',
            data: {
                labels: ['Productivity', 'Quality', 'Delivery', 'Collaboration'],
                datasets: [{
                    label: 'Current Period',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)'
                },
                {
                    label: 'Previous Period',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20
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
                    label: 'Overall Score',
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
                        max: 100,
                        title: {
                            display: true,
                            text: 'Score (%)'
                        }
                    }
                }
            }
        });
    },

    initializeTable() {
        this.table = $('#performanceTable').DataTable({
            pageLength: 25,
            order: [[5, 'desc']],
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
            const response = await fetch('/api/admin/reports/team-performance?' + new URLSearchParams(filters));
            const data = await response.json();

            if (response.ok) {
                this.updateCharts(data);
                this.updateTable(data.details);
                this.updateSummary(data.summary);
            } else {
                toastr.error(data.message || 'Error loading team performance data');
            }
        } catch (error) {
            console.error('Error loading team performance data:', error);
            toastr.error('Error loading team performance data');
        }
    },

    updateCharts(data) {
        // Update Metric Chart
        this.charts.metric.data.datasets[0].data = [
            data.metrics.current.productivity,
            data.metrics.current.quality,
            data.metrics.current.delivery,
            data.metrics.current.collaboration
        ];
        this.charts.metric.data.datasets[1].data = [
            data.metrics.previous.productivity,
            data.metrics.previous.quality,
            data.metrics.previous.delivery,
            data.metrics.previous.collaboration
        ];
        this.charts.metric.update();

        // Update Team Chart
        this.charts.team.data.labels = data.team_comparison.labels;
        this.charts.team.data.datasets[0].data = data.team_comparison.scores;
        this.charts.team.update();
    },

    updateTable(data) {
        this.table.clear();
        this.table.rows.add(data);
        this.table.draw();
    },

    updateSummary(data) {
        $('#overallScore').text(data.overall_score.toFixed(1) + '%');
        $('#topTeam').text(data.top_team);
        $('#avgTeamSize').text(data.avg_team_size.toFixed(1));
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
            const response = await fetch('/api/admin/reports/team-performance/export?' + new URLSearchParams(filters));
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'team_performance_report.xlsx';
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
    TeamPerformanceReport.init();
}); 