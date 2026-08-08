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
        console.log('🧹 Clearing session...');
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
            showToast('Card not found to share.', 'danger');
            shareBtn.innerHTML = originalText;
            shareBtn.disabled = false;
            return;
        }
        
        // Check if html2canvas is loaded
        if (typeof html2canvas === 'undefined') {
            console.error('html2canvas not loaded');
            showToast('Share library not loaded. Please refresh and try again.', 'danger');
            shareBtn.innerHTML = originalText;
            shareBtn.disabled = false;
            return;
        }
        
        // Get the site URL for the watermark/link
        const siteUrl = window.location.origin;
        
        // Generate image with watermark
        const canvas = await html2canvas(card, {
            scale: 2, // Higher quality
            backgroundColor: '#ffffff',
            allowTaint: true,
            useCORS: true,
            logging: false,
            onclone: function(document) {
                // Ensure all images load properly
                document.querySelectorAll('img').forEach(img => {
                    img.crossOrigin = 'anonymous';
                });
            }
        });
        
        // Add watermark/text to the image
        const ctx = canvas.getContext('2d');
        
        // Draw semi-transparent footer with site URL
        const footerHeight = 40;
        const gradient = ctx.createLinearGradient(0, canvas.height - footerHeight, 0, canvas.height);
        gradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0.7)');
        
        ctx.fillStyle = gradient;
        ctx.fillRect(0, canvas.height - footerHeight, canvas.width, footerHeight);
        
        // Add text (site URL)
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`Check your score at ${siteUrl}`, canvas.width / 2, canvas.height - (footerHeight / 2));
        
        // Add small watermark in corner (optional)
        ctx.font = '12px Arial, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'bottom';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.fillText('Am I Being Carried?', canvas.width - 10, canvas.height - 5);
        
        // Convert to image URL
        const imageUrl = canvas.toDataURL('image/png');
        
        // Get score text
        const scoreElement = document.querySelector('[style*="font-size: 4rem;"]');
        const scoreText = scoreElement?.textContent?.trim() || '??';
        
        // Create share text with link
        const shareText = `I got a ${scoreText} Carried Score! Check yours at ${siteUrl}`;
        
        // Check if Web Share API is available (mobile/desktop sharing)
        if (navigator.share) {
            try {
                // Convert image URL to blob for sharing
                const response = await fetch(imageUrl);
                const blob = await response.blob();
                const file = new File([blob], 'carried-score.png', { type: 'image/png' });
                
                await navigator.share({
                    title: 'Am I Being Carried?',
                    text: shareText,
                    files: [file],
                    url: siteUrl
                });
            } catch (shareError) {
                console.log('Share error (user cancelled or fallback):', shareError);
                // If file sharing fails or user cancels, try text-only share
                try {
                    await navigator.share({
                        title: 'Am I Being Carried?',
                        text: shareText,
                        url: siteUrl
                    });
                } catch (textShareError) {
                    console.log('Text share cancelled or failed');
                    // Fallback to download
                    downloadImageAndCopyLink(imageUrl, shareText);
                }
            }
        } else {
            // Desktop fallback: Download image + copy link
            downloadImageAndCopyLink(imageUrl, shareText);
        }
        
        // Reset button
        shareBtn.innerHTML = originalText;
        shareBtn.disabled = false;
        
    } catch (error) {
        console.error('Share error:', error);
        showToast('❌ Failed to share. Please try again.', 'danger');
        
        // Reset button
        const shareBtn = document.querySelector('.share-btn');
        if (shareBtn) {
            shareBtn.innerHTML = '<i class="fas fa-share-alt"></i> Share';
            shareBtn.disabled = false;
        }
    }
}

// Helper function for desktop fallback
function downloadImageAndCopyLink(imageUrl, shareText) {
    // Download the image
    const link = document.createElement('a');
    link.download = 'carried-score.png';
    link.href = imageUrl;
    link.click();
    
    // Copy text with link to clipboard
    navigator.clipboard.writeText(shareText).then(() => {
        showToast('Image downloaded! Link copied to clipboard.', 'success');
    }).catch(() => {
        // Fallback: show manual copy instructions
        showToast('Image downloaded! Share text: ' + shareText, 'info');
    });
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

// 9. Initialize Everything
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
        console.log('✅ Platform buttons initialized successfully');
    }
    
    // --- Initialize Share Button ---
    const shareButton = document.querySelector('.share-btn');
    if (shareButton) {
        shareButton.addEventListener('click', shareResult);
        console.log('✅ Share button initialized');
    }
    
    // --- Handle Enter key on username field ---
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitApiForm('apiForm');
            }
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
    
    console.log('✅ All initializations complete');
});

// 10. Make functions globally accessible
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

console.log('✅ All functions loaded and ready');