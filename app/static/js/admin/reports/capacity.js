// Capacity Report Management
const CapacityReport = {
    charts: {},
    table: null,

    init() {
        this.initializeCharts();
        this.initializeTable();
        this.bindEvents();
        this.loadData();
    },

    initializeCharts() {
        // Capacity Trend Chart
        this.charts.trend = new Chart(document.getElementById('capacityTrend'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Total Capacity',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1
                    },
                    {
                        label: 'Allocated Capacity',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    },
                    {
                        label: 'Available Capacity',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
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

        // Resource Distribution Chart
        this.charts.distribution = new Chart(document.getElementById('resourceDistribution'), {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgb(54, 162, 235)',
                        'rgb(255, 99, 132)',
                        'rgb(75, 192, 192)',
                        'rgb(255, 205, 86)'
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
    },

    initializeTable() {
        this.table = $('#capacityTable').DataTable({
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
        $('#viewType').on('change', this.loadData.bind(this));
        $('#exportReport').on('click', this.exportReport.bind(this));
    },

    async loadData() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            view_type: $('#viewType').val()
        };

        try {
            const response = await fetch('/api/admin/reports/capacity?' + new URLSearchParams(filters));
            const data = await response.json();

            if (response.ok) {
                this.updateCharts(data);
                this.updateTable(data.details);
                this.updateSummary(data.summary);
            } else {
                toastr.error(data.message || 'Error loading capacity data');
            }
        } catch (error) {
            console.error('Error loading capacity data:', error);
            toastr.error('Error loading capacity data');
        }
    },

    updateCharts(data) {
        // Update Trend Chart
        this.charts.trend.data.labels = data.trend.labels;
        data.trend.datasets.forEach((dataset, index) => {
            this.charts.trend.data.datasets[index].data = dataset.values;
        });
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
        $('#totalCapacity').text(data.total_capacity + ' hours');
        $('#availableCapacity').text(data.available_capacity + ' hours');
        $('#utilizationRate').text(data.utilization_rate + '%');
        $('#resourceCount').text(data.resource_count);
    },

    async exportReport() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            view_type: $('#viewType').val(),
            format: 'excel'
        };

        try {
            const response = await fetch('/api/admin/reports/capacity/export?' + new URLSearchParams(filters));
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'capacity_report.xlsx';
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
    CapacityReport.init();
}); 