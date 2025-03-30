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
        try {
            console.log("Displaying results for:", username);
            
            // Safety check: make sure we have the required data
            if (!data) {
                throw new Error("No data received from API");
            }
            
            // Set default values if data structure is incomplete
            const stats = data.stats || {
                profiles_found: 0,
                platforms_checked: 0,
                time_taken: 0,
                date: new Date().toLocaleString(),
                timeouts: 0,
                errors: 0
            };
            
            // Update result summary - safely accessing properties
            try {
                document.getElementById('result-summary').textContent = 
                    `Found ${stats.profiles_found || 0} profiles for username "${username}" across ${stats.platforms_checked || 0} platforms in ${stats.time_taken || 0} seconds`;
            } catch (summaryError) {
                console.error("Error updating summary:", summaryError);
            }
            
            // Update stats - safely
            try {
                document.getElementById('result-username').textContent = username || "Unknown";
                document.getElementById('result-date').textContent = stats.date || "Unknown";
                document.getElementById('result-platforms-checked').textContent = stats.platforms_checked || "0";
                document.getElementById('result-profiles-found').textContent = stats.profiles_found || "0";
                document.getElementById('result-time-taken').textContent = (stats.time_taken || "0") + ' seconds';
                document.getElementById('result-timeouts').textContent = stats.timeouts || "0";
                document.getElementById('result-errors').textContent = stats.errors || "0";
            } catch (statsError) {
                console.error("Error updating stats:", statsError);
            }
            
            // Populate profiles list - with additional safety checks
            try {
                const profilesList = document.getElementById('profiles-list');
                if (!profilesList) throw new Error("Could not find profiles list element");
                
                profilesList.innerHTML = ''; // Clear any previous results
                const profilesFoundContainer = document.getElementById('profiles-found-container');
                const profileCount = document.getElementById('profile-count');
                
                // Get results or empty object if not available
                const results = (data && data.results) ? data.results : {};
                const profileKeys = Object.keys(results);
                
                // Update profile count
                if (profilesFoundContainer) profilesFoundContainer.classList.remove('d-none');
                if (profileCount) profileCount.textContent = profileKeys.length;
                    
                if (profileKeys.length > 0) {
                    // Sort platforms alphabetically for consistent display
                    try {
                        const sortedPlatforms = Object.entries(results).sort((a, b) => a[0].localeCompare(b[0]));
                            
                        // Create a simple list of profiles
                        for (const [platform, url] of sortedPlatforms) {
                            try {
                                if (!platform || !url) continue; // Skip invalid entries
                                
                                const item = createProfileListItem(platform, url);
                                profilesList.appendChild(item);
                            } catch (itemError) {
                                console.error(`Error creating list item for ${platform}:`, itemError);
                                // Create a basic fallback item if there's an error
                                try {
                                    const fallbackItem = document.createElement('div');
                                    fallbackItem.className = 'list-group-item';
                                    fallbackItem.innerHTML = `<div>${platform}: <a href="${url}" target="_blank">${url}</a></div>`;
                                    profilesList.appendChild(fallbackItem);
                                } catch (fallbackError) {
                                    console.error("Error creating fallback item:", fallbackError);
                                }
                            }
                        }
                    } catch (sortError) {
                        console.error("Error sorting profiles:", sortError);
                        // Simple display without sorting
                        for (const platform in results) {
                            try {
                                const url = results[platform];
                                if (!platform || !url) continue; // Skip invalid entries
                                
                                const basicItem = document.createElement('div');
                                basicItem.className = 'list-group-item';
                                basicItem.innerHTML = `<div>${platform}: <a href="${url}" target="_blank">${url}</a></div>`;
                                profilesList.appendChild(basicItem);
                            } catch (entryError) {
                                console.error("Error creating basic entry:", entryError);
                            }
                        }
                    }
                        
                    // Log success message
                    console.log("Successfully displayed", profileKeys.length, "profiles");
                } else {
                    // Show a message when no profiles are found
                    try {
                        const noResults = document.createElement('div');
                        noResults.className = 'alert alert-warning';
                        noResults.innerHTML = '<i class="fa fa-exclamation-triangle me-2"></i> No profiles found for this username.';
                        profilesList.appendChild(noResults);
                    } catch (noResultsError) {
                        console.error("Error showing no results message:", noResultsError);
                    }
                }
            } catch (profilesError) {
                console.error("Error displaying profiles:", profilesError);
                // Show a more user-friendly error
                try {
                    const profilesList = document.getElementById('profiles-list');
                    if (profilesList) {
                        profilesList.innerHTML = '';
                        const errorAlert = document.createElement('div');
                        errorAlert.className = 'alert alert-danger';
                        errorAlert.innerHTML = '<i class="fa fa-exclamation-circle me-2"></i> There was an error displaying the profiles. Please try again.';
                        profilesList.appendChild(errorAlert);
                    }
                } catch (fallbackError) {
                    console.error("Error creating fallback error message:", fallbackError);
                }
            }
            
            // Add reverse image search links if provided
            try {
                const reverseImageContainer = document.getElementById('reverse-image-container');
                const reverseImageLinks = document.getElementById('reverse-image-links');
                
                if (reverseImageContainer && reverseImageLinks && data.reverse_image_urls) {
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
                    
                    // Make sure the reverse_image_urls is an object and not empty
                    if (typeof data.reverse_image_urls === 'object' && Object.keys(data.reverse_image_urls).length > 0) {
                        for (const [engine, url] of Object.entries(data.reverse_image_urls)) {
                            try {
                                if (!engine || !url) continue; // Skip invalid entries
                                
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
                                if (url) { 
                                    link.href = url;
                                    link.target = '_blank';
                                    link.className = 'btn btn-sm btn-outline-info w-100';
                                    link.innerHTML = '<i class="fa fa-external-link me-2"></i>Search on ' + engine;
                                } else {
                                    link.className = 'btn btn-sm btn-outline-secondary w-100 disabled';
                                    link.innerHTML = '<i class="fa fa-exclamation-circle me-2"></i>Link unavailable';
                                }
                                
                                cardFooter.appendChild(link);
                                card.appendChild(cardBody);
                                card.appendChild(cardFooter);
                                colDiv.appendChild(card);
                                reverseImageLinks.appendChild(colDiv);
                            } catch (cardError) {
                                console.error(`Error creating card for ${engine}:`, cardError);
                            }
                        }
                        
                        // If we have image metadata and it's valid, show a preview
                        if (data.image_metadata && data.image_metadata.validated && data.image_metadata.url) {
                            try {
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
                            } catch (previewError) {
                                console.error("Error creating image preview:", previewError);
                            }
                        }
                    } else {
                        // Empty reverse image URLs - display a message
                        try {
                            const noUrls = document.createElement('div');
                            noUrls.className = 'alert alert-info';
                            noUrls.innerHTML = '<i class="fa fa-info-circle me-2"></i> No reverse image search URLs available.';
                            reverseImageLinks.appendChild(noUrls);
                        } catch (noUrlsError) {
                            console.error("Error showing no URLs message:", noUrlsError);
                        }
                    }
                } else {
                    if (reverseImageContainer) {
                        reverseImageContainer.classList.add('d-none');
                    }
                }
            } catch (reverseImageError) {
                console.error("Error processing reverse image search:", reverseImageError);
            }
            
            // Add image metadata if available
            try {
                const imageMetadataContainer = document.getElementById('image-metadata-container');
                const imageMetadataContent = document.getElementById('image-metadata-content');
                
                if (imageMetadataContainer && imageMetadataContent && data.image_metadata) {
                    imageMetadataContainer.classList.remove('d-none');
                    
                    // Clear previous content
                    imageMetadataContent.innerHTML = '';
                    
                    // Create a table for image metadata
                    try {
                        const table = document.createElement('table');
                        table.className = 'table table-sm table-dark table-hover';
                        
                        const tableBody = document.createElement('tbody');
                        
                        for (const [key, value] of Object.entries(data.image_metadata)) {
                            if (!key) continue; // Skip entries without a key
                            
                            const row = document.createElement('tr');
                            const keyCell = document.createElement('td');
                            keyCell.className = 'fw-bold';
                            keyCell.textContent = key;
                            row.appendChild(keyCell);
                            
                            const valueCell = document.createElement('td');
                            valueCell.textContent = value || '';
                            row.appendChild(valueCell);
                            
                            tableBody.appendChild(row);
                        }
                        
                        table.appendChild(tableBody);
                        imageMetadataContent.appendChild(table);
                    } catch (tableError) {
                        console.error("Error creating metadata table:", tableError);
                        
                        // Fallback - simple display
                        const errorMessage = document.createElement('div');
                        errorMessage.className = 'alert alert-info';
                        errorMessage.textContent = 'Image metadata is available but could not be displayed.';
                        imageMetadataContent.appendChild(errorMessage);
                    }
                }
            } catch (imageMetadataError) {
                console.error("Error setting up image metadata:", imageMetadataError);
            }
        } catch (error) {
            console.error("Error in displayResults:", error);
            // Global error handler
            try {
                loadingIndicator.classList.add('d-none');
                
                // Create global error alert
                const alertEl = document.createElement('div');
                alertEl.className = 'alert alert-danger alert-dismissible fade show mt-3';
                alertEl.role = 'alert';
                alertEl.innerHTML = `
                    <i class="fa fa-exclamation-triangle me-2"></i>
                    There was an error processing the results. Please try again.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                
                // Insert after the form
                const formContainer = document.querySelector('.container');
                if (formContainer) {
                    formContainer.appendChild(alertEl);
                }
                
                return; // Exit early
            } catch (fallbackError) {
                console.error("Critical error in error handler:", fallbackError);
                alert("An error occurred. Please refresh the page and try again.");
            }
        }
        
        // Finally, show the results and hide the loading indicator
        try {
            resultsContainer.classList.remove('d-none');
            loadingIndicator.classList.add('d-none');
            
            // Scroll to results
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } catch (finalError) {
            console.error("Error in final display steps:", finalError);
        }
    }
    
    // Create a profile list item
    function createProfileListItem(platform, url) {
        try {
            if (!platform || !url) {
                console.error("Invalid platform or URL provided to createProfileListItem");
                // Return a basic item with an error message
                const errorItem = document.createElement('div');
                errorItem.className = 'list-group-item list-group-item-action text-danger';
                errorItem.innerHTML = '<i class="fa fa-exclamation-circle me-2"></i> Invalid profile data';
                return errorItem;
            }
            
            // Create the main container div instead of <a> to allow for more complex content
            const item = document.createElement('div');
            item.setAttribute('data-platform', platform.toLowerCase());
            item.className = 'list-group-item list-group-item-action';
            
            // Try to add an icon if possible
            const iconClass = getIconClass(platform.toLowerCase());
            
            // Check if we have metadata for this profile
            let metadataHtml = '';
            try {
                if (currentSearchResults && 
                    currentSearchResults.platform_metadata && 
                    currentSearchResults.platform_metadata.detailed_metadata && 
                    currentSearchResults.platform_metadata.detailed_metadata[platform]) {
                    
                    const metadata = currentSearchResults.platform_metadata.detailed_metadata[platform];
                    if (metadata) {
                        // Build metadata section with collapsible details
                        const metadataId = `metadata-${platform.toLowerCase().replace(/[^a-z0-9]/g, '')}`;
                        metadataHtml = `
                            <div class="mt-3 border-top pt-3">
                                <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" 
                                        data-bs-target="#${metadataId}" aria-expanded="false">
                                    <i class="fa fa-info-circle me-1"></i> Show Profile Details
                                </button>
                                <div class="collapse mt-2" id="${metadataId}">
                                    <div class="card card-body bg-dark">
                                        <div class="row">
                                            ${metadata.avatar_url ? 
                                            `<div class="col-md-3 mb-3">
                                                <img src="${metadata.avatar_url}" class="img-fluid rounded" alt="Profile picture">
                                                ${metadata.verified ? '<span class="badge bg-info mt-2 d-block"><i class="fa fa-check-circle"></i> Verified</span>' : ''}
                                            </div>` : ''}
                                            
                                            <div class="${metadata.avatar_url ? 'col-md-9' : 'col-12'}">
                                                ${metadata.name ? `<h5>${metadata.name}</h5>` : ''}
                                                ${metadata.username ? `<p class="mb-1"><strong>Username:</strong> ${metadata.username}</p>` : ''}
                                                ${metadata.bio ? `<p class="mb-2">${metadata.bio}</p>` : ''}
                                                
                                                <div class="row g-2 mb-2">
                                                    ${metadata.followers_count ? 
                                                    `<div class="col-auto">
                                                        <span class="badge bg-secondary">
                                                            <i class="fa fa-users me-1"></i> ${metadata.followers_count} followers
                                                        </span>
                                                    </div>` : ''}
                                                    
                                                    ${metadata.following_count ? 
                                                    `<div class="col-auto">
                                                        <span class="badge bg-secondary">
                                                            <i class="fa fa-user-plus me-1"></i> ${metadata.following_count} following
                                                        </span>
                                                    </div>` : ''}
                                                    
                                                    ${metadata.posts_count ? 
                                                    `<div class="col-auto">
                                                        <span class="badge bg-secondary">
                                                            <i class="fa fa-file-text me-1"></i> ${metadata.posts_count} posts
                                                        </span>
                                                    </div>` : ''}
                                                </div>
                                                
                                                ${metadata.location ? 
                                                `<p class="mb-1"><i class="fa fa-map-marker me-1"></i> ${metadata.location}</p>` : ''}
                                                
                                                ${metadata.website ? 
                                                `<p class="mb-1">
                                                    <i class="fa fa-link me-1"></i> 
                                                    <a href="${metadata.website}" target="_blank">${metadata.website}</a>
                                                </p>` : ''}
                                                
                                                ${metadata.join_date ? 
                                                `<p class="mb-1"><i class="fa fa-calendar me-1"></i> Joined: ${metadata.join_date}</p>` : ''}
                                                
                                                ${metadata.content_sample ? 
                                                `<div class="mt-3">
                                                    <small class="text-muted">Profile content sample:</small>
                                                    <div class="card p-2 bg-secondary mt-1">
                                                        <small>${metadata.content_sample.substring(0, 200)}${metadata.content_sample.length > 200 ? '...' : ''}</small>
                                                    </div>
                                                </div>` : ''}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }
                }
            } catch (metadataError) {
                console.error("Error processing metadata for " + platform, metadataError);
                metadataHtml = ''; // Reset to empty if there's an error
            }
            
            // Main profile section with link
            try {
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <i class="${iconClass} me-3"></i>
                            <div>
                                <div class="fw-bold">${platform}</div>
                                <div class="small text-truncate" style="max-width: 400px;">
                                    <a href="${url}" target="_blank" class="text-info">${url}</a>
                                </div>
                            </div>
                        </div>
                        <div>
                            <a href="${url}" target="_blank" class="btn btn-sm btn-outline-info me-1" title="Open Profile">
                                <i class="fa fa-external-link"></i>
                            </a>
                            <button class="btn btn-sm btn-outline-secondary copy-btn" data-url="${url}" title="Copy URL">
                                <i class="fa fa-clipboard"></i>
                            </button>
                        </div>
                    </div>
                    ${metadataHtml}
                `;
            } catch (htmlError) {
                console.error("Error setting inner HTML for " + platform, htmlError);
                item.innerHTML = `<div class="text-danger">Error creating item for ${platform}</div>`;
                return item;
            }
            
            // Handle copy button click
            try {
                const copyBtn = item.querySelector('.copy-btn');
                if (copyBtn) {
                    copyBtn.addEventListener('click', function(e) {
                        try {
                            e.preventDefault();
                            e.stopPropagation();
                            
                            const url = this.getAttribute('data-url');
                            if (!url) {
                                throw new Error("No URL found to copy");
                            }
                            
                            navigator.clipboard.writeText(url)
                                .then(() => {
                                    // Change button to show copied state
                                    this.innerHTML = '<i class="fa fa-check"></i>';
                                    this.classList.remove('btn-outline-secondary');
                                    this.classList.add('btn-success');
                                    
                                    // Reset after 2 seconds
                                    setTimeout(() => {
                                        this.innerHTML = '<i class="fa fa-clipboard"></i>';
                                        this.classList.remove('btn-success');
                                        this.classList.add('btn-outline-secondary');
                                    }, 2000);
                                })
                                .catch(err => {
                                    console.error('Could not copy text: ', err);
                                    // Alert as fallback
                                    alert('Profile URL: ' + url);
                                });
                        } catch (clickError) {
                            console.error("Error handling copy button click", clickError);
                        }
                    });
                }
            } catch (eventError) {
                console.error("Error setting up event listener for " + platform, eventError);
            }
            
            return item;
        } catch (error) {
            console.error("Error in createProfileListItem:", error);
            // Return a basic item with an error message
            const errorItem = document.createElement('div');
            errorItem.className = 'list-group-item list-group-item-action text-danger';
            errorItem.innerHTML = '<i class="fa fa-exclamation-circle me-2"></i> Error creating profile item';
            return errorItem;
        }
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
