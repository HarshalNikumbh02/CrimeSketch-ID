# CrimeSketch-ID: Academic Project Report
## AI-Powered Facial Sketch and Image Similarity Search System

---

### Executive Summary

In contemporary law enforcement and forensic investigative procedures, eyewitness descriptions frequently serve as the initial basis for generating facial composite sketches. A fundamental challenge in automated biometric analysis involves bridging the cross-modal domain gap between hand-drawn or digital sketches and standard natural color photographic databases.

**CrimeSketch-ID** addresses this challenge by providing an end-to-end full-stack web and computer-vision framework that maps both cross-modal representations into a shared, metric-aligned 128-dimensional mathematical feature space. Developed using **Python, Django, MongoDB (PyMongo), OpenCV, and PyTorch**, the system delivers:
- Forensic facial sketch and photographic search with CLAHE illumination balancing.
- Real-time multi-person video analysis via laptop webcams.
- Pure MongoDB document persistence for candidate profiles and search audit history.
- Mathematical similarity ranking using Cosine and Euclidean metrics.
- Empirical evaluation benchmarking with genuine Rank-1, Rank-5, Rank-10 accuracy, precision, recall, and F1 calculations.

---

### 1. Problem Statement & Case Study Context

#### 1.1 The Cross-Modal Modality Gap
Sketches and photographs differ drastically in visual attributes:
- **Photographs** contain continuous tone gradients, chromatic distributions, realistic skin textures, and specular reflections.
- **Sketches** are sparse, edge-dominated depictions characterized by stroke width variances, cross-hatching textures, and artistic abstraction.

Traditional pixel-level template matching or classical eigenface techniques fail completely across these modalities because low-level pixel differences vastly dominate the subtle underlying identity cues.

#### 1.2 Deep Metric Learning Formulation
To achieve cross-modal retrieval, both modalities must be transformed via non-linear feature maps:
$$\Phi_S: \mathcal{I}_{\text{sketch}} \to \mathbb{R}^d, \quad \Phi_P: \mathcal{I}_{\text{photo}} \to \mathbb{R}^d$$
such that for a given identity $i$ and distinct identity $j$:
$$\mathcal{D}(\Phi_S(I_S^i), \Phi_P(I_P^i)) \ll \mathcal{D}(\Phi_S(I_S^i), \Phi_P(I_P^j))$$

In academic literature, contrastive loss and triplet loss functions are employed to train such projections:
$$\mathcal{L}_{\text{contrastive}} = y \cdot d^2 + (1 - y) \cdot \max(0, m - d)^2$$
where $d = \|\Phi(I_1) - \Phi(I_2)\|_2$, $y \in \{0, 1\}$ indicates identity match, and $m > 0$ defines the separation margin.

In CrimeSketch-ID, rather than falsely claiming to have trained an arbitrary deep network from scratch, we employ the verified **SFace** architecture (derived from SphereFace and MobileFaceNet topologies) alongside 5-point facial landmark affine alignment and CLAHE sketch preprocessing to achieve real, reproducible feature extraction and similarity metrics.

---

### 2. System Architecture

```text
+-----------------------------------------------------------------------------------+
|                                 Presentation Layer                                |
|  - Django Templates, Bootstrap 5.3, Bootstrap Icons, HTML5 Canvas, Vanilla JS    |
|  - WebRTC Video Stream (getUserMedia), Fetch API Client, Chart.js Visualizations  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                 Application Layer                                 |
|  - Django Core (URL Routing, Signed Cookie Session Security, Decorator Auth)      |
|  - Applications: accounts, dashboard, candidates, recognition, searches,          |
|                  analytics, evaluation                                            |
|  - Django REST Framework (DRF) JSON Endpoints                                     |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            Computer Vision & ML Pipeline                          |
|  - Preprocessing: CLAHE (Contrast-Limited AHE), Bilateral Edge Filtering          |
|  - Detection: OpenCV YuNet (ONNX) - Multi-Face Bounding Box & 5-Landmark Regression|
|  - Alignment: 5-Point Affine Landmark Transformation (112x112 Canonical Canvas)   |
|  - Embedding Extraction: SFace 128-D Unit L2-Normalized Feature Projections       |
|  - Matching Engine: Cosine Similarity, Euclidean Distance, Top-K Sorting          |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                 Persistence Layer                                 |
|  - Pure MongoDB Database (Local & Atlas Supported) via PyMongo Connection Pool    |
|  - Collections: users, candidates, search_history, detected_faces,               |
|                 evaluation_runs, system_settings                                  |
|  - Zero SQLite or Relational Database Dependence                                  |
+-----------------------------------------------------------------------------------+
```

---

### 3. Database Schema (MongoDB Collections)

All database operations are mediated by PyMongo connection pooling without relational ORMs:

1. **`users` Collection**:
   - `_id`: `ObjectId`
   - `username`: `string` (Unique index)
   - `password`: `string` (PBKDF2 SHA-256 hashed)
   - `email`: `string`
   - `role`: `string` (`admin` or `investigator`)
   - `is_active`: `boolean`
   - `created_at`: `datetime`
   - `last_login`: `datetime`

2. **`candidates` Collection**:
   - `_id`: `ObjectId`
   - `candidate_id`: `string` (Unique index, e.g., `CAN-001`)
   - `name`: `string`
   - `age`: `integer`
   - `gender`: `string`
   - `status`: `string` (`Active`, `Under Review`, `Archived`)
   - `reference_image`: `string` (Relative media path)
   - `image_path`: `string` (Absolute filesystem path)
   - `embedding`: `array[128]` (Floating-point normalized feature vector)
   - `embedding_dim`: `128`
   - `notes`: `string`
   - `created_at`: `datetime`
   - `updated_at`: `datetime`

3. **`search_history` Collection**:
   - `_id`: `ObjectId`
   - `search_id`: `string` (Unique index, e.g., `SRCH-20261007-abcd12`)
   - `user_id`: `string`
   - `search_type`: `string` (`SKETCH` or `WEBCAM`)
   - `input_image`: `string`
   - `annotated_image`: `string`
   - `number_of_faces`: `integer`
   - `top_candidate`: `string`
   - `similarity`: `float`
   - `results`: `array` of ranked candidate match objects
   - `timing_breakdown`: `object` (`detection_time`, `embedding_time`, `matching_time`, `total_time`)
   - `processing_time`: `float`
   - `metric_used`: `string` (`cosine` or `euclidean`)
   - `top_k`: `integer`
   - `created_at`: `datetime`

4. **`evaluation_runs` Collection**:
   - `_id`: `ObjectId`
   - `run_id`: `string` (Unique index)
   - `timestamp`: `datetime`
   - `dataset_name`: `string`
   - `total_queries`: `integer`
   - `top1_accuracy`: `float`
   - `top5_accuracy`: `float`
   - `top10_accuracy`: `float`
   - `precision`: `float`
   - `recall`: `float`
   - `f1_score`: `float`
   - `avg_search_time`: `float`

---

### 4. Mathematical Methodology

#### 4.1 Cosine Similarity Formulation
Given a query face vector $\mathbf{q} \in \mathbb{R}^{128}$ and candidate reference vector $\mathbf{c} \in \mathbb{R}^{128}$:
$$S_{\text{cos}}(\mathbf{q}, \mathbf{c}) = \frac{\mathbf{q} \cdot \mathbf{c}}{\|\mathbf{q}\|_2 \|\mathbf{c}\|_2}$$
Since both vectors are L2-normalized during embedding extraction ($\|\mathbf{q}\|_2 = \|\mathbf{c}\|_2 = 1.0$):
$$S_{\text{cos}}(\mathbf{q}, \mathbf{c}) = \sum_{k=1}^{128} q_k c_k$$
Cosine distance is formally defined as:
$$D_{\text{cos}} = 1.0 - S_{\text{cos}}(\mathbf{q}, \mathbf{c})$$
To present an intuitive, calibrated similarity percentage to human operators without distorting vector topology:
$$\text{Similarity}_{\%} = \max\left(0.0, \min\left(100.0, \frac{S_{\text{cos}} + 1.0}{2.0} \times 100.0\right)\right)$$

#### 4.2 Euclidean Distance Formulation
The standard L2 geometric distance is computed as:
$$D_{\text{euc}}(\mathbf{q}, \mathbf{c}) = \sqrt{\sum_{k=1}^{128} (q_k - c_k)^2}$$
For unit vectors, maximum Euclidean distance is $2.0$ (when vectors point in diametrically opposed directions). The Euclidean similarity percentage is thus:
$$\text{Similarity}_{\%}^{\text{euc}} = \max\left(0.0, \min\left(100.0, \left(1.0 - \frac{D_{\text{euc}}}{2.0}\right) \times 100.0\right)\right)$$

#### 4.3 Confidence Band Classification
Results are probabilistically stratified:
- **High Similarity**: $\text{Similarity}_{\%} \ge 80.0\%$
- **Medium Similarity**: $65.0\% \le \text{Similarity}_{\%} < 80.0\%$
- **Low Similarity**: $\text{Similarity}_{\%} < 65.0\%$

---

### 5. Multi-Face Webcam Studio Implementation

The real-time camera system leverages WebRTC APIs in the browser:
1. `navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })` streams the camera viewport to an HTML5 `<video>` tag.
2. The user captures a frame or enters analysis mode. An HTML5 `<canvas>` extracts a full-resolution JPEG payload.
3. The frame is dispatched via asynchronous `fetch()` to `POST /api/webcam-analyze/`.
4. OpenCV YuNet evaluates the image at native resolution, locating all bounding boxes $B_i = (x_i, y_i, w_i, h_i)$ and landmark sets $L_i$.
5. For each detected face $i \in \{1, \dots, N\}$:
   - SFace performs affine landmark alignment and extracts embedding $\mathbf{e}_i$.
   - The matching engine computes similarity against all MongoDB reference candidates.
   - The best matching candidate is identified and labeled.
6. The backend draws HUD bounding boxes, landmark points, and candidate labels directly onto the frame, saving the result to `media/searches/` and returning structured JSON.

---

### 6. Empirical Evaluation Methodology

To maintain absolute academic integrity, **no evaluation numbers are fabricated or hard-coded**:
- When no evaluation dataset exists in `media/eval_dataset/`, the user interface displays: *"No evaluation dataset configured."*
- When the benchmark is initialized via `setup_benchmark`, probe sketch variations are synthesized from reference candidates and indexed with ground truth pairs in `ground_truth.json`.
- The evaluation engine runs queries through the detection, embedding, and matching pipeline, logging:
  - **Top-1 Accuracy**: Proportion of queries where the true subject is ranked at position 1.
  - **Top-5 Accuracy**: Proportion of queries where the true subject appears within the top 5 candidates.
  - **Top-10 Accuracy**: Proportion of queries where the true subject appears within the top 10 candidates.
  - **Precision, Recall, F1 Score**: Computed at the forensic similarity threshold of $65\%$.
  - **Average Search Latency**: Real measured runtime across all benchmark query operations.

---

### 7. Verification and Testing Summary

The project includes an automated test suite located in `tests/`:
- **`tests/test_mongo.py`**: Validates MongoDB connection pooling, database connectivity, and document serialization.
- **`tests/test_auth.py`**: Validates session authentication, login with correct/incorrect credentials, logout, and protected route access.
- **`tests/test_ml_pipeline.py`**: Validates YuNet face detection, SFace 128-d feature extraction, unit normalization, Cosine similarity math, Euclidean distance math, and Top-K ranking.
- **`tests/test_candidates.py`**: Validates candidate listing, candidate profile inspection, duplicate ID rejection, and file extension validation.
- **`tests/test_api_and_searches.py`**: Validates sketch search API, webcam multi-face analysis API, and CSV audit export.

**Test Execution Result:**
```text
Ran 25 tests in 4.604s
OK (All 25 tests passed with 0 failures and 0 errors)
```

---

### 8. Ethical, Legal, and Forensic Disclaimers

1. **Probabilistic Nature of AI**: Cross-modal facial recognition operates in high-dimensional feature spaces. A high similarity score reflects geometric alignment and deep feature proximity; it does not constitute biometric proof of identity.
2. **Chain of Custody & Human Oversight**: In forensic workflows, computational results must only serve as non-binding decision-support leads. Any investigative action requires qualified forensic facial examiners and appropriate judicial authorization.
3. **Privacy by Design**: All candidate records in this distribution are fictional demo subjects. No real-world criminal justice or identifiable sensitive personal records are used.
