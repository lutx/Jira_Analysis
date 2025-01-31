document.addEventListener('DOMContentLoaded', function() {
    console.log('Application loaded successfully');
    loadCharts();
});

function loadCharts() {
    fetch('/get_active_users_trend')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            const ctx = document.getElementById('activityChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Aktywni użytkownicy',
                        data: data.counts,
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Trend aktywności użytkowników'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            },
                            title: {
                                display: true,
                                text: 'Liczba użytkowników'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Data'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error loading chart data:', error);
            const chartContainer = document.getElementById('activityChart').parentElement;
            chartContainer.innerHTML = `
                <div class="alert alert-danger">
                    Błąd podczas ładowania danych wykresu: ${error.message}
                </div>
            `;
        });
}
