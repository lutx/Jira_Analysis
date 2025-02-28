document.addEventListener('DOMContentLoaded', function() {
    console.log('Workload JS loaded at', new Date().toISOString());
    
    // Store original project options for filtering
    let originalProjectOptions = [];
    
    // Initialize components and event handlers
    initialize();
    
    // Main initialization function
    function initialize() {
        try {
            // Debug DOM elements
            debugCheckElements();
            
            // Store original project options
            storeOriginalProjectOptions();
            
            // Initialize DateRangePicker
            initializeDateRangePicker();
            
            // Add project selection buttons
            addProjectSelectionButtons();
            
            // Initialize charts with empty data
            initializeCharts();
            
            // Set up event listeners
            setupEventListeners();
            
            // Initial update of filters display
            updateCurrentFilters();
            
            console.log('Workload page fully initialized');
        } catch (error) {
            console.error('Error during initialization:', error);
            showNotification('Error initializing workload page: ' + error.message, 'danger');
        }
    }
    
    // Function to store original project options
    function storeOriginalProjectOptions() {
        originalProjectOptions = [];
        
        $('#project-select option').each(function() {
            const option = $(this);
            originalProjectOptions.push({
                value: option.val(),
                text: option.text(),
                teamIds: option.data('team-ids') ? option.data('team-ids').toString().split(',') : []
            });
        });
        
        console.log('Stored original project options:', originalProjectOptions.length);
    }
    
    // Function to initialize date range picker
    function initializeDateRangePicker() {
        console.log('Initializing DateRangePicker');
        
        // First check if DateRangePicker element exists
        const datePickerElement = document.getElementById('date-range-picker');
        if (!datePickerElement) {
            console.error('Date picker element not found with ID #date-range-picker');
            return;
        }
        
        const datePickerInput = $(datePickerElement);
        
        try {
            // Check if DateRangePicker is already initialized
            if (datePickerInput.data('daterangepicker')) {
                console.log('DateRangePicker already initialized');
                return;
            }
            
            const defaultStart = moment().subtract(29, 'days');
            const defaultEnd = moment();
            
            datePickerInput.daterangepicker({
                startDate: defaultStart,
                endDate: defaultEnd,
                ranges: {
                    'Last 7 Days': [moment().subtract(6, 'days'), moment()],
                    'Last 30 Days': [moment().subtract(29, 'days'), moment()],
                    'This Month': [moment().startOf('month'), moment().endOf('month')],
                    'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')],
                    'Last Quarter': [moment().subtract(3, 'month').startOf('month'), moment()],
                    'Year to Date': [moment().startOf('year'), moment()]
                },
                opens: 'right',
                autoUpdateInput: true,
                alwaysShowCalendars: true,
                locale: {
                    format: 'YYYY-MM-DD'
                }
            });
            
            // Set initial value
            const initialRange = defaultStart.format('YYYY-MM-DD') + ' - ' + defaultEnd.format('YYYY-MM-DD');
            datePickerInput.val(initialRange);
            
            // Update report period badge when date range changes
            datePickerInput.on('apply.daterangepicker', function(ev, picker) {
                const formattedDates = picker.startDate.format('YYYY-MM-DD') + ' - ' + picker.endDate.format('YYYY-MM-DD');
                $(this).val(formattedDates);
                updateReportPeriod(formattedDates);
                updateCurrentFilters();
            });
            
            console.log('DateRangePicker initialized successfully with range:', initialRange);
            updateReportPeriod(initialRange);
        } catch (error) {
            console.error('Error initializing DateRangePicker:', error);
            showNotification('Error initializing date picker. Please try refreshing the page.', 'danger');
        }
    }
    
    // Function to add project selection buttons
    function addProjectSelectionButtons() {
        const projectSelect = $('#project-select');
        if (projectSelect.length === 0) {
            console.error('Project select not found');
            return;
        }
        
        // Add buttons after the select element
        const projectSelectContainer = projectSelect.parent();
        
        // Check if buttons already exist
        if (projectSelectContainer.find('#select-all-projects').length > 0) {
            console.log('Project selection buttons already exist');
            return;
        }
        
        const buttonsHtml = `
            <div class="d-flex justify-content-between mt-2">
                <button type="button" class="btn btn-sm btn-outline-secondary" id="select-all-projects">
                    <i class="bi bi-check-all"></i> Select All
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" id="clear-project-selection">
                    <i class="bi bi-x-lg"></i> Clear Selection
                </button>
            </div>
        `;
        
        projectSelectContainer.append(buttonsHtml);
        
        // Add click handlers for the buttons
        $('#select-all-projects').on('click', function(e) {
            e.preventDefault();
            $('#project-select option').prop('selected', true);
            updateCurrentFilters();
        });
        
        $('#clear-project-selection').on('click', function(e) {
            e.preventDefault();
            $('#project-select option').prop('selected', false);
            updateCurrentFilters();
        });
        
        console.log('Project selection buttons added');
    }
    
    // Function to set up event listeners
    function setupEventListeners() {
        console.log('Setting up event listeners');
        
        // Handle form submission
        $('#workloadFilters').on('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = getFormData();
            
            // Validate form data
            if (!formData.date_range) {
                showNotification('Please select a date range', 'warning');
                return;
            }
            
            // Update UI for loading state
            showLoadingState();
            
            // Update filters display
            updateCurrentFilters();
            
            // Make API request
            updateWorkloadData(formData);
        });
        
        // Handle team selection change - filter projects
        $('#team-select').on('change', function() {
            const teamId = $(this).val();
            console.log('Team selection changed to:', teamId);
            
            if (teamId) {
                filterProjectsByTeam(teamId);
            } else {
                // Reset to show all projects
                resetProjectsDropdown();
            }
            
            updateCurrentFilters();
        });
        
        // Update current filters when any filter changes
        $('#workloadFilters select, #workloadFilters input').on('change', function() {
            updateCurrentFilters();
        });
        
        console.log('Event listeners set up successfully');
    }
    
    // Function to reset projects dropdown to show all projects
    function resetProjectsDropdown() {
        console.log('Resetting projects dropdown to show all projects');
        const projectSelect = $('#project-select');
        
        // Clear current options
        projectSelect.empty();
        
        // Add back all original options
        originalProjectOptions.forEach(function(option) {
            projectSelect.append(new Option(option.text, option.value));
        });
        
        // Make sure multiple property is set
        projectSelect.prop('multiple', true);
        
        console.log('Projects dropdown reset completed');
    }
    
    // Function to filter projects by selected team
    function filterProjectsByTeam(teamId) {
        console.log('Filtering projects for team:', teamId);
        
        const projectSelect = $('#project-select');
        
        // Show loading indicator
        const loadingSpinner = $('<div class="spinner-border spinner-border-sm text-primary position-absolute" style="right: 30px; top: 38px;"></div>');
        projectSelect.parent().append(loadingSpinner);
        
        // Disable select while loading
        projectSelect.prop('disabled', true);
        
        // Clear current selection
        projectSelect.empty();
        projectSelect.append(new Option('Loading projects...', ''));
        
        // Headers for JSON request
        const headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        };
        
        // Fetch team details to get assigned projects
        fetch(`/admin/teams/${teamId}`, {
            method: 'GET',
            headers: headers
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch team details (${response.status}: ${response.statusText})`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Team data received:', data);
                
                // Clear current options
                projectSelect.empty();
                
                // Check if there are projects in the response
                let teamProjects = [];
                
                // Handle different API response formats
                if (data.projects && Array.isArray(data.projects)) {
                    teamProjects = data.projects;
                    console.log(`Found ${teamProjects.length} projects in data.projects`);
                } else if (data.team && data.team.projects && Array.isArray(data.team.projects)) {
                    teamProjects = data.team.projects;
                    console.log(`Found ${teamProjects.length} projects in data.team.projects`);
                } else if (data.assigned_projects && Array.isArray(data.assigned_projects)) {
                    teamProjects = data.assigned_projects;
                    console.log(`Found ${teamProjects.length} projects in data.assigned_projects`);
                } else {
                    console.warn('No projects array found in API response:', data);
                    teamProjects = [];
                }
                
                if (teamProjects.length === 0) {
                    console.log('No projects found for team');
                    projectSelect.append(new Option('No projects available', ''));
                    showNotification('This team has no assigned projects.', 'warning');
                } else {
                    console.log(`Found ${teamProjects.length} projects for team`);
                    
                    // Add all option
                    projectSelect.append(new Option('All Team Projects', ''));
                    
                    // Add team projects
                    teamProjects.forEach(project => {
                        projectSelect.append(new Option(project.name, project.id));
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching team projects:', error);
                
                // Fallback to client-side filtering using data attributes
                console.log('Falling back to client-side filtering');
                
                // Clear current options
                projectSelect.empty();
                
                // Add all option
                projectSelect.append(new Option('All Team Projects', ''));
                
                // Filter projects by team ID using the data-team-ids attribute
                const teamProjects = originalProjectOptions.filter(option => {
                    if (!option.value) return false; // Skip empty value
                    
                    // Check if this project has the team ID in its teamIds array
                    return option.teamIds.includes(teamId.toString());
                });
                
                if (teamProjects.length === 0) {
                    console.log('No projects found for team (client filtering)');
                    projectSelect.append(new Option('No projects available', ''));
                } else {
                    console.log(`Found ${teamProjects.length} projects for team (client filtering)`);
                    
                    // Add team projects
                    teamProjects.forEach(option => {
                        projectSelect.append(new Option(option.text, option.value));
                    });
                }
                
                showNotification('Error loading team projects. Showing available projects based on local data.', 'warning');
            })
            .finally(() => {
                // Remove loading indicator
                loadingSpinner.remove();
                
                // Re-enable select
                projectSelect.prop('disabled', false);
                
                // Make sure multiple property is set
                projectSelect.prop('multiple', true);
            });
    }
    
    // Function to get form data
    function getFormData() {
        const teamId = $('#team-select').val();
        
        // Get selected project IDs (multiple selection)
        const projectIds = [];
        $('#project-select option:selected').each(function() {
            const val = $(this).val();
            if (val) projectIds.push(val);
        });
        
        // Get date range
        const dateRange = $('#date-range-picker').val();
        
        console.log('Form data collected:', {
            team_id: teamId,
            project_ids: projectIds,
            date_range: dateRange
        });
        
        return {
            team_id: teamId,
            project_ids: projectIds,
            date_range: dateRange
        };
    }
    
    // Function to update workload data
    function updateWorkloadData(formData) {
        console.log('Updating workload data with filters:', formData);
        
        // Build URL with parameters
        let url = '/admin/reports/workload/data?';
        
        if (formData.team_id) {
            url += `team_id=${formData.team_id}&`;
        }
        
        // Handle multiple project IDs
        if (formData.project_ids && formData.project_ids.length > 0) {
            formData.project_ids.forEach(projectId => {
                url += `project_ids[]=${projectId}&`;
            });
        }
        
        if (formData.date_range) {
            url += `date_range=${encodeURIComponent(formData.date_range)}`;
        }
        
        console.log('Fetching workload data from URL:', url);
        
        // Make AJAX request to get data
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Network response was not ok (${response.status}: ${response.statusText})`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Workload data received:', data);
                
                if (data.status === 'error') {
                    throw new Error(data.message || 'Unknown error occurred');
                }
                
                // Extract workload data
                const teamWorkloadData = {
                    labels: data.team_workload ? data.team_workload.labels : [],
                    values: data.team_workload ? data.team_workload.datasets[0].data : [],
                    colors: data.team_workload ? data.team_workload.datasets[0].backgroundColor : []
                };
                
                const userWorkloadData = {
                    labels: data.user_workload ? data.user_workload.labels : [],
                    values: data.user_workload ? data.user_workload.datasets[0].data : [],
                    colors: data.user_workload ? data.user_workload.datasets[0].backgroundColor : []
                };
                
                // Update team workload chart
                updateChart('team-workload-chart', teamWorkloadData, 'Team Workload Distribution');
                
                // Update user workload chart
                updateChart('user-workload-chart', userWorkloadData, 'User Workload Distribution');
                
                // Update table
                updateWorkloadTable(data.detailed_stats || []);
                
                // Update report period
                if (data.date_info) {
                    updateReportPeriod(`${data.date_info.start_date} - ${data.date_info.end_date}`);
                }
                
                showNotification('Workload data updated successfully', 'success');
                hideLoadingState();
            })
            .catch(error => {
                console.error('Error fetching workload data:', error);
                showNotification(`Error loading workload data: ${error.message}`, 'danger');
                hideLoadingState();
                
                // Clear charts and table
                updateChart('team-workload-chart', { labels: [], values: [], colors: [] }, 'Team Workload Distribution');
                updateChart('user-workload-chart', { labels: [], values: [], colors: [] }, 'User Workload Distribution');
                updateWorkloadTable([]);
            });
    }
    
    // Function to update workload table
    function updateWorkloadTable(data) {
        const tableBody = $('#workloadTable tbody');
        
        // Clear existing rows
        tableBody.empty();
        
        if (!data || data.length === 0) {
            tableBody.html('<tr><td colspan="5" class="text-center">No data available for the selected filters</td></tr>');
            return;
        }
        
        // Add rows for each item
        data.forEach(item => {
            const utilizationValue = item.utilization || 0;
            const utilizationPercent = (utilizationValue * 100).toFixed(0);
            const utilizationClass = getUtilizationClass(utilizationValue);
            const progressWidth = Math.min(100, utilizationPercent); // Ograniczamy szerokość paska do 100%
            
            // Dodajemy specjalny styl dla wartości powyżej 100%
            const utilizationStyle = utilizationValue > 1 
                ? 'font-weight: bold; color: #d4380d;' 
                : '';
            
            const row = `
                <tr>
                    <td class="fw-bold fs-5">${item.name || 'Unknown'}</td>
                    <td class="text-center fs-5">${(item.total_hours || 0).toFixed(1)}</td>
                    <td class="text-center fs-5">${item.projects_count || item.project_count || 0}</td>
                    <td class="text-center fs-5">${(item.avg_daily_hours || 0).toFixed(1)}</td>
                    <td>
                        <div class="progress" style="height: 25px;" data-bs-toggle="tooltip" 
                             title="${utilizationPercent}% wykorzystania (${(item.avg_daily_hours || 0).toFixed(1)} godz. średnio dziennie)">
                            <div class="progress-bar ${utilizationClass}" 
                                 style="width: ${progressWidth}%">
                                <span style="${utilizationStyle}">${utilizationPercent}%</span>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
            
            tableBody.append(row);
        });
        
        // Initialize tooltips after adding rows
        try {
            $('[data-bs-toggle="tooltip"]').tooltip();
        } catch (error) {
            console.warn("Could not initialize tooltips:", error);
        }
    }
    
    // Function to update chart
    function updateChart(chartId, data, title) {
        console.log(`Updating chart ${chartId} with ${data ? data.labels.length : 0} data points`);
        
        // Get the canvas element
        const canvas = document.getElementById(chartId);
        if (!canvas) {
            console.error(`Canvas element not found: ${chartId}`);
            return;
        }
        
        // Destroy existing chart if it exists
        const chartInstance = Chart.getChart(canvas);
        if (chartInstance) {
            chartInstance.destroy();
        }
        
        if (!data || !data.labels || data.labels.length === 0) {
            console.log(`No data available for chart: ${chartId}`);
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No data available for the selected filters', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // Generate colors if none provided
        if (!data.colors || data.colors.length === 0) {
            data.colors = generateColors(data.labels.length);
        }
        
        // Create the chart
        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: data.colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 15,
                            padding: 15
                        }
                    },
                    title: {
                        display: true,
                        text: title,
                        padding: {
                            top: 10,
                            bottom: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value.toFixed(1)} hours (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Function to initialize charts with empty data
    function initializeCharts() {
        console.log('Initializing charts with empty data');
        try {
            // Initialize team workload chart
            updateChart('team-workload-chart', {
                labels: [],
                values: [],
                colors: []
            }, 'Team Workload Distribution');
            
            // Initialize user workload chart
            updateChart('user-workload-chart', {
                labels: [],
                values: [],
                colors: []
            }, 'User Workload Distribution');
            
            console.log('Charts initialized successfully');
        } catch (error) {
            console.error('Error initializing charts:', error);
            showNotification('Error initializing charts. Some visualizations may not display correctly.', 'warning');
        }
    }
    
    // Function to generate colors for chart
    function generateColors(count) {
        const colors = [];
        const baseColors = [
            '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
            '#5a5c69', '#858796', '#6610f2', '#fd7e14', '#20c9a6'
        ];
        
        for (let i = 0; i < count; i++) {
            colors.push(baseColors[i % baseColors.length]);
        }
        
        return colors;
    }
    
    // Function to get utilization class based on value
    function getUtilizationClass(utilization) {
        if (utilization < 0.5) return 'bg-danger';
        if (utilization < 0.75) return 'bg-warning';
        if (utilization < 0.9) return 'bg-info';
        return 'bg-success';
    }
    
    // Function to show loading state
    function showLoadingState() {
        // Add loading overlay
        $('body').append('<div class="loading-overlay"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>');
    }
    
    // Function to hide loading state
    function hideLoadingState() {
        // Remove loading overlay
        $('.loading-overlay').remove();
    }
    
    // Function to show notification
    function showNotification(message, type = 'info') {
        const notification = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        $('.notifications-container').append(notification);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            $('.alert').alert('close');
        }, 5000);
    }
    
    // Function to update report period
    function updateReportPeriod(dateRange) {
        const reportPeriod = document.getElementById('reportPeriod');
        if (reportPeriod && dateRange) {
            reportPeriod.textContent = dateRange;
        }
    }
    
    // Function to update current filters display
    function updateCurrentFilters() {
        const teamName = $('#team-select option:selected').text() || 'All Teams';
        const dateRange = $('#date-range-picker').val() || 'Last 30 days';
        
        let projectsText = 'All Projects';
        const selectedProjects = $('#project-select option:selected');
        if (selectedProjects.length > 0 && selectedProjects.val()) {
            if (selectedProjects.length == 1) {
                projectsText = selectedProjects.text();
            } else {
                projectsText = selectedProjects.length + ' selected projects';
            }
        }
        
        $('#currentFilters').html(`<strong>Team:</strong> ${teamName} | <strong>Projects:</strong> ${projectsText} | <strong>Date:</strong> ${dateRange}`);
    }
    
    // Function to check if DOM elements exist (for debugging)
    function debugCheckElements() {
        console.log('Checking DOM elements:');
        console.log('- Team select exists:', $('#team-select').length > 0);
        console.log('- Project select exists:', $('#project-select').length > 0);
        console.log('- Date range picker exists:', $('#date-range-picker').length > 0);
        console.log('- Team chart exists:', $('#team-workload-chart').length > 0);
        console.log('- User chart exists:', $('#user-workload-chart').length > 0);
        console.log('- Form exists:', $('#workloadFilters').length > 0);
        console.log('- Report period element exists:', $('#reportPeriod').length > 0);
    }
}); 