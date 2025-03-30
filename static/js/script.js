document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const searchForm = document.getElementById('search-form');
    const usernameInput = document.getElementById('username');
    const hasImageCheckbox = document.getElementById('has-image');
    const imageUrlContainer = document.getElementById('image-url-container');
    const imageUrlInput = document.getElementById('image-url');
    const loadingIndicator = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    
    // Handle image checkbox change
    hasImageCheckbox.addEventListener('change', function() {
        if (this.checked) {
            imageUrlContainer.classList.remove('d-none');
            imageUrlInput.disabled = false;
            imageUrlInput.required = true;
        } else {
            imageUrlContainer.classList.add('d-none');
            imageUrlInput.disabled = true;
            imageUrlInput.required = false;
            imageUrlInput.value = '';
        }
    });
    
    // Form submission
    searchForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Form validation
        if (!searchForm.checkValidity()) {
            event.stopPropagation();
            searchForm.classList.add('was-validated');
            return;
        }
        
        // Get form data
        const username = usernameInput.value.trim();
        const imageUrl = hasImageCheckbox.checked ? imageUrlInput.value.trim() : null;
        
        // Show loading, hide results
        loadingIndicator.classList.remove('d-none');
        resultsContainer.classList.add('d-none');
        
        // Make API request
        fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                image_url: imageUrl
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                displayResults(data, username);
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while processing your request. Please try again.');
        })
        .finally(() => {
            loadingIndicator.classList.add('d-none');
        });
    });
    
    // Function to display results
    function displayResults(data, username) {
        // Update stats
        document.getElementById('result-username').textContent = username;
        document.getElementById('result-date').textContent = data.stats.date;
        document.getElementById('result-platforms-checked').textContent = data.stats.platforms_checked;
        document.getElementById('result-profiles-found').textContent = data.stats.profiles_found;
        document.getElementById('result-time-taken').textContent = data.stats.time_taken + ' seconds';
        document.getElementById('result-timeouts').textContent = data.stats.timeouts;
        document.getElementById('result-errors').textContent = data.stats.errors;
        
        // Populate profiles list
        const profilesList = document.getElementById('profiles-list');
        profilesList.innerHTML = '';
        
        if (Object.keys(data.results).length > 0) {
            document.getElementById('profiles-found-container').classList.remove('d-none');
            
            for (const [platform, url] of Object.entries(data.results)) {
                const item = document.createElement('a');
                item.href = url;
                item.target = '_blank';
                item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                
                const platformName = document.createElement('span');
                
                // Try to add an icon if possible
                const iconClass = getIconClass(platform.toLowerCase());
                platformName.innerHTML = `<i class="${iconClass}"></i> ${platform}`;
                
                const badge = document.createElement('span');
                badge.className = 'badge bg-info rounded-pill';
                badge.innerHTML = '<i class="fa fa-external-link"></i>';
                
                item.appendChild(platformName);
                item.appendChild(badge);
                profilesList.appendChild(item);
            }
        } else {
            document.getElementById('profiles-found-container').classList.add('d-none');
        }
        
        // Add reverse image search links if provided
        const reverseImageContainer = document.getElementById('reverse-image-container');
        const reverseImageLinks = document.getElementById('reverse-image-links');
        
        if (data.reverse_image_urls) {
            reverseImageContainer.classList.remove('d-none');
            reverseImageLinks.innerHTML = '';
            
            for (const [engine, url] of Object.entries(data.reverse_image_urls)) {
                const item = document.createElement('a');
                item.href = url;
                item.target = '_blank';
                item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                
                const engineName = document.createElement('span');
                engineName.innerHTML = `<i class="fa fa-search"></i> ${engine}`;
                
                const badge = document.createElement('span');
                badge.className = 'badge bg-info rounded-pill';
                badge.innerHTML = '<i class="fa fa-external-link"></i>';
                
                item.appendChild(engineName);
                item.appendChild(badge);
                reverseImageLinks.appendChild(item);
            }
        } else {
            reverseImageContainer.classList.add('d-none');
        }
        
        // Show results
        resultsContainer.classList.remove('d-none');
    }
    
    // Helper function to get appropriate icon class for a platform
    function getIconClass(platform) {
        // Map platforms to Font Awesome icons where possible
        const iconMap = {
            'instagram': 'fa fa-instagram',
            'twitter': 'fa fa-twitter',
            'facebook': 'fa fa-facebook',
            'linkedin': 'fa fa-linkedin',
            'pinterest': 'fa fa-pinterest',
            'tiktok': 'fa fa-music', // No specific TikTok icon in FA 4.7
            'github': 'fa fa-github',
            'gitlab': 'fa fa-gitlab',
            'reddit': 'fa fa-reddit',
            'youtube': 'fa fa-youtube',
            'tumblr': 'fa fa-tumblr',
            'vimeo': 'fa fa-vimeo',
            'soundcloud': 'fa fa-soundcloud',
            'flickr': 'fa fa-flickr',
            'dribbble': 'fa fa-dribbble',
            'medium': 'fa fa-medium',
            'quora': 'fa fa-quora',
            'steam': 'fa fa-steam',
            'slack': 'fa fa-slack',
            'twitch': 'fa fa-twitch',
            'snapchat': 'fa fa-snapchat',
            'linktr.ee': 'fa fa-link',
            'deviantart': 'fa fa-deviantart',
            'wordpress': 'fa fa-wordpress',
            'blogger': 'fa fa-rss',
            'blogspot': 'fa fa-rss'
        };
        
        return iconMap[platform] || 'fa fa-globe';
    }
});
