// Utilization Report Management
const UtilizationReport = {
    charts: {},
    table: null,

    init() {
        this.initializeCharts();
        this.initializeTable();
        this.bindEvents();
        this.loadData();
    },

    initializeCharts() {
        // Utilization Trend Chart
        this.charts.trend = new Chart(document.getElementById('utilizationTrend'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Average Utilization',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: 'Target Utilization',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        borderDash: [5, 5],
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Utilization Rate (%)'
                        }
                    }
                }
            }
        });

        // Resource Distribution Chart
        this.charts.distribution = new Chart(document.getElementById('utilizationDistribution'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Resource Utilization',
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
                            text: 'Utilization Rate (%)'
                        }
                    }
                }
            }
        });
    },

    initializeTable() {
        this.table = $('#utilizationTable').DataTable({
            pageLength: 25,
            order: [[3, 'desc']],
            dom: 'Bfrtip',
            buttons: [
                'copy', 'csv', 'excel', 'pdf'
            ]
        });
    },

    bindEvents() {
        $('#dateRange').on('change', this.loadData.bind(this));
        $('#teamFilter').on('change', this.loadData.bind(this));
        $('#resourceType').on('change', this.loadData.bind(this));
        $('#exportReport').on('click', this.exportReport.bind(this));
    },

    async loadData() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            resource_type: $('#resourceType').val()
        };

        try {
            const response = await fetch('/api/admin/reports/utilization?' + new URLSearchParams(filters));
            const data = await response.json();

            if (response.ok) {
                this.updateCharts(data);
                this.updateTable(data.details);
                this.updateSummary(data.summary);
            } else {
                toastr.error(data.message || 'Error loading utilization data');
            }
        } catch (error) {
            console.error('Error loading utilization data:', error);
            toastr.error('Error loading utilization data');
        }
    },

    updateCharts(data) {
        // Update Trend Chart
        this.charts.trend.data.labels = data.trend.labels;
        this.charts.trend.data.datasets[0].data = data.trend.utilization;
        this.charts.trend.data.datasets[1].data = data.trend.target;
        this.charts.trend.update();

        // Update Distribution Chart
        this.charts.distribution.data.labels = data.distribution.labels;
        this.charts.distribution.data.datasets[0].data = data.distribution.values;
        this.charts.distribution.update();
    },

    updateTable(data) {
        this.table.clear();
        this.table.rows.add(data);
        this.table.draw();
    },

    updateSummary(data) {
        $('#avgUtilization').text(data.average + '%');
        $('#peakUtilization').text(data.peak + '%');
        $('#underutilizedCount').text(data.underutilized);
        $('#overutilizedCount').text(data.overutilized);
    },

    async exportReport() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            resource_type: $('#resourceType').val(),
            format: 'excel'
        };

        try {
            const response = await fetch('/api/admin/reports/utilization/export?' + new URLSearchParams(filters));
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'utilization_report.xlsx';
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
    UtilizationReport.init();
}); 