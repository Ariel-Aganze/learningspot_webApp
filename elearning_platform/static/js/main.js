// main.js - Main JavaScript file for the E-Learning Platform

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Add active class to nav-links based on current page
    const currentLocation = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        
        // Skip dropdown toggles
        if (link.classList.contains('dropdown-toggle')) {
            return;
        }
        
        if (href === currentLocation || 
            (href !== '/' && currentLocation.includes(href))) {
            link.classList.add('active');
            
            // If inside dropdown, also activate the parent
            const dropdownMenu = link.closest('.dropdown-menu');
            if (dropdownMenu) {
                const dropdownToggle = dropdownMenu.previousElementSibling;
                if (dropdownToggle && dropdownToggle.classList.contains('dropdown-toggle')) {
                    dropdownToggle.classList.add('active');
                }
            }
        }
    });

    // Handle organization checkbox on signup form
    const orgCheckbox = document.getElementById('is_organization');
    const orgFields = document.getElementById('organization_fields');
    
    if (orgCheckbox && orgFields) {
        // Initial state
        if (orgCheckbox.checked) {
            orgFields.style.display = 'block';
        } else {
            orgFields.style.display = 'none';
        }
        
        // Toggle organization fields
        orgCheckbox.addEventListener('change', function() {
            if (this.checked) {
                orgFields.style.display = 'block';
            } else {
                orgFields.style.display = 'none';
            }
        });
    }

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });

    // Handle quiz timers
    const quizTimer = document.getElementById('quizTimer');
    const questionTimer = document.getElementById('questionTimer');
    
    if (quizTimer) {
        const minutesElement = document.getElementById('minutes');
        const secondsElement = document.getElementById('seconds');
        let remainingTime = parseInt(quizTimer.dataset.remaining);
        
        // Update quiz timer
        const updateQuizTimer = () => {
            const minutes = Math.floor(remainingTime / 60);
            const seconds = remainingTime % 60;
            
            minutesElement.textContent = minutes.toString().padStart(2, '0');
            secondsElement.textContent = seconds.toString().padStart(2, '0');
            
            // Add warning class when time is running low (less than 5 minutes)
            if (remainingTime < 300) {
                quizTimer.classList.add('timer-warning');
            }
            
            remainingTime--;
            
            // If time is up, submit the form
            if (remainingTime < 0) {
                window.location.reload();
            }
        };
        
        // Start timer
        updateQuizTimer();
        setInterval(updateQuizTimer, 1000);
    }
    
    if (questionTimer) {
        const questionSecondsElement = document.getElementById('questionSeconds');
        let questionTimeLimit = parseInt(questionTimer.dataset.limit);
        let questionTimeTaken = 0;
        const timeField = document.querySelector('input[name="time_taken"]');
        
        // Update question timer
        const updateQuestionTimer = () => {
            questionSecondsElement.textContent = questionTimeLimit;
            
            // Add warning class when time is running low (less than 10 seconds)
            if (questionTimeLimit < 10) {
                questionTimer.classList.add('timer-warning');
            }
            
            questionTimeLimit--;
            questionTimeTaken++;
            
            if (timeField) {
                timeField.value = questionTimeTaken;
            }
            
            // If question time is up, submit the form
            if (questionTimeLimit < 0 && document.getElementById('questionForm')) {
                document.getElementById('questionForm').submit();
            }
        };
        
        // Start timer
        updateQuestionTimer();
        setInterval(updateQuestionTimer, 1000);
    }
});

// Function to handle file input display
function updateFileLabel(input) {
    const fileLabel = document.querySelector(`label[for="${input.id}"]`);
    if (fileLabel) {
        if (input.files.length > 0) {
            fileLabel.textContent = input.files[0].name;
        } else {
            fileLabel.textContent = 'Choose file';
        }
    }
}

// Function to preview image before upload
function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    if (preview && input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        
        reader.readAsDataURL(input.files[0]);
    }
}