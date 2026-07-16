/* ========================================
   Gesture Control System - JavaScript
   ======================================== */

// Theme Management
function applyTheme(theme) {
    const htmlElement = document.documentElement;
    const bodyElement = document.body;
    
    if (theme === 'dark') {
        htmlElement.setAttribute('data-theme', 'dark');
        bodyElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    } else {
        htmlElement.setAttribute('data-theme', 'light');
        bodyElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
    }
}

function initializeTheme() {
    // Get theme from HTML or body attribute set by Flask
    const htmlTheme = document.documentElement.getAttribute('data-theme');
    const bodyTheme = document.body.getAttribute('data-theme');
    const currentTheme = htmlTheme || bodyTheme || localStorage.getItem('theme') || 'light';
    
    applyTheme(currentTheme);
}

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Apply theme first
    initializeTheme();
    
    // Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Gesture-related functions
function deleteGesture(gestureId) {
    if (confirm('Are you sure you want to delete this gesture?')) {
        fetch(`/api/gestures/${gestureId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message and reload
                showNotification('Gesture deleted successfully!', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showNotification('Error deleting gesture', 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', 'danger');
        });
    }
}

function launchGestureApp() {
    // Show loading state
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Launching...';

    fetch('/api/launch-app', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        btn.innerHTML = originalText;
        btn.disabled = false;
        
        if (data.success) {
            showNotification('Gesture app launched! Check your desktop.', 'success');
            // Close modal if open
            const modal = bootstrap.Modal.getInstance(document.getElementById('launchModal'));
            if (modal) modal.hide();
        } else {
            showNotification(data.error || 'Failed to launch app', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        btn.innerHTML = originalText;
        btn.disabled = false;
        showNotification('An error occurred while launching the app', 'danger');
    });
}

function startGestureRecording() {
    showNotification('Recording started! Perform your gesture in front of the webcam.', 'info');
}

function saveGestureSettings() {
    const gestureData = {
        gesture_name: document.getElementById('gestureName')?.value,
        description: document.getElementById('gestureDesc')?.value,
        gesture_data: JSON.stringify({})
    };

    fetch('/api/gestures', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(gestureData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Gesture saved successfully!', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification('Error saving gesture', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred', 'danger');
    });
}

// Settings functions
function updateSettings() {
    const settingsData = {
        default_effect: document.getElementById('defaultEffect')?.value,
        enable_shape_detection: document.getElementById('shapeDetection')?.checked,
        enable_gesture_recording: document.getElementById('gestureRecording')?.checked,
        gesture_sensitivity: parseFloat(document.getElementById('sensitivity')?.value),
        theme: document.getElementById('theme')?.value
    };

    fetch('/api/settings', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settingsData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Settings updated successfully!', 'success');
        } else {
            showNotification('Error updating settings', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred', 'danger');
    });
}

// Utility functions
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
}

function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Range input update
document.addEventListener('input', function(e) {
    if (e.target.type === 'range') {
        const value = e.target.value;
        const label = e.target.previousElementSibling;
        if (label && label.querySelector('.badge')) {
            const x = (value - e.target.min) / (e.target.max - e.target.min) * 100;
            e.target.style.setProperty('--value', x + '%');
        }
    }
});

// Table sorting
function sortTable(tableId, columnIndex) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aValue = a.children[columnIndex].textContent.trim();
        const bValue = b.children[columnIndex].textContent.trim();
        return aValue.localeCompare(bValue);
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// Search functionality
function filterTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    
    const filter = input.value.toUpperCase();
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toUpperCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
}

// Export data as CSV
function exportToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const csvRow = [];
        cols.forEach(col => {
            csvRow.push('"' + col.textContent.trim() + '"');
        });
        csv.push(csvRow.join(','));
    });
    
    const csvContent = csv.join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent));
    link.setAttribute('download', filename);
    link.click();
}

// Check password strength
function checkPasswordStrength(passwordInput) {
    const password = passwordInput.value;
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    
    const strengthBar = document.getElementById('passwordStrength');
    if (strengthBar) {
        strengthBar.style.width = (strength * 20) + '%';
        strengthBar.className = 'progress-bar ' + 
            (strength < 2 ? 'bg-danger' : 
             strength < 3 ? 'bg-warning' : 
             strength < 4 ? 'bg-info' : 
             'bg-success');
    }
    
    return strength;
}

// Console logging for debugging
console.log('%cGesture Control System', 'color: #667eea; font-size: 16px; font-weight: bold;');
console.log('%cVersion 1.0', 'color: #764ba2;');
console.log('%cReady to control gestures!', 'color: #10b981;');
