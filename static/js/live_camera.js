// CrimeSketch-ID Multi-Face Live Webcam Client
document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('webcamVideo');
    const canvas = document.getElementById('webcamCanvas');
    const btnStart = document.getElementById('btnStartCamera');
    const btnStop = document.getElementById('btnStopCamera');
    const btnCapture = document.getElementById('btnCaptureFrame');
    const btnAnalyze = document.getElementById('btnAnalyzeWebcam');
    const btnClear = document.getElementById('btnClearWebcam');
    const statusBadge = document.getElementById('cameraStatusBadge');
    const resultsPanel = document.getElementById('webcamResultsPanel');
    const facesSummary = document.getElementById('detectedFacesSummary');
    const facesContainer = document.getElementById('facesListContainer');
    const timingBadge = document.getElementById('webcamTimingBadge');
    const alertBox = document.getElementById('cameraAlert');
    const metricSelect = document.getElementById('webcamMetric');
    const topkSelect = document.getElementById('webcamTopK');

    let stream = null;
    let capturedDataUrl = null;

    if (!video || !canvas) return;

    // Start Camera
    btnStart.addEventListener('click', async () => {
        try {
            hideAlert();
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: false
            });
            video.srcObject = stream;
            video.play();

            statusBadge.textContent = 'Live Feed Active';
            statusBadge.className = 'badge bg-success';
            btnStart.disabled = true;
            btnStop.disabled = false;
            btnCapture.disabled = false;
            btnAnalyze.disabled = false;
        } catch (err) {
            showAlert('Camera access failed or permission denied: ' + err.message);
            statusBadge.textContent = 'Camera Inactive';
            statusBadge.className = 'badge bg-secondary';
        }
    });

    // Stop Camera
    btnStop.addEventListener('click', () => {
        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            video.srcObject = null;
            stream = null;
        }
        statusBadge.textContent = 'Camera Stopped';
        statusBadge.className = 'badge bg-secondary';
        btnStart.disabled = false;
        btnStop.disabled = true;
        btnCapture.disabled = true;
        btnAnalyze.disabled = true;
    });

    // Capture Frame to Canvas
    btnCapture.addEventListener('click', () => {
        captureCurrentFrame();
    });

    function captureCurrentFrame() {
        if (!video.videoWidth) {
            showAlert('Camera stream not ready yet.');
            return null;
        }
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        
        // Mirror horizontally to match mirrored video preview
        ctx.save();
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        ctx.restore();

        capturedDataUrl = canvas.toDataURL('image/jpeg', 0.9);
        showAlert('Frame captured! Click "Analyze Multi-Face" to process.', 'info');
        return capturedDataUrl;
    }

    // Clear Canvas and Results
    btnClear.addEventListener('click', () => {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        capturedDataUrl = null;
        if (resultsPanel) resultsPanel.classList.add('d-none');
        hideAlert();
    });

    // Analyze Webcam Frame
    btnAnalyze.addEventListener('click', async () => {
        hideAlert();
        let frameData = capturedDataUrl;
        if (!frameData) {
            frameData = captureCurrentFrame();
        }
        if (!frameData) {
            showAlert('Could not capture frame. Ensure camera is started.');
            return;
        }

        btnAnalyze.disabled = true;
        btnAnalyze.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Analyzing...`;

        const formData = new FormData();
        formData.append('frame', frameData);
        formData.append('metric', metricSelect ? metricSelect.value : 'cosine');
        formData.append('top_k', topkSelect ? topkSelect.value : '5');

        const csrfToken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');

        try {
            const resp = await fetch('/api/webcam-analyze/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            const data = await resp.json();
            btnAnalyze.disabled = false;
            btnAnalyze.innerHTML = `<i class="bi bi-cpu me-1"></i> Analyze Multi-Face`;

            if (!data.success) {
                showAlert(data.message || data.error || 'No faces recognized.');
                return;
            }

            renderWebcamMultiFaceResults(data);

        } catch (e) {
            btnAnalyze.disabled = false;
            btnAnalyze.innerHTML = `<i class="bi bi-cpu me-1"></i> Analyze Multi-Face`;
            showAlert('Server error during analysis: ' + e.message);
        }
    });

    function showAlert(msg, type = 'danger') {
        if (!alertBox) return;
        alertBox.className = `alert alert-${type} alert-dismissible fade show`;
        alertBox.innerHTML = `<span>${msg}</span><button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        alertBox.classList.remove('d-none');
    }

    function hideAlert() {
        if (alertBox) {
            alertBox.classList.add('d-none');
            alertBox.innerHTML = '';
        }
    }

    function renderWebcamMultiFaceResults(data) {
        if (!resultsPanel) return;
        resultsPanel.classList.remove('d-none');
        resultsPanel.scrollIntoView({ behavior: 'smooth' });

        const count = data.faces_detected || 0;
        facesSummary.textContent = `Detected Faces: ${count}`;
        timingBadge.textContent = `${data.processing_time}s`;

        // Render face results list
        facesContainer.innerHTML = '';
        const faceResults = data.face_results || [];

        faceResults.forEach(face => {
            const topMatch = (face.top_matches && face.top_matches.length > 0) ? face.top_matches[0] : null;
            const topName = topMatch ? topMatch.name : 'No reference match';
            const topSim = topMatch ? topMatch.similarity : 0;
            const topImg = topMatch ? `/media/${topMatch.reference_image}` : '';
            const topConf = topMatch ? topMatch.confidence : 'Low';

            const card = document.createElement('div');
            card.className = 'card mb-3 border shadow-sm';
            
            let candidateRowsHtml = '';
            if (face.top_matches && face.top_matches.length > 0) {
                face.top_matches.forEach(cand => {
                    candidateRowsHtml += `
                        <tr>
                            <td class="fw-bold">${cand.rank}</td>
                            <td><img src="/media/${cand.reference_image}" class="candidate-thumb"></td>
                            <td>
                                <strong>${cand.name}</strong><br>
                                <small class="text-muted">${cand.candidate_id}</small>
                            </td>
                            <td>
                                <span class="fw-bold text-${cand.similarity >= 80 ? 'success' : cand.similarity >= 65 ? 'warning' : 'danger'}">
                                    ${cand.similarity}%
                                </span>
                            </td>
                            <td><span class="badge ${cand.confidence === 'High' ? 'badge-similarity-high' : 'badge-similarity-medium'}">${cand.confidence}</span></td>
                            <td>
                                <a href="/candidates/${cand.candidate_id}/" class="btn btn-sm btn-outline-secondary">
                                    <i class="bi bi-box-arrow-up-right"></i>
                                </a>
                            </td>
                        </tr>
                    `;
                });
            }

            card.innerHTML = `
                <div class="card-header bg-light d-flex justify-content-between align-items-center">
                    <span class="fw-bold text-primary">
                        <i class="bi bi-person-bounding-box me-1"></i> Face #${face.face_index}
                    </span>
                    <span class="badge bg-secondary font-monospace">BBox: [${face.bbox.join(', ')}]</span>
                </div>
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-3 text-center mb-2 mb-md-0">
                            ${topMatch ? `<img src="${topImg}" class="candidate-preview-lg img-thumbnail mb-2" style="max-height: 140px; width: auto;">` : ''}
                            <div class="small text-muted">Potential Similarity Match</div>
                        </div>
                        <div class="col-md-9">
                            <h5 class="mb-1 fw-bold">${topName}</h5>
                            <p class="text-muted mb-2 small">Top Candidate Match for Face #${face.face_index}</p>
                            
                            <div class="d-flex align-items-center gap-3 mb-3">
                                <div>
                                    <span class="fs-4 fw-bold text-${topSim >= 80 ? 'success' : 'primary'}">${topSim}%</span>
                                    <small class="text-muted d-block">Similarity Score</small>
                                </div>
                                <div class="vr"></div>
                                <div>
                                    <span class="badge ${topConf === 'High' ? 'badge-similarity-high' : 'badge-similarity-medium'} fs-6">${topConf}</span>
                                    <small class="text-muted d-block">Confidence Band</small>
                                </div>
                            </div>

                            <button class="btn btn-sm btn-outline-primary" type="button" data-bs-toggle="collapse" data-bs-target="#collapseFace${face.face_index}">
                                <i class="bi bi-list-ol me-1"></i> View All Top Candidates for Face #${face.face_index}
                            </button>
                        </div>
                    </div>

                    <div class="collapse mt-3" id="collapseFace${face.face_index}">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover align-middle mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th>Rank</th>
                                        <th>Portrait</th>
                                        <th>Candidate</th>
                                        <th>Similarity</th>
                                        <th>Confidence</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${candidateRowsHtml}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
            facesContainer.appendChild(card);
        });
    }
});
