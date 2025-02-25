document.addEventListener('DOMContentLoaded', function() {
    // Funkcja do aktualizacji statystyk
    function updateStats() {
        fetch('/api/admin/stats')
            .then(response => response.json())
            .then(data => {
                // Aktualizuj statystyki na stronie
                Object.keys(data).forEach(key => {
                    const element = document.getElementById(`stat-${key}`);
                    if (element) {
                        element.textContent = data[key];
                    }
                });
            })
            .catch(error => console.error('Error updating stats:', error));
    }

    // Aktualizuj co 30 sekund
    setInterval(updateStats, 30000);

    // Przykład inicjalizacji wykresu
    const ctx = document.getElementById('myChart').getContext('2d');
    const myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Red', 'Blue', 'Yellow', 'Green', 'Purple', 'Orange'],
            datasets: [{
                label: '# of Votes',
                data: [12, 19, 3, 5, 2, 3],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}); 