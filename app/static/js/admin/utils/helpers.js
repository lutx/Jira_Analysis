const AdminHelpers = {
    formatDate(date) {
        return moment(date).format('YYYY-MM-DD');
    },

    formatDateTime(date) {
        return moment(date).format('YYYY-MM-DD HH:mm:ss');
    },

    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    },

    showLoading() {
        $('#loadingModal').modal('show');
    },

    hideLoading() {
        $('#loadingModal').modal('hide');
    },

    showError(message) {
        toastr.error(message);
    },

    showSuccess(message) {
        toastr.success(message);
    }
}; 