# CrimeSketch-ID: AI-Powered Facial Sketch and Image Similarity Search System

> **Tagline:** *"AI-Powered Facial Sketch and Image Similarity Search System"*  
> **Academic Disclaimer:** *This system is an academic/demo similarity-ranking system. Results are probabilistic and must not be treated as definitive identification or evidence of criminal activity.*

---

## 1. Project Overview

**CrimeSketch-ID** is an end-to-end full-stack computer vision application developed for forensic sketch analysis and facial similarity ranking. The platform enables authorized researchers and investigators to:
1. Upload forensic hand-drawn or composite sketches (JPG, JPEG, PNG).
2. Detect faces, landmarks, and apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to balance sketch stroke contrast.
3. Align and project facial features into a 128-dimensional mathematical feature space using deep convolutional neural networks (OpenCV SFace).
4. Rank reference candidates from a **pure MongoDB** candidate database using **Cosine Similarity** and **Euclidean Distance**.
5. Stream real-time video from a laptop webcam to perform **multi-face detection**, simultaneous embedding generation, and live candidate ranking.
6. Track complete search history, telemetry, analytics charts, and rigorous evaluation accuracy benchmarks (Top-1, Top-5, Top-10, Precision, Recall, F1).

---

## 2. Key Features

- **Pure MongoDB Database Integration**: Strictly zero SQLite dependence. All candidate profiles, 128-d vectors, search audits, and evaluations persist directly in MongoDB via PyMongo with support for MongoDB Atlas.
- **Robust Computer Vision Pipeline**:
  - **OpenCV YuNet DNN**: High-accuracy face detection and 5-point facial landmark regression (eyes, nose, mouth corners).
  - **SFace Deep Feature Extractor**: 128-dimensional unit-sphere L2-normalized embedding representation.
  - **Sketch Preprocessing**: Dual-pass CLAHE contrast enhancement and bilateral filtering to normalize pencil grain and paper texture.
- **Interactive Multi-Face Webcam Studio**:
  - Accesses laptop webcam directly via `navigator.mediaDevices.getUserMedia()`.
  - Concurrently detects multiple individuals in the live camera viewport.
  - Generates independent embeddings and similarity rankings for each person.
- **Ranked Similarity Engine**:
  - Exact Cosine Similarity and Euclidean Distance calculations.
  - Configurable Top-K candidate limit (Top 5, Top 10, Top 20, Top 50).
  - Dynamic similarity confidence classification (High $\ge 80\%$, Medium $65-79\%$, Low $< 65\%$).
  - **Strict No-Fake-AI Policy**: Every metric and latency value is mathematically computed from actual tensor operations.
- **Audit History & CSV Export**: Complete historical tracking of every sketch or webcam search with downloadable CSV audit logs.
- **Empirical Evaluation Framework**: True benchmark testing over probe sketches and gallery photos, calculating real Top-1/5/10 accuracy, precision, recall, and F1 scores.

---

## 3. Technology Stack

### Backend
- **Python 3.11+ / 3.14**
- **Django 5.0+** (MVC structure with pure MongoDB session/auth layer)
- **Django REST Framework (DRF)** for JSON API endpoints
- **PyMongo 4.6+** (MongoDB connection pooling and collection management)
- **OpenCV 5.0** (YuNet Face Detector & SFace Feature Recognizer)
- **NumPy & SciPy** (Vector algebra, normalization, and distance metrics)
- **Pillow (PIL)** (Image decoding and manipulation)
- **PyTorch & Torchvision** (Deep learning infrastructure & fallback feature backbones)

### Frontend
- **HTML5 & CSS3**
- **Bootstrap 5.3 & Bootstrap Icons**
- **Vanilla JavaScript & Fetch API** (No heavy frontend frameworks)
- **Chart.js** (Dynamic analytics and telemetry visualization)

### Database
- **MongoDB 7.0+ / 8.0+** (Local or MongoDB Atlas)

---

## 4. Architecture

```text
┌─────────────────────────┐          ┌───────────────────────────┐
│  Forensic Sketch Upload │          │  Live Multi-Face Webcam   │
└────────────┬────────────┘          └─────────────┬─────────────┘
             │                                     │
             ▼                                     ▼
┌────────────────────────────────────────────────────────────────┐
│           OpenCV YuNet Deep Neural Network Detector            │
│         - Bounding Box Extraction & 5-Point Landmarks         │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│            Preprocessing & Affine Landmark Alignment           │
│        - CLAHE Contrast Normalization for Pencil Strokes       │
│        - Affine Transformation to 112x112 Standard Canvas       │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                 SFace Deep Feature Extractor                   │
│        - 128-Dimensional L2 Unit-Sphere Feature Vector         │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│            Mathematical Similarity & Distance Engine           │
│        - Cosine: (u · v) / (||u|| ||v||)                       │
│        - Euclidean: ||u - v||2                                 │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│              MongoDB Reference Gallery (PyMongo)               │
│        - Candidates Collection (Metadata + 128-d Vector)       │
│        - Search History Audit Collection                       │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│              Ranked Candidate Display & Evaluation             │
│        - Top-K Candidate Rankings & Confidence Categorization  │
│        - Audit Trail Logging & Benchmark Metrics (Top-1/5/10)  │
└────────────────────────────────────────────────────────────────┘
```

---

## 5. Installation and Setup

### Step 1: Clone or Open the Repository
```bash
cd crimesketch_id
```

### Step 2: Create and Activate Virtual Environment
**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 6. MongoDB Configuration

CrimeSketch-ID requires a running MongoDB instance.

### Option A: Local MongoDB
Ensure your local MongoDB daemon (`mongod`) is running on port 27017:
```env
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=crimesketch_id
```

### Option B: MongoDB Atlas (Cloud)
To connect to MongoDB Atlas, create a free M0 cluster on [mongodb.com](https://www.mongodb.com/cloud/atlas), create a database user, and configure your connection string in `.env`:
```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=crimesketch_id
```

### Environment File (`.env`)
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Ensure `.env` contains:
```env
SECRET_KEY=your-secure-secret-key-here
DEBUG=True
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=crimesketch_id
```

---

## 7. Seeding Demo Data & Admin User

Run the built-in management command to initialize indexes, default administrator, 6 demo reference candidates, and the evaluation benchmark:

```bash
python manage.py seed_demo_data
```

**Default Administrator Credentials:**
- **Username:** `admin`
- **Password:** `Admin@123`

---

## 8. Running the Application

Start the development server:
```bash
python manage.py runserver
```

Open your browser at:
```text
http://127.0.0.1:8000/
```

1. Log in with `admin` / `Admin@123`.
2. Access the **Dashboard**, **Sketch Search**, **Live Camera**, **Candidates**, **Search History**, **Analytics**, and **Evaluation**.

---

## 9. Running Tests

Run the automated test suite:
```bash
python -m unittest discover tests
```

Expected output:
```text
Ran 25 tests in 4.604s
OK
```

All 25 automated tests cover:
- MongoDB connection and BSON serialization
- User authentication and session security
- Candidate creation, duplicate detection, and file validation
- Face detection, SFace 128-d feature extraction, and alignment
- Cosine similarity and Euclidean distance math
- Candidate ranking and Top-K retrieval
- Sketch Search API (`/api/sketch-search/`)
- Multi-face webcam analysis API (`/api/webcam-analyze/`)
- History audit logging and CSV export

---

## 10. Operational Guide

### 1. Forensic Sketch Search (`/sketch-search/`)
1. Navigate to **Sketch Search**.
2. Select or drag-and-drop a composite facial sketch or image (`sample_sketch_demo.jpg` is provided in `media/searches/`).
3. Select your desired metric (Cosine or Euclidean) and Top-K limit.
4. Click **Detect Face & Rank Candidates**.
5. Review the annotated face preview, latency telemetry, and the ranked candidate table with similarity percentages and confidence ratings.

### 2. Multi-Face Live Webcam Studio (`/live-camera/`)
1. Navigate to **Live Camera**.
2. Click **Start Camera** and permit browser camera access.
3. Direct one or more individuals into the camera frame.
4. Click **Analyze Multi-Face**.
5. The system will detect all visible faces, draw labeled HUD bounding boxes (`Face #1`, `Face #2`, etc.), and display matching reference candidate cards.

### 3. Candidate Management (`/candidates/`)
- Browse all enrolled reference individuals.
- Click **Add New Candidate** to enroll a new portrait.
- The pipeline automatically detects the face, computes its 128-d SFace embedding, and saves the document in MongoDB.

### 4. Empirical Evaluation Benchmark (`/evaluation/`)
- If no dataset is configured, the page displays: *"No evaluation dataset configured."*
- Click **Initialize Demo Benchmark** to construct a controlled probe sketch ground-truth dataset from reference candidates.
- Click **Run Benchmark Evaluation** to compute genuine Rank-1, Rank-5, Rank-10 accuracy, precision, recall, and F1 score across the algorithmic pipeline.

---

## 11. Important Limitations

1. **Cross-Modal Domain Gap**: While CLAHE normalization and deep representation mitigate modality differences, hand-drawn forensic sketches inherently possess stylistic distortions compared to photographic portraits.
2. **Illumination & Pose Variations**: Extreme profile angles (> 45° yaw) or severe occlusions will reduce detection reliability.
3. **Probabilistic Outputs**: High similarity reflects proximity in feature space; it does not constitute identity confirmation or proof of criminal activity.

---

## 12. Ethical & Legal Notice

> **Mandatory Disclaimer:**  
> *CrimeSketch-ID is an academic demonstration of facial similarity search. A similarity score does not establish identity, criminal involvement, or guilt. Results require qualified human review and appropriate legal authorization under applicable laws.*
