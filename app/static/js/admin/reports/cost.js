// Cost Report Management
const CostReport = {
    charts: {},
    table: null,

    init() {
        this.initializeCharts();
        this.initializeTable();
        this.bindEvents();
        this.loadData();
    },

    initializeCharts() {
        // Cost Trend Chart
        this.charts.trend = new Chart(document.getElementById('costTrend'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Total Cost',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    },
                    {
                        label: 'Revenue',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: 'Profit',
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
                            text: 'Amount ($)'
                        }
                    }
                }
            }
        });

        // Cost Distribution Chart
        this.charts.distribution = new Chart(document.getElementById('costDistribution'), {
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
    },

    initializeTable() {
        this.table = $('#costTable').DataTable({
            pageLength: 25,
            order: [[3, 'desc']],
            dom: 'Bfrtip',
            buttons: [
                'copy', 'csv', 'excel', 'pdf'
            ],
            footerCallback: function(row, data, start, end, display) {
                const api = this.api();
                const total = api
                    .column(3)
                    .data()
                    .reduce((a, b) => a + this.parseCurrency(b), 0);
                
                $(api.column(3).footer()).html(this.formatCurrency(total));
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
        $('#costType').on('change', this.loadData.bind(this));
        $('#exportReport').on('click', this.exportReport.bind(this));
    },

    async loadData() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            cost_type: $('#costType').val()
        };

        try {
            const response = await fetch('/api/admin/reports/cost?' + new URLSearchParams(filters));
            const data = await response.json();

            if (response.ok) {
                this.updateCharts(data);
                this.updateTable(data.details);
                this.updateSummary(data.summary);
            } else {
                toastr.error(data.message || 'Error loading cost data');
            }
        } catch (error) {
            console.error('Error loading cost data:', error);
            toastr.error('Error loading cost data');
        }
    },

    updateCharts(data) {
        // Update Trend Chart
        this.charts.trend.data.labels = data.trend.labels;
        this.charts.trend.data.datasets[0].data = data.trend.costs;
        this.charts.trend.data.datasets[1].data = data.trend.revenue;
        this.charts.trend.data.datasets[2].data = data.trend.profit;
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
        $('#totalCost').text(this.formatCurrency(data.total_cost));
        $('#totalRevenue').text(this.formatCurrency(data.total_revenue));
        $('#profitMargin').text(data.profit_margin + '%');
        $('#costPerResource').text(this.formatCurrency(data.cost_per_resource));
    },

    async exportReport() {
        const filters = {
            date_range: $('#dateRange').val(),
            team_id: $('#teamFilter').val(),
            cost_type: $('#costType').val(),
            format: 'excel'
        };

        try {
            const response = await fetch('/api/admin/reports/cost/export?' + new URLSearchParams(filters));
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'cost_report.xlsx';
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
    CostReport.init();
}); 