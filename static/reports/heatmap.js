document.addEventListener('DOMContentLoaded', function() {
    const margin = { top: 20, right: 30, bottom: 30, left: 40 };
    const width = 960 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    fetch('/api/reports/heatmap')
        .then(response => response.json())
        .then(data => {
            const svg = d3.select('#heatmapContainer')
                .append('svg')
                .attr('width', width + margin.left + margin.right)
                .attr('height', height + margin.top + margin.bottom)
                .append('g')
                .attr('transform', `translate(${margin.left},${margin.top})`);

            const x = d3.scaleBand()
                .range([0, width])
                .domain(data.hours)
                .padding(0.01);

            const y = d3.scaleBand()
                .range([height, 0])
                .domain(data.days)
                .padding(0.01);

            const colorScale = d3.scaleSequential()
                .interpolator(d3.interpolateYlOrRd)
                .domain([0, d3.max(data.data.flat())]);

            // Add X axis
            svg.append('g')
                .attr('transform', `translate(0,${height})`)
                .call(d3.axisBottom(x));

            // Add Y axis
            svg.append('g')
                .call(d3.axisLeft(y));

            // Create heatmap cells
            data.days.forEach((day, i) => {
                data.hours.forEach((hour, j) => {
                    svg.append('rect')
                        .attr('x', x(hour))
                        .attr('y', y(day))
                        .attr('width', x.bandwidth())
                        .attr('height', y.bandwidth())
                        .style('fill', colorScale(data.data[i][j]))
                        .append('title')
                        .text(`${day} ${hour}:00 - Count: ${data.data[i][j]}`);
                });
            });
        });
}); 