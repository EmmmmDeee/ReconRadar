document.addEventListener('DOMContentLoaded', function() {
    // Store search results for export and filtering
    let currentSearchResults = null;
    let currentUsername = null;
    
    // Elements
    const searchForm = document.getElementById('search-form');
    const usernameInput = document.getElementById('username');
    const hasImageCheckbox = document.getElementById('has-image');
    const imageUrlContainer = document.getElementById('image-url-container');
    const imageUrlInput = document.getElementById('image-url');
    const loadingIndicator = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    const exportResultsBtn = document.getElementById('export-results');
    const newSearchBtn = document.getElementById('new-search-btn');
    const profileFilter = document.getElementById('profile-filter');
    
    // Handle image checkbox change with animation
    hasImageCheckbox.addEventListener('change', function() {
        if (this.checked) {
            imageUrlContainer.classList.remove('d-none');
            setTimeout(() => {
                imageUrlContainer.classList.add('animate__animated', 'animate__fadeIn');
            }, 10);
            imageUrlInput.disabled = false;
            imageUrlInput.required = true;
            imageUrlInput.focus();
        } else {
            imageUrlContainer.classList.add('animate__fadeOut');
            setTimeout(() => {
                imageUrlContainer.classList.add('d-none');
                imageUrlContainer.classList.remove('animate__animated', 'animate__fadeIn', 'animate__fadeOut');
                imageUrlInput.disabled = true;
                imageUrlInput.required = false;
                imageUrlInput.value = '';
            }, 500);
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
        
        // Store username for later use
        currentUsername = username;
        
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
            // Debug log to see the structure of the data
            console.log("API Response:", data);
                
            if (data.status === 'success') {
                // Store the results for export
                currentSearchResults = data;
                
                // Display the results
                displayResults(data, username);
            } else {
                // Display error in a more user-friendly way
                loadingIndicator.classList.add('d-none');
                showErrorAlert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingIndicator.classList.add('d-none');
            showErrorAlert('An error occurred while processing your request. Please try again.');
        });
    });
    
    // Function to display error alerts
    function showErrorAlert(message) {
        const alertEl = document.createElement('div');
        alertEl.className = 'alert alert-danger alert-dismissible fade show animate__animated animate__fadeIn';
        alertEl.role = 'alert';
        alertEl.innerHTML = `
            <i class="fa fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert at the top of the form
        const formBody = searchForm.closest('.card-body');
        formBody.insertBefore(alertEl, formBody.firstChild);
        
        // Auto dismiss after 8 seconds
        setTimeout(() => {
            alertEl.classList.add('animate__fadeOut');
            setTimeout(() => alertEl.remove(), 500);
        }, 8000);
    }
    
    // Function to display results
    function displayResults(data, username) {
        // Update result summary
        document.getElementById('result-summary').textContent = 
            `Found ${data.stats.profiles_found} profiles for username "${username}" across ${data.stats.platforms_checked} platforms in ${data.stats.time_taken} seconds`;
        
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
        const profilesFoundContainer = document.getElementById('profiles-found-container');
        const profileCount = document.getElementById('profile-count');
        
        if (Object.keys(data.results).length > 0) {
            profilesFoundContainer.classList.remove('d-none');
            profileCount.textContent = Object.keys(data.results).length;
            
            // Check if we have platform metadata with categories
            if (data.platform_metadata && data.platform_metadata.categories && 
                Object.keys(data.platform_metadata.categories).length > 0) {
                
                try {
                    // Group platforms by category
                    const categories = data.platform_metadata.categories;
                    
                    // Create a header for each category and list platforms underneath
                    for (const [category, platforms] of Object.entries(categories)) {
                        if (!platforms || !Array.isArray(platforms) || platforms.length === 0) {
                            continue; // Skip empty categories
                        }
                        
                        // Create a category header
                        const categoryHeader = document.createElement('div');
                        categoryHeader.className = 'mb-3';
                        categoryHeader.innerHTML = `
                            <h5 class="border-bottom pb-2 text-info">
                                <i class="fa fa-folder-open me-2"></i>${category}
                            </h5>
                        `;
                        profilesList.appendChild(categoryHeader);
                        
                        // Sort platforms alphabetically within category
                        const sortedPlatforms = [...platforms].sort();
                        
                        // Add platforms to this category
                        for (const platform of sortedPlatforms) {
                            if (data.results[platform]) {
                                const item = createProfileListItem(platform, data.results[platform]);
                                
                                // Add response time if available
                                try {
                                    if (data.platform_metadata.response_times && 
                                        data.platform_metadata.response_times[platform]) {
                                        const responseTime = data.platform_metadata.response_times[platform];
                                        
                                        // Add a small indicator for fast responses
                                        if (responseTime < 1) {
                                            const speedBadge = document.createElement('span');
                                            speedBadge.className = 'badge bg-success ms-2';
                                            speedBadge.innerHTML = '<i class="fa fa-bolt"></i> Fast';
                                            
                                            const titleElement = item.querySelector('.fw-bold');
                                            if (titleElement) {
                                                titleElement.appendChild(speedBadge);
                                            }
                                        }
                                    }
                                } catch (e) {
                                    console.error("Error adding response time badge:", e);
                                }
                                
                                profilesList.appendChild(item);
                            }
                        }
                    }
                } catch (e) {
                    console.error("Error displaying categorized results:", e);
                    // Fallback to non-categorized display
                    const sortedPlatforms = Object.entries(data.results).sort((a, b) => a[0].localeCompare(b[0]));
                    for (const [platform, url] of sortedPlatforms) {
                        const item = createProfileListItem(platform, url);
                        profilesList.appendChild(item);
                    }
                }
            } else {
                // Sort platforms alphabetically (fallback if no categories)
                const sortedPlatforms = Object.entries(data.results).sort((a, b) => a[0].localeCompare(b[0]));
                
                for (const [platform, url] of sortedPlatforms) {
                    const item = createProfileListItem(platform, url);
                    profilesList.appendChild(item);
                }
            }
        } else {
            profilesFoundContainer.classList.remove('d-none');
            profileCount.textContent = '0';
            
            // Show a message when no profiles are found
            const noResults = document.createElement('div');
            noResults.className = 'alert alert-warning';
            noResults.innerHTML = '<i class="fa fa-exclamation-triangle me-2"></i> No profiles found for this username.';
            profilesList.appendChild(noResults);
        }
        
        // Add reverse image search links if provided
        const reverseImageContainer = document.getElementById('reverse-image-container');
        const reverseImageLinks = document.getElementById('reverse-image-links');
        
        if (data.reverse_image_urls) {
            reverseImageContainer.classList.remove('d-none');
            reverseImageLinks.innerHTML = '';
            
            // Add status alert if the image metadata exists and is invalidated
            if (data.image_metadata && data.image_metadata.validated === false) {
                try {
                    const errorAlert = document.createElement('div');
                    errorAlert.className = 'alert alert-danger mb-4';
                    const errorMsg = (data.image_metadata.error) ? data.image_metadata.error : 'Invalid image URL provided';
                    errorAlert.innerHTML = `
                        <i class="fa fa-exclamation-circle me-2"></i>
                        <strong>Image validation error:</strong> ${errorMsg}
                        <p class="small mb-0 mt-2">Please make sure the URL points to a valid image file (JPG, PNG, etc.)</p>
                    `;
                    reverseImageLinks.appendChild(errorAlert);
                } catch (e) {
                    console.error("Error displaying image validation message:", e);
                }
            }
            
            for (const [engine, url] of Object.entries(data.reverse_image_urls)) {
                const colDiv = document.createElement('div');
                colDiv.className = 'col';
                
                const card = document.createElement('div');
                card.className = 'card h-100';
                
                const cardBody = document.createElement('div');
                cardBody.className = 'card-body';
                
                // Select icon based on engine
                let engineIcon = 'fa-search';
                let iconColor = 'text-info';
                let engineDescription = 'Find similar images or sources';
                
                if (engine === 'Google') {
                    engineIcon = 'fa-google';
                    iconColor = 'text-danger';
                    engineDescription = 'Powerful visual search with AI-powered image recognition';
                } else if (engine === 'Bing') {
                    engineIcon = 'fa-windows';
                    iconColor = 'text-primary';
                    engineDescription = 'Microsoft\'s image search with visual similarity matching';
                } else if (engine === 'Yandex') {
                    engineIcon = 'fa-search';
                    iconColor = 'text-warning';
                    engineDescription = 'Excellent at finding exact matches and sources';
                } else if (engine === 'Baidu') {
                    engineIcon = 'fa-globe';
                    iconColor = 'text-info';
                    engineDescription = 'China\'s search engine, good for finding Asian sources';
                } else if (engine === 'TinEye') {
                    engineIcon = 'fa-eye';
                    iconColor = 'text-success';
                    engineDescription = 'Specialized reverse image search engine with precise matching';
                }
                
                cardBody.innerHTML = `
                    <h5 class="card-title">
                        <i class="fa ${engineIcon} ${iconColor} me-2"></i>${engine}
                    </h5>
                    <p class="card-text small">${engineDescription}</p>
                `;
                
                const cardFooter = document.createElement('div');
                cardFooter.className = 'card-footer';
                
                const link = document.createElement('a');
                link.href = url;
                link.target = '_blank';
                link.className = 'btn btn-sm btn-outline-info w-100';
                link.innerHTML = '<i class="fa fa-external-link me-2"></i>Search on ' + engine;
                
                cardFooter.appendChild(link);
                card.appendChild(cardBody);
                card.appendChild(cardFooter);
                colDiv.appendChild(card);
                reverseImageLinks.appendChild(colDiv);
            }
            
            // If we have image metadata and it's valid, show a preview
            if (data.image_metadata && data.image_metadata.validated) {
                const previewRow = document.createElement('div');
                previewRow.className = 'row mt-4';
                
                const previewCol = document.createElement('div');
                previewCol.className = 'col-12';
                
                const previewCard = document.createElement('div');
                previewCard.className = 'card';
                
                const previewHeader = document.createElement('div');
                previewHeader.className = 'card-header';
                previewHeader.innerHTML = '<h5 class="mb-0"><i class="fa fa-image me-2"></i>Image Preview</h5>';
                
                const previewBody = document.createElement('div');
                previewBody.className = 'card-body text-center';
                
                const previewImage = document.createElement('img');
                previewImage.src = data.image_metadata.url;
                previewImage.className = 'img-fluid';
                previewImage.style.maxHeight = '200px';
                previewImage.alt = 'Uploaded image';
                
                previewBody.appendChild(previewImage);
                previewCard.appendChild(previewHeader);
                previewCard.appendChild(previewBody);
                previewCol.appendChild(previewCard);
                previewRow.appendChild(previewCol);
                reverseImageLinks.appendChild(previewRow);
            }
        } else {
            reverseImageContainer.classList.add('d-none');
        }
        
        // Hide loading and show results with animation
        loadingIndicator.classList.add('d-none');
        resultsContainer.classList.remove('d-none');
        resultsContainer.classList.add('animate__animated', 'animate__fadeIn');
        
        // Scroll to results smoothly
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Create a profile list item
    function createProfileListItem(platform, url) {
        const item = document.createElement('a');
        item.href = url;
        item.target = '_blank';
        item.setAttribute('data-platform', platform.toLowerCase());
        item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        
        // Try to add an icon if possible
        const iconClass = getIconClass(platform.toLowerCase());
        
        // Create content with verification note
        const content = document.createElement('div');
        content.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="${iconClass} me-3"></i>
                <div>
                    <div class="fw-bold">${platform}</div>
                    <div class="small text-truncate" style="max-width: 400px;">${url}</div>
                </div>
            </div>
        `;
        
        // Add badge
        const badge = document.createElement('span');
        badge.className = 'badge bg-info rounded-pill';
        badge.innerHTML = '<i class="fa fa-external-link"></i>';
        
        item.appendChild(content);
        item.appendChild(badge);
        
        return item;
    }
    
    // Profile filter functionality
    if (profileFilter) {
        profileFilter.addEventListener('input', function() {
            const filterValue = this.value.toLowerCase();
            const profileItems = document.querySelectorAll('#profiles-list .list-group-item');
            
            profileItems.forEach(item => {
                const platform = item.getAttribute('data-platform').toLowerCase();
                if (platform.includes(filterValue)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    // New search button functionality
    if (newSearchBtn) {
        newSearchBtn.addEventListener('click', function() {
            // Hide results, scroll to top of form
            resultsContainer.classList.add('d-none');
            document.querySelector('header').scrollIntoView({ behavior: 'smooth', block: 'start' });
            
            // Focus on username input
            setTimeout(() => {
                usernameInput.focus();
            }, 500);
        });
    }
    
    // Export results functionality
    if (exportResultsBtn) {
        exportResultsBtn.addEventListener('click', function() {
            if (!currentSearchResults || !currentUsername) {
                return;
            }
            
            // Create export object
            const exportData = {
                metadata: {
                    toolName: 'unve1ler',
                    version: currentSearchResults.stats.version || '1.0.2',
                    exportDate: new Date().toISOString(),
                    searchDate: currentSearchResults.stats.date
                },
                searchInfo: {
                    username: currentUsername,
                    platforms_checked: currentSearchResults.stats.platforms_checked,
                    profiles_found: currentSearchResults.stats.profiles_found,
                    time_taken: currentSearchResults.stats.time_taken,
                    timeouts: currentSearchResults.stats.timeouts,
                    errors: currentSearchResults.stats.errors
                },
                results: currentSearchResults.results,
                reverseImageLinks: currentSearchResults.reverse_image_urls,
                platform_metadata: currentSearchResults.platform_metadata || {},
                image_metadata: currentSearchResults.image_metadata || {},
                categorized_results: {}
            };
            
            // Add categorized results if available
            if (currentSearchResults.platform_metadata && 
                currentSearchResults.platform_metadata.categories) {
                Object.entries(currentSearchResults.platform_metadata.categories).forEach(([category, platforms]) => {
                    exportData.categorized_results[category] = {};
                    platforms.forEach(platform => {
                        if (currentSearchResults.results[platform]) {
                            exportData.categorized_results[category][platform] = currentSearchResults.results[platform];
                        }
                    });
                });
            }
            
            // Convert to pretty JSON string
            const dataStr = JSON.stringify(exportData, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
            
            // Create export filename
            const exportFilename = `unve1ler_${currentUsername}_${exportData.metadata.searchDate}.json`;
            
            // Create link and trigger download
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFilename);
            linkElement.click();
        });
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
            'blogspot': 'fa fa-rss',
            'vero': 'fa fa-share-alt',
            'kik': 'fa fa-comments',
            'ebay': 'fa fa-shopping-cart',
            'etsy': 'fa fa-shopping-bag',
            'viber': 'fa fa-phone',
            'tryhackme': 'fa fa-terminal',
            'replit': 'fa fa-code'
        };
        
        return iconMap[platform] || 'fa fa-globe';
    }
});
