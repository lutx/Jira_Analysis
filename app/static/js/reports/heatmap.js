document.addEventListener('DOMContentLoaded', function() {
    initializeDatePickers();
    loadUsers();
    loadHeatmap();
});

function initializeDatePickers() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    document.getElementById('startDate').valueAsDate = thirtyDaysAgo;
    document.getElementById('endDate').valueAsDate = today;
}

async function loadUsers() {
    try {
        const response = await fetch('/api/users');
        const users = await response.json();
        
        const userSelect = document.getElementById('userSelect');
        users.forEach(user => {
            userSelect.add(new Option(user.display_name || user.user_name, user.user_name));
        });
        
        userSelect.addEventListener('change', loadHeatmap);
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Błąd podczas ładowania użytkowników');
    }
}

async function loadHeatmap() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const user = document.getElementById('userSelect').value;
        
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });
        if (user) params.append('user', user);
        
        const response = await fetch(`/api/reports/heatmap?${params}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas generowania heatmapy');
        }
        
        renderHeatmap(data);
        
    } catch (error) {
        console.error('Error loading heatmap:', error);
        showError(error.message);
    }
}

function renderHeatmap(data) {
    // Usuń poprzednią heatmapę
    d3.select('#heatmap').selectAll('*').remove();
    
    const margin = { top: 20, right: 30, bottom: 30, left: 60 };
    const width = 800 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;
    
    const days = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela'];
    const hours = Array.from({length: 24}, (_, i) => i);
    
    const cellWidth = width / 24;
    const cellHeight = height / 7;
    
    // Skala kolorów
    const colorScale = d3.scaleSequential()
        .domain([0, d3.max(data.data.flat())])
        .interpolator(d3.interpolateYlOrRd);
    
    // Utworzenie SVG
    const svg = d3.select('#heatmap')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Dodanie etykiet dni
    svg.selectAll('.dayLabel')
        .data(days)
        .enter()
        .append('text')
        .attr('class', 'dayLabel')
        .attr('x', -10)
        .attr('y', (d, i) => i * cellHeight + cellHeight / 2)
        .style('text-anchor', 'end')
        .style('dominant-baseline', 'middle')
        .text(d => d);
    
    // Dodanie etykiet godzin
    svg.selectAll('.hourLabel')
        .data(hours)
        .enter()
        .append('text')
        .attr('class', 'hourLabel')
        .attr('x', (d, i) => i * cellWidth + cellWidth / 2)
        .attr('y', -5)
        .style('text-anchor', 'middle')
        .text(d => `${d}:00`);
    
    // Utworzenie tooltipa
    const tooltip = d3.select('body')
        .append('div')
        .attr('class', 'tooltip')
        .style('opacity', 0);
    
    // Dodanie komórek heatmapy
    svg.selectAll('.hour')
        .data(data.data)
        .enter()
        .append('g')
        .attr('class', 'hour')
        .attr('transform', (d, i) => `translate(0,${i * cellHeight})`)
        .selectAll('.cell')
        .data(d => d)
        .enter()
        .append('rect')
        .attr('class', 'heatmap-cell')
        .attr('x', (d, i) => i * cellWidth)
        .attr('width', cellWidth)
        .attr('height', cellHeight)
        .style('fill', d => colorScale(d))
        .on('mouseover', function(event, d) {
            const [x, y] = d3.pointer(event);
            tooltip.transition()
                .duration(200)
                .style('opacity', .9);
            tooltip.html(`Liczba godzin: ${d.toFixed(1)}`)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        });
    
    // Dodanie legendy
    const legendData = d3.range(0, d3.max(data.data.flat()), d3.max(data.data.flat()) / 5);
    
    const legend = d3.select('#legend');
    legend.selectAll('*').remove();
    
    legendData.forEach(d => {
        legend.append('div')
            .attr('class', 'legend-cell')
            .style('background-color', colorScale(d));
    });
}

function showError(message) {
    // Implementacja wyświetlania błędu
    alert(message);
} 