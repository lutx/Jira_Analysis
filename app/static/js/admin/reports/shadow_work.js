// Shadow Work Report Management
const ShadowWorkReport = {
    charts: {},
    table: null,

    init() {
        this.initializeCharts();
        this.initializeTable();
        this.bindEvents();
        this.loadData();
    },

    initializeCharts() {
        // Shadow Distribution Chart
        this.charts.distribution = new Chart(document.getElementById('shadowDistribution'), {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgb(255, 99, 132)',
                        'rgb(54, 162, 235)',
                        'rgb(255, 205, 86)',
                        'rgb(75, 192, 192)',
                        'rgb(153, 102, 255)'
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

        // Shadow Trend Chart
        this.charts.trend = new Chart(document.getElementById('shadowTrend'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Shadow Hours',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: 'Regular Hours',
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
        this.table = $('#shadowTable').DataTable({
            pageLength: 25,
            order: [[0, 'desc']],
            dom: 'Bfrtip',
            buttons: [
                'copy', 'csv', 'excel', 'pdf'
            ],
            footerCallback: function(row, data, start, end, display) {
                const api = this.api();
                
                // Calculate total hours
                const totalHours = api
                    .column(4)
                    .data()
                    .reduce((a, b) => a + parseFloat(b), 0);
                
                // Calculate total cost
                const totalCost = api
                    .column(6)
                    .data()
                    .reduce((a, b) => a + this.parseCurrency(b), 0);
                
                $(api.column(4).footer()).html(totalHours.toFixed(2));
                $(api.column(6).footer()).html(this.formatCurrency(totalCost));
            }
        });
    },

    parseCurrency(value) {
        return parseFloat(value.replace(/[^\d.-]/g, ''));
    },

    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    },

    bindEvents() {
        $('#dateRange').on('change', this.loadData.bind(this));
        $('#teamFilter').on('change', this.loadData.bind(this));
        $('#categoryFilter').on('change', this.loadData.bind(this));
        $('#exportReport').on('click', this.exportReport.bind(this));
    },

    async loadData() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            category: $('#categoryFilter').val()
        };

        try {
            const response = await fetch('/api/admin/reports/shadow-work?' + new URLSearchParams(filters));
            const data = await response.json();

            if (response.ok) {
                this.updateCharts(data);
                this.updateTable(data.details);
                this.updateSummary(data.summary);
            } else {
                toastr.error(data.message || 'Error loading shadow work data');
            }
        } catch (error) {
            console.error('Error loading shadow work data:', error);
            toastr.error('Error loading shadow work data');
        }
    },

    updateCharts(data) {
        // Update Distribution Chart
        this.charts.distribution.data.labels = data.distribution.labels;
        this.charts.distribution.data.datasets[0].data = data.distribution.values;
        this.charts.distribution.update();

        // Update Trend Chart
        this.charts.trend.data.labels = data.trend.labels;
        this.charts.trend.data.datasets[0].data = data.trend.shadow_hours;
        this.charts.trend.data.datasets[1].data = data.trend.regular_hours;
        this.charts.trend.update();
    },

    updateTable(data) {
        this.table.clear();
        this.table.rows.add(data);
        this.table.draw();
    },

    updateSummary(data) {
        $('#totalShadowHours').text(data.total_shadow_hours.toFixed(2));
        $('#shadowWorkPercentage').text(data.shadow_work_percentage.toFixed(1) + '%');
        $('#commonCategory').text(data.most_common_category);
        $('#costImpact').text(this.formatCurrency(data.cost_impact));
    },

    async exportReport() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            category: $('#categoryFilter').val(),
            format: 'excel'
        };

        try {
            const response = await fetch('/api/admin/reports/shadow-work/export?' + new URLSearchParams(filters));
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'shadow_work_report.xlsx';
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
    ShadowWorkReport.init();
}); 