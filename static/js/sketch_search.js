// CrimeSketch-ID Sketch Search Client
document.addEventListener('DOMContentLoaded', function() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('sketchInput');
    const previewContainer = document.getElementById('previewContainer');
    const previewImg = document.getElementById('previewImg');
    const searchForm = document.getElementById('sketchSearchForm');
    const btnSubmit = document.getElementById('btnSubmitSearch');
    const spinner = document.getElementById('searchSpinner');
    const resultsContainer = document.getElementById('resultsContainer');
    const errorAlert = document.getElementById('errorAlert');

    if (!dropzone || !fileInput) return;

    // Click to open file dialog
    dropzone.addEventListener('click', () => fileInput.click());

    // Drag and drop handlers
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileSelect(fileInput.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.type.match('image.*')) {
            showError('Please upload an image file (JPG, JPEG, or PNG).');
            return;
        }
        hideError();
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewContainer.classList.remove('d-none');
        };
        reader.readAsDataURL(file);
    }

    // Ajax Form Submit
    if (searchForm) {
        searchForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            if (!fileInput.files || fileInput.files.length === 0) {
                showError('Please select or drop an image first.');
                return;
            }

            hideError();
            setLoading(true);

            const formData = new FormData(searchForm);
            const csrfToken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');

            try {
                const response = await fetch('/api/sketch-search/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });

                const data = await response.json();
                setLoading(false);

                if (!data.success) {
                    showError(data.error || 'Face search could not be completed.');
                    if (data.faces_detected === 0) {
                        showError('No face detected. Please upload a clearer image with distinct facial features.');
                    }
                    return;
                }

                renderSearchResults(data);

            } catch (err) {
                setLoading(false);
                showError('Network error or server unavailable: ' + err.message);
            }
        });
    }

    let loadingInterval; // To hold our animation loop

    function setLoading(isLoading) {
        if (isLoading) {
            btnSubmit.disabled = true;
            if (spinner) spinner.classList.remove('d-none');
            if (resultsContainer) resultsContainer.classList.add('opacity-50');
            
            // Trigger CSS Scanner Animation from your custom_2.css
            dropzone.classList.add('scan-effect');

            // "Hollywood" Processing Text Animation
            const loadingPhases = [
                "Initializing YuNet DNN...",
                "Aligning 5-Point Landmarks...",
                "Extracting 128-D SFace Vector...",
                "Computing Similarity Distances...",
                "Ranking Candidate Database..."
            ];
            let phaseIndex = 0;
            
            btnSubmit.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> <span id="loadingText">${loadingPhases[0]}</span>`;
            
            loadingInterval = setInterval(() => {
                phaseIndex = (phaseIndex + 1) % loadingPhases.length;
                const textSpan = document.getElementById('loadingText');
                if (textSpan) textSpan.innerText = loadingPhases[phaseIndex];
            }, 800); // Change text every 800ms

        } else {
            clearInterval(loadingInterval);
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = `<i class="bi bi-search me-1"></i> Detect Face & Rank Candidates`;
            dropzone.classList.remove('scan-effect');

            if (spinner) spinner.classList.add('d-none');
            if (resultsContainer) resultsContainer.classList.remove('opacity-50');
        }
    }

    // --- NEW: Official PDF Report Generation ---
    // --- Official PDF Report Generation ---
    const btnExportPDF = document.getElementById('btnExportPDF');
    if (btnExportPDF) {
        btnExportPDF.addEventListener('click', function() {
            // Check if html2pdf loaded
            if (typeof html2pdf === 'undefined') {
                showError("PDF Library not loaded. Please refresh the page.");
                return;
            }

            // Change button state to show it's working
            const originalText = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Generating PDF...';
            this.disabled = true;

            const element = document.getElementById('pdfExportArea');
            
            // Configuration for html2pdf
            const opt = {
                margin:       [0.5, 0.5, 0.5, 0.5], // top, left, bottom, right
                filename:     'CrimeSketch_Forensic_Report_' + new Date().getTime() + '.pdf',
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#0a0e1a' },
                jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' }
            };

            // Generate the PDF
            html2pdf().set(opt).from(element).save().then(() => {
                // Restore button
                this.innerHTML = originalText;
                this.disabled = false;
            });
        });
    }

    function showError(msg) {
        if (errorAlert) {
            errorAlert.textContent = msg;
            errorAlert.classList.remove('d-none');
        }
    }

    function hideError() {
        if (errorAlert) {
            errorAlert.classList.add('d-none');
            errorAlert.textContent = '';
        }
    }

    function renderSearchResults(data) {
        if (!resultsContainer) return;
        resultsContainer.classList.remove('d-none');
        resultsContainer.scrollIntoView({ behavior: 'smooth' });

        // Update detection info
        const detCountElem = document.getElementById('resFacesCount');
        if (detCountElem) detCountElem.textContent = data.faces_detected;

        const timeElem = document.getElementById('resTotalTime');
        if (timeElem) timeElem.textContent = data.processing_time + ' s';

        const annotatedImgElem = document.getElementById('resAnnotatedImg');
        if (annotatedImgElem) annotatedImgElem.src = data.annotated_image_url;

        // Breakdown timings
        const tb = data.timing_breakdown || {};
        const tDet = document.getElementById('timeDet');
        if (tDet) tDet.textContent = (tb.detection_time || 0) + 's';
        const tEmb = document.getElementById('timeEmb');
        if (tEmb) tEmb.textContent = (tb.embedding_time || 0) + 's';
        const tMatch = document.getElementById('timeMatch');
        if (tMatch) tMatch.textContent = (tb.matching_time || 0) + 's';

        // Render Candidate Table
        const tbody = document.getElementById('candidatesTableBody');
        if (!tbody) return;
        tbody.innerHTML = '';

        const candidates = data.primary_matches || [];
        if (candidates.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No matching candidates in database.</td></tr>`;
            return;
        }

        candidates.forEach(cand => {
            const confClass = cand.confidence === 'High' ? 'badge-similarity-high' :
                             cand.confidence === 'Medium' ? 'badge-similarity-medium' : 'badge-similarity-low';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="fw-bold text-center">${cand.rank}</td>
                <td>
                    <img src="/media/${cand.reference_image}" alt="${cand.name}" class="candidate-thumb shadow-sm">
                </td>
                <td>
                    <div class="fw-semibold">${cand.name}</div>
                    <small class="text-muted">${cand.candidate_id}</small>
                </td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <div class="progress flex-grow-1" style="height: 6px;">
                            <div class="progress-bar ${cand.similarity >= 80 ? 'bg-success' : cand.similarity >= 65 ? 'bg-warning' : 'bg-danger'}" 
                                 style="width: ${cand.similarity}%"></div>
                        </div>
                        <span class="fw-bold">${cand.similarity}%</span>
                    </div>
                </td>
                <td class="text-muted font-monospace">${cand.distance}</td>
                <td>
                    <span class="badge ${confClass}">${cand.confidence}</span>
                </td>
                <td>
                    <a href="/candidates/${cand.candidate_id}/" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-person-badge"></i> Profile
                    </a>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
});
