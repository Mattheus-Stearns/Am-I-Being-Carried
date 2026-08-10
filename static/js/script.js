// ============================================
// ALL FUNCTIONS DEFINED AT THE TOP LEVEL
// ============================================

const stripe = Stripe('{{ stripe_publishable_key }}');

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

function showError(message) {
    console.log('Showing error:', message);
    const alert = document.getElementById('errorAlert');
    if (alert) {
        document.getElementById('errorMessage').textContent = message;
        alert.style.display = 'block';
        setTimeout(() => {
            hideError();
        }, 5000);
    } else {
        alert('Error: ' + message);
    }
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
    status.innerHTML = `<div class="alert alert-${type} alert-sm mb-0">${message}</div>`;
    setTimeout(() => status.innerHTML = '', 10000);
}

// 2. Toast Notification Function
function showToast(message, type = 'success') {
    // Remove existing toast
    const existingToast = document.querySelector('.custom-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = `custom-toast alert alert-${type} position-fixed bottom-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.style.maxWidth = '400px';
    toast.style.animation = 'slideUp 0.3s ease-out';
    toast.innerHTML = message;
    document.body.appendChild(toast);
    
    // Auto remove after 5 seconds
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
    
    // Get all platform buttons
    const allButtons = document.querySelectorAll('.platform-btn');
    
    // Remove 'active' class from all buttons
    allButtons.forEach(btn => {
        btn.classList.remove('active', 'btn-primary');
        btn.classList.add('btn-outline-primary');
    });
    
    // Activate the clicked button
    button.classList.remove('btn-outline-primary');
    button.classList.add('active', 'btn-primary');
    
    // Store the selected platform ID
    const platformId = button.dataset.platform;
    const selectedPlatformInput = document.getElementById('selectedPlatform');
    if (selectedPlatformInput) {
        selectedPlatformInput.value = platformId;
    }
    
    console.log('Selected platform:', platformId);
}

// 5. Main Submit Function
async function submitApiForm(formId) {
    const username = document.getElementById('username').value.trim();
    
    // Validate username
    const validation = validateUsername(username);
    if (!validation.valid) {
        showError(validation.message);
        return;
    }
    console.log('Submitting form...');
    
    const form = document.getElementById(formId);
    if (!form) {
        console.error('Form not found!');
        showError('Form not found');
        return;
    }
    
    // Get selected platform
    const platformId = document.getElementById('selectedPlatform').value;
    console.log('Platform ID from hidden input:', platformId);
    
    if (!platformId) {
        showError('Please select a platform first!');
        const statusEl = document.getElementById('platformStatus');
        if (statusEl) {
            statusEl.textContent = 'Please select a platform!';
            statusEl.style.color = 'red';
        }
        return;
    }
    
    // Get username
    const username = document.getElementById('username').value.trim();
    console.log('Username:', username);
    
    if (!username) {
        showError('Please enter a username.');
        return;
    }
    
    showPreloader();
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    data.force_refresh = true;
    console.log('Form data with force_refresh:', data);
    
    try {
        // First, clear the session to force a fresh request
        console.log(' Clearing session...');
        await fetch('/api/clear_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        console.log('Session cleared');
        
        // Then make the API query
        console.log('Making API query...');
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        console.log('Response:', result);
        
        if (response.status === 429) {
            showError(result.message || 'Rate limit exceeded. Please try again later.');
            hidePreloader();
            return;
        }
        
        if (result.success) {
            window.location.href = '/results';
        } else {
            showError(result.message || 'Failed to fetch data');
            hidePreloader();
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred while processing your request.');
        hidePreloader();
    }
}

// 6. Share Result Function
async function shareResult() {
    try {
        // Show loading state
        const shareBtn = document.querySelector('.share-btn');
        if (!shareBtn) {
            console.error('Share button not found');
            return;
        }
        
        const originalText = shareBtn.innerHTML;
        shareBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        shareBtn.disabled = true;
        
        // Get the card element
        const card = document.getElementById('carried-score-card');
        if (!card) {
            console.error('Card not found');
            showToast(' Card not found to share.', 'danger');
            shareBtn.innerHTML = originalText;
            shareBtn.disabled = false;
            return;
        }
        
        // Check if html2canvas is loaded
        if (typeof html2canvas === 'undefined') {
            console.error('html2canvas not loaded');
            showToast(' Share library not loaded. Please refresh and try again.', 'danger');
            shareBtn.innerHTML = originalText;
            shareBtn.disabled = false;
            return;
        }
        
        // Get the site URL for the watermark/link
        const siteUrl = window.location.origin;
        
        // Generate image with watermark
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
        
        // Add watermark/text to the image
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
        
        // Convert to image URL
        const imageUrl = canvas.toDataURL('image/png');
        
        // Get score text
        const scoreElement = document.querySelector('[style*="font-size: 4rem;"]');
        const scoreText = scoreElement?.textContent?.trim() || '??';
        
        // Create share text with link
        const shareText = `I got a ${scoreText} Carried Score! Check yours at ${siteUrl}`;
        
        // --- MODIFIED: Better handling for macOS ---
        let shareSuccessful = false;
        
        // Check if Web Share API is available
        if (navigator.share) {
            try {
                // Convert image to blob
                const response = await fetch(imageUrl);
                const blob = await response.blob();
                const file = new File([blob], 'carried-score.png', { type: 'image/png' });
                
                // Share with file
                await navigator.share({
                    title: 'Am I Being Carried?',
                    text: shareText,
                    files: [file],
                    url: siteUrl
                });
                
                shareSuccessful = true;
                showToast(' Shared successfully!', 'success');
                
            } catch (shareError) {
                console.log('Share cancelled or failed:', shareError);
                
                // If user cancelled or share failed, try text-only share
                if (shareError.name !== 'AbortError' && shareError.name !== 'CancelError') {
                    try {
                        // Try text-only share as fallback
                        await navigator.share({
                            title: 'Am I Being Carried?',
                            text: shareText,
                            url: siteUrl
                        });
                        shareSuccessful = true;
                        showToast(' Shared successfully!', 'success');
                    } catch (textError) {
                        console.log('Text share failed:', textError);
                        // Fall through to desktop fallback
                    }
                } else {
                    // User cancelled - show a friendly message
                    showToast(' Share cancelled. Link copied to clipboard instead.', 'info');
                    // Still copy to clipboard
                    await navigator.clipboard.writeText(shareText);
                    shareSuccessful = true;
                }
            }
        }
        
        // If share wasn't successful (or not available), use desktop fallback
        if (!shareSuccessful) {
            // For desktop: just download the image and copy link
            const link = document.createElement('a');
            link.download = 'carried-score.png';
            link.href = imageUrl;
            link.click();
            
            // Copy text to clipboard
            try {
                await navigator.clipboard.writeText(shareText);
                showToast(' Image downloaded! Link copied to clipboard.', 'success');
            } catch (clipError) {
                // If clipboard fails, show manual copy
                showToast(' Image downloaded! Copy this link: ' + shareText, 'info');
            }
        }
        
        // Reset button
        shareBtn.innerHTML = originalText;
        shareBtn.disabled = false;
        
    } catch (error) {
        console.error('Share error:', error);
        showToast(' Failed to share. Please try again.', 'danger');
        
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
        
        // Get player info if available
        const platform = document.body?.dataset?.platform || '';
        const username = document.body?.dataset?.username || '';
        const playerInfo = platform && username ? ` (${platform}/${username})` : '';
        
        const shareText = `I got a ${scoreText} Carried Score${playerInfo}! Check yours at ${siteUrl}`;
        
        // Copy to clipboard
        await navigator.clipboard.writeText(shareText);
        showToast(' Share link copied to clipboard! Share it with your friends.', 'success');
        
        if (copyBtn) {
            copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Link';
                copyBtn.disabled = false;
            }, 2000);
        }
    } catch (error) {
        console.error('Copy error:', error);
        showToast(' Failed to copy. Please try again.', 'danger');
        
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
    
    // Get platform and username from data attributes
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

// Star rating for feedback
let selectedRating = 0;

function setRating(rating) {
    selectedRating = rating;
    document.getElementById('feedbackRating').value = rating;
    
    // Update star display
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

// Submit feedback
async function submitFeedback(event) {
    event.preventDefault();
    
    const name = document.getElementById('feedbackName').value.trim();
    const email = document.getElementById('feedbackEmail').value.trim();
    const rating = parseInt(document.getElementById('feedbackRating').value);
    const message = document.getElementById('feedbackMessage').value.trim();
    const statusDiv = document.getElementById('feedbackStatus');
    
    // Validate
    if (!message) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger alert-sm mb-0">
                <i class="fas fa-exclamation-triangle"></i> Please enter your feedback message.
            </div>
        `;
        return;
    }
    
    // Show loading
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
            // Reset form
            document.getElementById('feedbackForm').reset();
            setRating(0);
            document.getElementById('feedbackRating').value = 0;
            
            // Reset stars
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
        
        // Auto-hide status after 5 seconds
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
        // Add click event listeners
        buttons.forEach(button => {
            button.removeAttribute('onclick');
            button.addEventListener('click', function() {
                selectPlatform(this);
            });
        });
        console.log(' Platform buttons initialized successfully');
    }
    
    // --- Initialize Share Button ---
    const shareButton = document.querySelector('.share-btn');
    if (shareButton) {
        shareButton.addEventListener('click', shareResult);
        console.log(' Share button initialized');
    }

    const copyBtn = document.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', copyShareLink);
        console.log(' Copy button initialized');
    }
    
    // Handle form submission (covers Enter key and button click)
    const form = document.getElementById('apiForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent default form submission
            submitApiForm('apiForm');
        });
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

    // Amount selection
    const amountBtns = document.querySelectorAll('.amount-btn');
    const customAmount = document.getElementById('customAmount');
    const selectedAmount = document.getElementById('selectedAmount');
    
    amountBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active from all
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
    
    customAmount.addEventListener('input', function() {
        if (this.value) {
            selectedAmount.value = this.value;
        }
    });
    
    // Form submission
    document.getElementById('donationForm').addEventListener('submit', async function(e) {
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
        
        // Show loading
        const donateBtn = document.getElementById('donateBtn');
        const originalText = donateBtn.innerHTML;
        donateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        donateBtn.disabled = true;
        
        try {
            // Create payment intent
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
            
            // Confirm payment with Stripe
            const { error } = await stripe.confirmCardPayment(result.client_secret, {
                payment_method: {
                    card: {
                        // Stripe Elements will handle this
                    },
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
            
            // Payment successful - confirm with server
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
                showDonationStatus('🎉 Thank you for your support! Your donation means the world to us.', 'success');
                document.getElementById('donationForm').reset();
                document.querySelectorAll('.amount-btn').forEach(b => b.classList.remove('active'));
                customAmount.style.display = 'none';
                
                // Refresh supporter wall
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
    
    console.log(' All initializations complete');
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

console.log(' All functions loaded and ready');