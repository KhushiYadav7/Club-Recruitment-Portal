// Main JavaScript for Recruitment Portal

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeAlerts();
    initializeConfirmDialogs();
    initializeFormValidation();
    initializePasswordStrength();
    initializeTooltips();
    initializeTableSearch();
    initializeAnimations();
    initializeFormLoading();
    initializeDropdowns();
    
    // Start slot refresh if on slots page
    if (window.location.pathname.includes('/slots')) {
        startSlotRefresh();
    }
});

// ============================================
// NAVBAR DROPDOWN & MOBILE MENU
// ============================================
function toggleMobileMenu() {
    const menu = document.getElementById('navbarMenu');
    if (menu) {
        menu.classList.toggle('open');
    }
}

function toggleUserMenu() {
    const dropdown = document.querySelector('.user-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('open');
    }
}

function initializeDropdowns() {
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        const dropdown = document.querySelector('.user-dropdown');
        const toggle = document.querySelector('.user-dropdown-toggle');
        
        if (dropdown && toggle && !dropdown.contains(e.target)) {
            dropdown.classList.remove('open');
        }
    });
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        const menu = document.getElementById('navbarMenu');
        const toggler = document.querySelector('.navbar-toggler');
        
        if (menu && toggler && !menu.contains(e.target) && !toggler.contains(e.target)) {
            menu.classList.remove('open');
        }
    });
}

// ============================================
// ALERT HANDLING
// ============================================
function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });
}

// ============================================
// CONFIRM DIALOGS
// ============================================
function initializeConfirmDialogs() {
    const dangerButtons = document.querySelectorAll('[data-confirm]');
    dangerButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

// ============================================
// FORM VALIDATION
// ============================================
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

// ============================================
// PASSWORD STRENGTH
// ============================================
function initializePasswordStrength() {
    const passwordInput = document.getElementById('new_password');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            const strength = calculatePasswordStrength(password);
            updatePasswordStrengthIndicator(strength);
        });
    }
}

// Password strength calculator
function calculatePasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 8) strength += 1;
    if (password.length >= 12) strength += 1;
    if (/[a-z]/.test(password)) strength += 1;
    if (/[A-Z]/.test(password)) strength += 1;
    if (/[0-9]/.test(password)) strength += 1;
    if (/[^a-zA-Z0-9]/.test(password)) strength += 1;
    
    return strength;
}

// Update password strength indicator
function updatePasswordStrengthIndicator(strength) {
    const indicator = document.getElementById('password-strength');
    if (!indicator) return;
    
    const configs = [
        { color: 'danger', text: 'Very Weak', width: '20%' },
        { color: 'danger', text: 'Weak', width: '35%' },
        { color: 'warning', text: 'Fair', width: '50%' },
        { color: 'info', text: 'Good', width: '70%' },
        { color: 'success', text: 'Strong', width: '85%' },
        { color: 'success', text: 'Very Strong', width: '100%' }
    ];
    
    const config = configs[Math.min(strength, 5)];
    indicator.className = `progress-bar bg-${config.color}`;
    indicator.style.width = config.width;
    indicator.textContent = config.text;
}

// ============================================
// TOOLTIP INITIALIZATION
// ============================================
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// ============================================
// TABLE SEARCH
// ============================================
function initializeTableSearch() {
    const searchInputs = document.querySelectorAll('[data-table-search]');
    searchInputs.forEach(searchInput => {
        const table = document.querySelector(searchInput.getAttribute('data-table-search'));
        if (!table) return;
        
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    });
}

// Alias for backwards compatibility
function setupTableSearch() {
    initializeTableSearch();
}

// ============================================
// ANIMATIONS
// ============================================
function initializeAnimations() {
    // Fade in elements on scroll
    const fadeElements = document.querySelectorAll('.fade-in-scroll');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    fadeElements.forEach(el => observer.observe(el));
}

// ============================================
// REAL-TIME SLOT REFRESH
// ============================================
function startSlotRefresh() {
    setInterval(async function() {
        try {
            const response = await fetch('/api/slots');
            const data = await response.json();
            
            if (data.success) {
                updateSlotAvailability(data.slots);
            }
        } catch (error) {
            console.error('Error refreshing slots:', error);
        }
    }, 30000); // Refresh every 30 seconds
}

// Update slot availability in the DOM
function updateSlotAvailability(slots) {
    slots.forEach(slot => {
        const slotCard = document.querySelector(`[data-slot-id="${slot.id}"]`);
        if (slotCard) {
            const badge = slotCard.querySelector('.badge');
            const button = slotCard.querySelector('button[type="submit"]');
            const slotCardInner = slotCard.querySelector('.slot-card');
            
            if (slot.is_available) {
                if (badge) {
                    badge.className = 'badge bg-success';
                    badge.textContent = `${slot.available_spots} spots available`;
                }
                if (slotCardInner) {
                    slotCardInner.classList.remove('full');
                }
            } else {
                if (badge) {
                    badge.className = 'badge bg-secondary';
                    badge.textContent = 'Fully Booked';
                }
                if (button) {
                    button.disabled = true;
                    button.className = 'btn btn-secondary';
                    button.innerHTML = '<i class="bi bi-x-circle"></i> Full';
                }
                if (slotCardInner) {
                    slotCardInner.classList.add('full');
                }
            }
        }
    });
}

// ============================================
// LOADING OVERLAY
// ============================================
function showLoading(message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
    overlay.id = 'loading-overlay';
    overlay.style.cssText = 'background: rgba(0,0,0,0.5); z-index: 9999;';
    overlay.innerHTML = `
        <div class="text-center text-white">
            <div class="loading-spinner mb-3" style="width: 50px; height: 50px; border-width: 4px;"></div>
            <p class="mb-0">${message}</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toastId = 'toast-' + Date.now();
    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1100';
    document.body.appendChild(container);
    return container;
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function formatDate(dateString) {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

function formatTime(timeString) {
    return new Date('1970-01-01T' + timeString).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

// ============================================
// FORM LOADING STATE
// ============================================
function initializeFormLoading() {
    // Add loading state to all forms with buttons
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.classList.contains('no-loading')) {
                // Store original content
                submitBtn.dataset.originalText = submitBtn.innerHTML;
                
                // Add loading state
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
                
                // Add spinner
                const spinner = document.createElement('span');
                spinner.className = 'spinner-border spinner-border-sm ms-2';
                spinner.setAttribute('role', 'status');
                submitBtn.appendChild(spinner);
            }
        });
    });
}

// Reset button state (useful after AJAX calls)
function resetButtonState(button) {
    if (button && button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
        button.classList.remove('loading');
        button.disabled = false;
    }
}

// ============================================
// ENHANCED CONFIRM DIALOGS
// ============================================
function confirmAction(message, callback) {
    if (confirm(message)) {
        if (typeof callback === 'function') {
            callback();
        }
        return true;
    }
    return false;
}

// ============================================
// EXPORT FUNCTIONS
// ============================================
window.recruitmentPortal = {
    showLoading,
    hideLoading,
    showToast,
    updateSlotAvailability,
    formatDate,
    formatTime,
    resetButtonState,
    confirmAction
};
