document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const leaveTable = $('#leaveTable').DataTable({
        pageLength: 25,
        order: [[2, 'desc']]  // Sort by start date
    });
    
    // Initialize DateRangePicker
    $('.daterange').daterangepicker({
        opens: 'left',
        locale: {
            format: 'YYYY-MM-DD'
        },
        ranges: {
            'Next 7 Days': [moment(), moment().add(6, 'days')],
            'Next 30 Days': [moment(), moment().add(29, 'days')],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Next Month': [moment().add(1, 'month').startOf('month'), moment().add(1, 'month').endOf('month')]
        }
    });
    
    // Handle filter form submit
    $('#leaveFilters').on('submit', function(e) {
        e.preventDefault();
        updateLeaveData();
    });
});

function updateLeaveData() {
    const filters = {
        status: $('[name=status]').val(),
        date_range: $('[name=date_range]').val(),
        user_id: $('[name=user_id]').val()
    };
    
    fetch('/admin/leave-management/data?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            updateTable(data.leave_requests);
        })
        .catch(error => {
            console.error('Error updating leave data:', error);
            showNotification('Error updating leave data', 'error');
        });
}

function updateTable(requests) {
    const table = $('#leaveTable').DataTable();
    table.clear();
    
    requests.forEach(request => {
        table.row.add([
            request.user.display_name,
            request.type,
            request.start_date,
            request.end_date,
            request.days,
            `<span class="badge bg-${request.status_class}">${request.status}</span>`,
            generateActionButtons(request)
        ]);
    });
    
    table.draw();
}

function generateActionButtons(request) {
    let buttons = '';
    
    if (request.status === 'pending') {
        buttons += `
            <button class="btn btn-sm btn-success" onclick="approveLeave(${request.id})">
                <i class="bi bi-check"></i>
            </button>
            <button class="btn btn-sm btn-danger" onclick="rejectLeave(${request.id})">
                <i class="bi bi-x"></i>
            </button>
        `;
    }
    
    buttons += `
        <button class="btn btn-sm btn-info" onclick="viewLeaveDetails(${request.id})">
            <i class="bi bi-eye"></i>
        </button>
    `;
    
    return `<div class="btn-group btn-group-sm">${buttons}</div>`;
}

function approveLeave(leaveId) {
    updateLeaveStatus(leaveId, 'approved');
}

function rejectLeave(leaveId) {
    updateLeaveStatus(leaveId, 'rejected');
}

function updateLeaveStatus(leaveId, status) {
    fetch(`/admin/leave-management/${leaveId}/status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ status })
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification(`Leave request ${status} successfully`, 'success');
            updateLeaveData();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error updating leave status:', error);
        showNotification('Error updating leave status', 'error');
    });
}

function viewLeaveDetails(leaveId) {
    fetch(`/admin/leave-management/${leaveId}`)
        .then(response => response.json())
        .then(leave => {
            Swal.fire({
                title: 'Leave Request Details',
                html: `
                    <div class="text-start">
                        <p><strong>Employee:</strong> ${leave.user.display_name}</p>
                        <p><strong>Type:</strong> ${leave.type}</p>
                        <p><strong>From:</strong> ${leave.start_date}</p>
                        <p><strong>To:</strong> ${leave.end_date}</p>
                        <p><strong>Days:</strong> ${leave.days}</p>
                        <p><strong>Status:</strong> 
                            <span class="badge bg-${leave.status_class}">${leave.status}</span>
                        </p>
                        ${leave.approver ? 
                            `<p><strong>Approved/Rejected by:</strong> ${leave.approver.display_name}</p>` : 
                            ''}
                    </div>
                `,
                icon: 'info'
            });
        })
        .catch(error => {
            console.error('Error loading leave details:', error);
            showNotification('Error loading leave details', 'error');
        });
} 