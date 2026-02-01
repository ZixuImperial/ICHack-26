// Get DOM elements
const cameraBtn = document.getElementById('cameraBtn');
const uploadBtn = document.getElementById('uploadBtn');
const cameraInput = document.getElementById('cameraInput');
const fileInput = document.getElementById('fileInput');
const uploadSection = document.getElementById('uploadSection');
const previewSection = document.getElementById('previewSection');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');
const previewImage = document.getElementById('previewImage');
const analyzeBtn = document.getElementById('analyzeBtn');
const retakeBtn = document.getElementById('retakeBtn');
const checkAnotherBtn = document.getElementById('checkAnotherBtn');
const resultMain = document.getElementById('resultMain');
const resultSubtext = document.getElementById('resultSubtext');
const binsTextbox = document.getElementById('binsTextbox');
const enterBinsBtn = document.getElementById('enterBinsBtn');
const buildingIndicator = document.getElementById('buildingIndicator');
const buildingName = document.getElementById('buildingName');

let selectedFile = null;
let userLocation = null;
let new_bin_types = [];
let currentBuilding = null;

// Get user's location on page load
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
        async (position) => {
            userLocation = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            };
            console.log('Location acquired:', userLocation);

            // Immediately detect building and load bins
            try {
                const response = await fetch('/get_building_from_location', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(userLocation)
                });

                if (response.ok) {
                    const data = await response.json();
                    currentBuilding = data.building;
                    buildingName.textContent = currentBuilding;
                    buildingIndicator.style.display = 'block';

                    // Update bins display with building-specific bins
                    updateBinsDisplay(data.bins);

                    console.log(`🏢 Building detected on page load: ${currentBuilding}`);
                    console.log(`📦 Loaded bins for building:`, data.bins);
                } else {
                    console.warn('Could not detect building from GPS');
                }
            } catch (error) {
                console.warn('Error detecting building:', error);
            }
        },
        (error) => {
            console.warn('Location access denied or unavailable:', error.message);
        }
    );
}

// Event listeners
cameraBtn.addEventListener('click', () => {
    cameraInput.click();
});

uploadBtn.addEventListener('click', () => {
    fileInput.click();
});

cameraInput.addEventListener('change', handleFileSelect);
fileInput.addEventListener('change', handleFileSelect);
analyzeBtn.addEventListener('click', analyzeImage);
retakeBtn.addEventListener('click', resetToUpload);
checkAnotherBtn.addEventListener('click', resetToUpload);
enterBinsBtn.addEventListener('click', handleEnterBins);
binsTextbox.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        handleEnterBins();
    }
});

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
        selectedFile = file;
        displayPreview(file);
    }
}

// Display image preview
function displayPreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        showSection(previewSection);
    };
    reader.readAsDataURL(file);
}

// Analyze image
async function analyzeImage() {
    if (!selectedFile) {
        alert('Please select an image first');
        return;
    }

    showSection(loadingSection);

    const formData = new FormData();
    formData.append('image', selectedFile);

    // Add GPS coordinates if available
    if (userLocation) {
        formData.append('latitude', userLocation.latitude);
        formData.append('longitude', userLocation.longitude);
    }

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Failed to analyze image');
        }

        const data = await response.json();
        displayResults(data.main_response, data.subtext);

        // Store current building
        if (data.building) {
            currentBuilding = data.building;
            buildingName.textContent = currentBuilding;
            buildingIndicator.style.display = 'block';
            console.log(`🏢 Building detected: ${currentBuilding}`);
        }

        // Update bins display if available
        if (data.available_bins) {
            updateBinsDisplay(data.available_bins);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to analyze the image. Please try again.');
        showSection(previewSection);
    }
}

// Display results
function displayResults(mainResponse, subtext) {
    resultMain.textContent = mainResponse;
    resultSubtext.textContent = subtext;

    // Add styling based on response
    resultMain.classList.remove('recyclable', 'not-recyclable');
    if (mainResponse.toLowerCase().includes('yes') ||
        mainResponse.toLowerCase().includes('recyclable') &&
        !mainResponse.toLowerCase().includes('not')) {
        resultMain.classList.add('recyclable');
    } else if (mainResponse.toLowerCase().includes('no') ||
               mainResponse.toLowerCase().includes('not recyclable')) {
        resultMain.classList.add('not-recyclable');
    }

    showSection(resultsSection);
}

// Update bins display
function updateBinsDisplay(bins) {
    const binsList = document.getElementById('binsList');
    binsList.innerHTML = '';

    bins.forEach(bin => {
        const binTag = document.createElement('span');
        binTag.className = 'bin-tag';
        binTag.textContent = bin;
        binsList.appendChild(binTag);
    });
}

// Handle Enter button for bins
async function handleEnterBins() {
    const inputText = binsTextbox.value.trim();

    if (!inputText) {
        alert('Please enter bin types separated by commas');
        return;
    }

    // Disable button and show loading state
    enterBinsBtn.disabled = true;
    enterBinsBtn.textContent = 'Validating...';

    try {
        // Send to Gemini API for validation
        const response = await fetch('/validate_bins', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                input_text: inputText
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to validate bins');
        }

        const data = await response.json();
        new_bin_types = data.bins;

        // Update the display with validated bin types
        updateBinsDisplay(new_bin_types);

        // Clear the textbox
        binsTextbox.value = '';

        console.log('Validated bin types:', new_bin_types);

        // Save to building database if we have a current building
        if (currentBuilding && currentBuilding !== 'Unknown building') {
            console.log(`Attempting to save bins for building: "${currentBuilding}"`);
            try {
                const updateResponse = await fetch('/update_building_bins', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        building: currentBuilding,
                        bins: new_bin_types
                    })
                });

                const updateData = await updateResponse.json();

                if (updateResponse.ok) {
                    console.log(`✓ Successfully saved bins for building: ${currentBuilding}`, updateData);
                } else {
                    console.error('Failed to update building bins:', updateData);
                }
            } catch (updateError) {
                console.error('Error updating building bins:', updateError);
            }
        } else {
            console.warn(`Not saving bins - currentBuilding is: "${currentBuilding}"`);
            if (!currentBuilding) {
                console.warn('Tip: Analyze an item with GPS first to detect building');
            }
        }

    } catch (error) {
        console.error('Error:', error);
        alert(error.message || 'Failed to validate bin types. Please try again.');
    } finally {
        // Re-enable button
        enterBinsBtn.disabled = false;
        enterBinsBtn.textContent = 'Enter';
    }
}

// Reset to upload screen
function resetToUpload() {
    selectedFile = null;
    cameraInput.value = '';
    fileInput.value = '';
    previewImage.src = '';
    resultMain.textContent = '';
    resultSubtext.textContent = '';

    // Reset bins to default
    updateBinsDisplay(['Recyclable', 'General Waste']);

    showSection(uploadSection);
}

// Show specific section and hide others
function showSection(sectionToShow) {
    const sections = [uploadSection, previewSection, loadingSection, resultsSection];
    sections.forEach(section => {
        section.style.display = 'none';
    });
    sectionToShow.style.display = 'block';
    sectionToShow.classList.add('fade-in');
}

// Initialize
showSection(uploadSection);
