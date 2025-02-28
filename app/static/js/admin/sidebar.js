$(document).ready(function() {
    // Toggle submenu
    $('.nav-link[data-bs-toggle="collapse"]').on('click', function() {
        $(this).toggleClass('active');
    });

    // Highlight active menu item based on current URL
    const currentPath = window.location.pathname;
    $('.nav-link').each(function() {
        const href = $(this).attr('href');
        if (href && currentPath.startsWith(href)) {
            $(this).addClass('active');
            $(this).parents('.collapse').addClass('show');
            $(this).parents('.nav-item').find('.nav-link[data-bs-toggle="collapse"]').addClass('active');
        }
    });

    // Toggle sidebar on mobile
    $('#sidebarToggle').on('click', function() {
        $('.sidebar').toggleClass('active');
        $('.content-wrapper').toggleClass('active');
    });
}); 