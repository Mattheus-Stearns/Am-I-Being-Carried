// ============================================
// ALL FUNCTIONS DEFINED AT THE TOP LEVEL
// ============================================

// 1. Helper Functions (defined first)
function showPreloader() {
    console.log('Showing preloader');
    const preloader = document.getElementById('preloader');
    if (preloader) {
        preloader.style.display = 'flex';
    } else {
        console.warn('Preloader element not found');
    }
}

function validateUsername(username) {
    if (!username || username.trim().length === 0) {
        return { valid: false, message: 'Please enter a username.' };
    }
    
    const trimmed = username.trim();
    if (trimmed.length < 2) {
        return { valid: false, message: 'Username must be at least 2 characters.' };
    }
    
    if (trimmed.length > 100) {
        return { valid: false, message: 'Username must be less than 100 characters.' };
    }
    
    // Only allow alphanumeric, underscores, hyphens, dots, spaces
    if (!/^[a-zA-Z0-9_.\- ]+$/.test(trimmed)) {
        return { valid: false, message: 'Username contains invalid characters. Only letters, numbers, underscores, hyphens, dots, and spaces are allowed.' };
    }
    
    return { valid: true };
}

function hidePreloader() {
    console.log('Hiding preloader');
    const preloader = document.getElementById('preloader');
    if (preloader) {
        preloader.style.display = 'none';
    }
}

// Show Error Function - Fixed
function showError(message, suggestion = null, suggestionUsername = null) {
    console.log('Showing error:', message, suggestion, suggestionUsername);
    const alert = document.getElementById('errorAlert');
    if (!alert) {
        console.error('Error alert not found!');
        alert('Error: ' + message);
        return;
    }
    
    // Set the error message
    const errorMessageEl = document.getElementById('errorMessage');
    if (errorMessageEl) {
        errorMessageEl.textContent = message;
    }
    
    // Handle suggestion
    const suggestionText = document.getElementById('suggestionText');
    const suggestionButton = document.getElementById('suggestionButton');
    const suggestionUsernameEl = document.getElementById('suggestionUsername');
    
    if (suggestion && suggestionUsername) {
        // Show "Did you mean?" button
        if (suggestionText) suggestionText.textContent = suggestion;
        if (suggestionUsernameEl) suggestionUsernameEl.textContent = suggestionUsername;
        if (suggestionButton) suggestionButton.style.display = 'inline-block';
    } else if (suggestion) {
        // Show just the text suggestion without a button
        if (suggestionText) suggestionText.textContent = suggestion;
        if (suggestionButton) suggestionButton.style.display = 'none';
    } else {
        if (suggestionText) suggestionText.textContent = '';
        if (suggestionButton) suggestionButton.style.display = 'none';
    }
    
    // Show the alert
    alert.style.display = 'block';
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        hideError();
    }, 10000);
}

function hideError() {
    console.log('Hiding error');
    const alert = document.getElementById('errorAlert');
    if (alert) {
        alert.style.display = 'none';
    }
}

function showDonationStatus(message, type = 'info') {
    const status = document.getElementById('donationStatus');
    if (status) {
        status.innerHTML = `<div class="alert alert-${type} alert-sm mb-0">${message}</div>`;
        setTimeout(() => status.innerHTML = '', 10000);
    }
}

// 2. Toast Notification Function
function showToast(message, type = 'success') {
    const existingToast = document.querySelector('.custom-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `custom-toast alert alert-${type} position-fixed bottom-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.style.maxWidth = '400px';
    toast.style.animation = 'slideUp 0.3s ease-out';
    toast.innerHTML = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// 3. Time Since Function
function timeSince(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + ' years ago';
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + ' months ago';
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + ' days ago';
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + ' hours ago';
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + ' minutes ago';
    return Math.floor(seconds) + ' seconds ago';
}

// 4. Platform Selection Function
function selectPlatform(button) {
    console.log('Button clicked:', button);
    
    const allButtons = document.querySelectorAll('.platform-btn');
    allButtons.forEach(btn => {
        btn.classList.remove('active', 'btn-primary');
        btn.classList.add('btn-outline-primary');
    });
    
    button.classList.remove('btn-outline-primary');
    button.classList.add('active', 'btn-primary');
    
    const platformId = button.dataset.platform;
    const selectedPlatformInput = document.getElementById('selectedPlatform');
    if (selectedPlatformInput) {
        selectedPlatformInput.value = platformId;
    }
    
    // Update platform status
    const statusEl = document.getElementById('platformStatus');
    if (statusEl) {
        statusEl.textContent = `Selected platform: ${platformId.toUpperCase()}`;
        statusEl.className = 'text-success';
    }
    
    console.log('Selected platform:', platformId);
}

// 5. Main Submit Function
async function submitApiForm(formId) {
    console.log('submitApiForm called');
    
    const form = document.getElementById(formId);
    if (!form) {
        console.error('Form not found!');
        showError('Form not found');
        return;
    }
    
    // Get username
    const usernameInput = document.getElementById('username');
    if (!usernameInput) {
        console.error('Username field not found!');
        showError('Username field not found');
        return;
    }
    
    const username = usernameInput.value.trim();
    console.log('Username:', username);
    
    // Validate username
    const validation = validateUsername(username);
    if (!validation.valid) {
        showError(validation.message);
        return;
    }
    
    // Get selected platform
    const platformId = document.getElementById('selectedPlatform').value;
    console.log('Platform ID:', platformId);
    
    if (!platformId) {
        showError('Please select a platform first!');
        const statusEl = document.getElementById('platformStatus');
        if (statusEl) {
            statusEl.textContent = '⚠️ Please select a platform!';
            statusEl.style.color = 'red';
        }
        return;
    }
    
    console.log('Submitting form for:', platformId, username);
    showPreloader();
    
    // Build the data
    const data = {
        platform_id: platformId,
        username: username,
        force_refresh: true
    };
    console.log('Request data:', data);
    
    try {
        // Make the API query directly - skip clearing session for now
        console.log('Making API query to /api/query...');
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        console.log('Response status:', response.status);
        const result = await response.json();
        console.log('Response data:', result);
        
        if (result.success) {
            window.location.href = '/results';
            return;
        }
        
        // Handle errors
        let errorMessage = result.message || 'Failed to fetch data';
        let suggestionText = null;
        let suggestionUsername = null;
        
        // Check if we have a suggestion object
        if (result.suggestion && typeof result.suggestion === 'object') {
            suggestionText = `Did you mean "${result.suggestion.username}"? (Found ${result.suggestion.search_count} successful searches)`;
            suggestionUsername = result.suggestion.username;
        } else if (result.suggestion && typeof result.suggestion === 'string') {
            suggestionText = result.suggestion;
        }
        
        showError(errorMessage, suggestionText, suggestionUsername);
        hidePreloader();
        
    } catch (error) {
        console.error('Fetch error:', error);
        showError('An error occurred while processing your request. Please try again.');
        hidePreloader();
    }
}

// 6. Share Result Function
async function shareResult() {
    try {
        const shareBtn = document.querySelector('.share-btn');
        if (!shareBtn) {
            console.error('Share button not found');
            return;
        }
        
        const originalText = shareBtn.innerHTML;
        shareBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        shareBtn.disabled = true;
        
        const card = document.getElementById('carried-score-card');
        if (!card) {
            console.error('Card not found');
            showToast('Card not found to share.', 'danger');
            shareBtn.innerHTML = originalText;
            shareBtn.disabled = false;
            return;
        }
        
        if (typeof html2canvas === 'undefined') {
            console.error('html2canvas not loaded');
            showToast('Share library not loaded. Please refresh and try again.', 'danger');
            shareBtn.innerHTML = originalText;
            shareBtn.disabled = false;
            return;
        }
        
        const siteUrl = window.location.origin;
        
        const canvas = await html2canvas(card, {
            scale: 2,
            backgroundColor: '#ffffff',
            allowTaint: true,
            useCORS: true,
            logging: false,
            onclone: function(document) {
                document.querySelectorAll('img').forEach(img => {
                    img.crossOrigin = 'anonymous';
                });
            }
        });
        
        const ctx = canvas.getContext('2d');
        const footerHeight = 40;
        const gradient = ctx.createLinearGradient(0, canvas.height - footerHeight, 0, canvas.height);
        gradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0.7)');
        
        ctx.fillStyle = gradient;
        ctx.fillRect(0, canvas.height - footerHeight, canvas.width, footerHeight);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`Check your score at ${siteUrl}`, canvas.width / 2, canvas.height - (footerHeight / 2));
        
        const imageUrl = canvas.toDataURL('image/png');
        
        const scoreElement = document.querySelector('[style*="font-size: 4rem;"]');
        const scoreText = scoreElement?.textContent?.trim() || '??';
        const shareText = `I got a ${scoreText} Carried Score! Check yours at ${siteUrl}`;
        
        let shareSuccessful = false;
        
        if (navigator.share) {
            try {
                const response = await fetch(imageUrl);
                const blob = await response.blob();
                const file = new File([blob], 'carried-score.png', { type: 'image/png' });
                
                await navigator.share({
                    title: 'Am I Being Carried?',
                    text: shareText,
                    files: [file],
                    url: siteUrl
                });
                
                shareSuccessful = true;
                showToast('Shared successfully!', 'success');
                
            } catch (shareError) {
                console.log('Share cancelled or failed:', shareError);
                
                if (shareError.name !== 'AbortError' && shareError.name !== 'CancelError') {
                    try {
                        await navigator.share({
                            title: 'Am I Being Carried?',
                            text: shareText,
                            url: siteUrl
                        });
                        shareSuccessful = true;
                        showToast('Shared successfully!', 'success');
                    } catch (textError) {
                        console.log('Text share failed:', textError);
                    }
                } else {
                    showToast('Share cancelled. Link copied to clipboard instead.', 'info');
                    await navigator.clipboard.writeText(shareText);
                    shareSuccessful = true;
                }
            }
        }
        
        if (!shareSuccessful) {
            const link = document.createElement('a');
            link.download = 'carried-score.png';
            link.href = imageUrl;
            link.click();
            
            try {
                await navigator.clipboard.writeText(shareText);
                showToast('Image downloaded! Link copied to clipboard.', 'success');
            } catch (clipError) {
                showToast('Image downloaded! Copy this link: ' + shareText, 'info');
            }
        }
        
        shareBtn.innerHTML = originalText;
        shareBtn.disabled = false;
        
    } catch (error) {
        console.error('Share error:', error);
        showToast('Failed to share. Please try again.', 'danger');
        
        const shareBtn = document.querySelector('.share-btn');
        if (shareBtn) {
            shareBtn.innerHTML = '<i class="fas fa-share-alt"></i> Share';
            shareBtn.disabled = false;
        }
    }
}

async function copyShareLink() {
    try {
        const copyBtn = document.querySelector('.copy-btn');
        if (copyBtn) {
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Copying...';
            copyBtn.disabled = true;
        }
        
        const siteUrl = window.location.origin;
        const scoreElement = document.querySelector('[style*="font-size: 4rem;"]');
        const scoreText = scoreElement?.textContent?.trim() || '??';
        
        const platform = document.body?.dataset?.platform || '';
        const username = document.body?.dataset?.username || '';
        const playerInfo = platform && username ? ` (${platform}/${username})` : '';
        
        const shareText = `I got a ${scoreText} Carried Score${playerInfo}! Check yours at ${siteUrl}`;
        
        await navigator.clipboard.writeText(shareText);
        showToast('Share link copied to clipboard! Share it with your friends.', 'success');
        
        if (copyBtn) {
            copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Link';
                copyBtn.disabled = false;
            }, 2000);
        }
    } catch (error) {
        console.error('Copy error:', error);
        showToast('Failed to copy. Please try again.', 'danger');
        
        const copyBtn = document.querySelector('.copy-btn');
        if (copyBtn) {
            copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Link';
            copyBtn.disabled = false;
        }
    }
}

// 7. Refresh Data Function
async function refreshData() {
    if (!confirm('This will make a new API call and use one credit. Continue?')) {
        return;
    }
    
    const platform = document.body.dataset.platform || document.getElementById('platformData')?.value;
    const username = document.body.dataset.username || document.getElementById('usernameData')?.value;
    
    if (!platform || !username) {
        showError('Platform or username not found');
        return;
    }
    
    showPreloader();
    
    try {
        const response = await fetch('/api/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                platform_id: platform,
                username: username
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.location.reload();
        } else {
            showError(result.message || 'Failed to refresh data');
            hidePreloader();
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred while refreshing data.');
        hidePreloader();
    }
}

// 8. Clear Session Function
function clearAndSearch() {
    if (confirm('This will clear your current search results. Continue?')) {
        fetch('/api/clear_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        }).then(() => {
            window.location.href = '/';
        }).catch(error => {
            console.error('Error clearing session:', error);
            window.location.href = '/';
        });
    }
}

// 9. Feedback

let selectedRating = 0;

function setRating(rating) {
    selectedRating = rating;
    document.getElementById('feedbackRating').value = rating;
    
    const stars = document.querySelectorAll('.star-rating .fa-star');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add('text-warning');
            star.classList.remove('text-secondary');
        } else {
            star.classList.remove('text-warning');
            star.classList.add('text-secondary');
        }
    });
}

async function submitFeedback(event) {
    event.preventDefault();
    
    const name = document.getElementById('feedbackName').value.trim();
    const email = document.getElementById('feedbackEmail').value.trim();
    const rating = parseInt(document.getElementById('feedbackRating').value);
    const message = document.getElementById('feedbackMessage').value.trim();
    const statusDiv = document.getElementById('feedbackStatus');
    
    if (!message) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger alert-sm mb-0">
                <i class="fas fa-exclamation-triangle"></i> Please enter your feedback message.
            </div>
        `;
        return;
    }
    
    const submitBtn = document.querySelector('#feedbackForm button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                email: email,
                rating: rating,
                message: message,
                page_url: window.location.href
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success alert-sm mb-0">
                    <i class="fas fa-check-circle"></i> ${result.message}
                </div>
            `;
            document.getElementById('feedbackForm').reset();
            setRating(0);
            document.getElementById('feedbackRating').value = 0;
            
            document.querySelectorAll('.star-rating .fa-star').forEach(star => {
                star.classList.remove('text-warning');
                star.classList.add('text-secondary');
            });
        } else {
            statusDiv.innerHTML = `
                <div class="alert alert-danger alert-sm mb-0">
                    <i class="fas fa-exclamation-triangle"></i> ${result.message}
                </div>
            `;
        }
    } catch (error) {
        console.error('Feedback error:', error);
        statusDiv.innerHTML = `
            <div class="alert alert-danger alert-sm mb-0">
                <i class="fas fa-exclamation-triangle"></i> Failed to submit feedback. Please try again.
            </div>
        `;
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
        
        setTimeout(() => {
            if (statusDiv.innerHTML) {
                statusDiv.innerHTML = '';
            }
        }, 5000);
    }
}

// 10. Initialize Everything
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - initializing');
    
    // --- Initialize Platform Buttons ---
    const buttons = document.querySelectorAll('.platform-btn');
    console.log('Found platform buttons:', buttons.length);
    
    if (buttons.length > 0) {
        buttons.forEach(button => {
            button.removeAttribute('onclick');
            button.addEventListener('click', function() {
                selectPlatform(this);
            });
        });
        console.log('Platform buttons initialized');
    }
    
    // --- Initialize Form Submission ---
    const form = document.getElementById('apiForm');
    if (form) {
        console.log('Found form, adding submit listener');
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Form submitted via event listener');
            submitApiForm('apiForm');
        });
    } else {
        console.warn('apiForm not found');
    }
    
    // --- Initialize Submit Button (fallback) ---
    const submitBtn = document.querySelector('#apiForm button[type="submit"]');
    if (submitBtn) {
        submitBtn.addEventListener('click', function(e) {
            console.log('Submit button clicked');
            // The form's submit event will handle it
        });
    }

    // --- Suggestion button click handler ---
    const suggestionButton = document.getElementById('suggestionButton');
    if (suggestionButton) {
        suggestionButton.addEventListener('click', function() {
            const username = document.getElementById('suggestionUsername').textContent;
            if (username) {
                document.getElementById('username').value = username;
                hideError();
                submitApiForm('apiForm');
            }
        });
        console.log('Suggestion button initialized');
    }
    
    // --- Handle Enter key on username field ---
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                console.log('Enter key pressed on username field');
                submitApiForm('apiForm');
            }
        });
    }
    
    // --- Initialize Share Button ---
    const shareButton = document.querySelector('.share-btn');
    if (shareButton) {
        shareButton.addEventListener('click', shareResult);
        console.log('Share button initialized');
    }

    const copyBtn = document.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', copyShareLink);
        console.log('Copy button initialized');
    }
    
    // --- Show last updated time ---
    const lastUpdatedElement = document.querySelector('.last-updated-text');
    if (lastUpdatedElement) {
        const lastUpdated = lastUpdatedElement.dataset.time;
        if (lastUpdated) {
            const date = new Date(lastUpdated);
            const timeAgo = timeSince(date);
            const badge = document.querySelector('.alert .badge:not(.bg-secondary)');
            if (badge) {
                badge.textContent += ` (${timeAgo})`;
            }
        }
    }

    // --- Donation Form ---
    const amountBtns = document.querySelectorAll('.amount-btn');
    const customAmount = document.getElementById('customAmount');
    const selectedAmount = document.getElementById('selectedAmount');
    
    if (amountBtns.length > 0) {
        amountBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                amountBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                if (this.dataset.amount === 'custom') {
                    customAmount.style.display = 'block';
                    customAmount.focus();
                    selectedAmount.value = '';
                } else {
                    customAmount.style.display = 'none';
                    selectedAmount.value = this.dataset.amount;
                }
            });
        });
    }
    
    if (customAmount) {
        customAmount.addEventListener('input', function() {
            if (this.value) {
                selectedAmount.value = this.value;
            }
        });
    }
    
    const donationForm = document.getElementById('donationForm');
    if (donationForm) {
        donationForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const amount = selectedAmount.value;
            if (!amount || parseFloat(amount) < 1) {
                showDonationStatus('Please select or enter a donation amount (minimum $1).', 'danger');
                return;
            }
            
            const name = document.getElementById('donorName').value.trim();
            const email = document.getElementById('donorEmail').value.trim();
            const message = document.getElementById('donorMessage').value.trim();
            const isAnonymous = document.getElementById('anonymousDonation').checked;
            const showOnWall = document.getElementById('showOnWall').checked;
            
            const donateBtn = document.getElementById('donateBtn');
            const originalText = donateBtn.innerHTML;
            donateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            donateBtn.disabled = true;
            
            try {
                const response = await fetch('/donate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        amount: amount,
                        name: name,
                        email: email,
                        message: message,
                        is_anonymous: isAnonymous,
                        show_on_wall: showOnWall
                    })
                });
                
                const result = await response.json();
                
                if (!result.success) {
                    showDonationStatus(result.message || 'Error processing donation.', 'danger');
                    donateBtn.innerHTML = originalText;
                    donateBtn.disabled = false;
                    return;
                }
                
                const { error } = await stripe.confirmCardPayment(result.client_secret, {
                    payment_method: {
                        card: {},
                        billing_details: {
                            name: name || 'Anonymous',
                            email: email || undefined
                        }
                    }
                });
                
                if (error) {
                    showDonationStatus('Payment failed: ' + error.message, 'danger');
                    donateBtn.innerHTML = originalText;
                    donateBtn.disabled = false;
                    return;
                }
                
                const confirmResponse = await fetch('/api/donation/success', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        payment_intent_id: result.payment_intent_id
                    })
                });
                
                const confirmResult = await confirmResponse.json();
                
                if (confirmResult.success) {
                    showDonationStatus('Thank you for your support! Your donation means the world to us.', 'success');
                    document.getElementById('donationForm').reset();
                    document.querySelectorAll('.amount-btn').forEach(b => b.classList.remove('active'));
                    customAmount.style.display = 'none';
                    
                    setTimeout(() => location.reload(), 3000);
                } else {
                    showDonationStatus('Payment processed but confirmation failed. Please contact support.', 'warning');
                }
                
            } catch (error) {
                console.error('Donation error:', error);
                showDonationStatus('An error occurred. Please try again.', 'danger');
            } finally {
                donateBtn.innerHTML = originalText;
                donateBtn.disabled = false;
            }
        });
    }
    
    console.log('All initializations complete');
});

// 11. Make functions globally accessible
window.selectPlatform = selectPlatform;
window.submitApiForm = submitApiForm;
window.shareResult = shareResult;
window.refreshData = refreshData;
window.clearAndSearch = clearAndSearch;
window.showPreloader = showPreloader;
window.hidePreloader = hidePreloader;
window.showError = showError;
window.hideError = hideError;
window.showToast = showToast;
window.timeSince = timeSince;

console.log('All functions loaded and ready');