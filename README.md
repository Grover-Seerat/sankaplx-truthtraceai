# TruthTrace — Fully Integrated Frontend + Forensic Backend

The React frontend no longer reads case/forensic results from `src/data/mockData.ts`. That file has been removed. Case data, evidence, fingerprints, model results, similarity, context, propagation observations, audit trail and reports come from the FastAPI backend.

## Run frontend
```powershell
npm install
npm run dev
```

## Run backend
Open a second terminal:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend: http://localhost:5173
Backend docs: http://localhost:8000/docs

## First analysis
1. Open the frontend.
2. New Investigation.
3. Enter a claim/date/location.
4. Upload an image or video.
5. Open the workspace.
6. The backend computes the fingerprint and runs the forensic models.

## Models and forensic engines
- Community Forensics + NPR — content-agnostic synthetic-image forensic detection.
- DINOv2 (`facebook/dinov2-base`) — image embeddings / Media DNA similarity.
- CLIP (`openai/clip-vit-base-patch32`) — image/claim semantic consistency.
- GeoCLIP — estimated image geolocation supporting signal.
- PaddleOCR — OCR supporting signal.
- pHash — perceptual identity.
- SHA-256 — exact file identity.
- FFprobe/OpenCV — real video metadata and frame sampling.
- C2PA — provenance verification adapter.
- ELA — recompression forensic signal.

Model weights are intentionally NOT bundled in the ZIP. They are downloaded on first use from their model repositories. This keeps the project ZIP manageable and avoids shipping multi-hundred-MB/GB binaries.

## Important
A model score is evidence, not factual truth. The final API verdict is conservative and the UI should be treated as a forensic decision-support tool, not an autonomous fact adjudicator.


## Authentication and role access

TruthTrace uses the existing SQLite database. Startup creates/updates the authentication tables in that same database:

- `users` — server-managed accounts and roles
- `sessions` — hashed, expiring bearer sessions
- `case_assignments` — case-level access control

Three server-assigned roles are included for local development:

| Role | Demo account | Password |
|---|---|---|
| Investigator | `investigator@truthtrace.local` | `Investigator@123` |
| Case Officer | `officer@truthtrace.local` | `Officer@123` |
| Administrator | `admin@truthtrace.local` | `Admin@123` |

The login page does not allow role selection. The backend determines the role from the authenticated account. API permissions and case assignments are enforced server-side. These demo credentials are for local development only and must be replaced before deployment.

### Role dashboard boundaries

- **Investigator:** create investigations, upload evidence, run forensic analysis, review intelligence, generate reports, review audit history.
- **Case Officer:** review assigned cases, evidence, Media DNA, context, propagation, reports and audit history; forensic write operations are restricted.
- **Administrator:** platform-wide case/evidence/intelligence access plus user/role provisioning, case assignment and system governance.

## Forensic AI update

The authenticity pipeline now uses two explicit two-class image detectors:

- **Primary:** `buildborderless/CommunityForensics-DeepfakeDet-ViT` — single-logit synthetic probability; trained across thousands of generators.
- **Secondary:** `NPR-DeepfakeDetection` — neighboring-pixel-relationship detector targeting generalizable synthetic artifacts across GAN and diffusion generators.
- Both detectors are evaluated over multiple aspect-ratio-preserving views.

TruthTrace displays **Fake probability, Real probability, predicted label, model status, and ensemble agreement** instead of exposing only a single AI score. The fusion is deliberately conservative: strong AI findings require corroboration, strong authentic findings require both detectors to be low on synthetic probability, and major disagreement becomes Inconclusive. These are model signals, not ground truth.

### First run

From `backend`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

AI models are downloaded lazily on first analysis. The application accepts arbitrary supported image content; detector probabilities are evidence, not ground truth. Validate the system on a representative labeled benchmark before making accuracy claims.

### Detector configuration

The default configuration is:

```env
DEEPFAKE_MODEL=buildborderless/CommunityForensics-DeepfakeDet-ViT
ENABLE_SECOND_DETECTOR=true
SECOND_DETECTOR_MODEL=NPR-DeepfakeDetection
NPR_WEIGHTS_REPO=siddharthksah/deepsafe-weights
NPR_WEIGHTS_FILE=npr_deepfakedetection/NPR.pth
FORENSIC_VIEWS=5
```

Both models are downloaded on first inference and may be slow on CPU-only machines.

### Propagation

The Propagation page now has **Trace stored evidence**. It compares the current evidence against evidence already stored in TruthTrace using pHash and DINOv2 and creates explicit `AUTO-SIMILARITY` leads. It does not invent social-media history or claim that a URL was observed unless that URL is already stored in a case.

See `backend/FORENSIC_TESTING.md` before evaluating detector accuracy.


## TruthTrace 2.0 investigation extensions

This build adds four connected capabilities:

- **Audio Forensics**: audio evidence is fingerprinted and analysed. A trained Hugging Face audio-classification model is used by default when available; a dependency-light acoustic baseline remains available as a fallback. The model can be changed with `TRUTHTRACE_AUDIO_MODEL`.
- **Investigator Copilot**: case-aware, evidence-grounded chat with controlled access to the current case, analysis, propagation and OSINT results. It does not invent sources.
- **Propagation Intelligence**: existing pHash/DINOv2 stored-evidence tracing is surfaced as a relationship graph and explicitly labelled as similarity leads.
- **Web OSINT**: public-web search over the claim, OCR text and reference URL, with results stored as investigation leads.

### Audio setup

For MP3/M4A/MP4 audio conversion, install FFmpeg and make sure `ffmpeg` is on PATH. The default trained model is `Hemgg/Deepfake-audio-detection` (Apache-2.0). The official AASIST implementation remains a supported research path for a dedicated anti-spoofing adapter: https://github.com/clovaai/aasist

### New workspace tabs

`Audio Forensics`, `Investigator Copilot`, and `Web OSINT` are available in every role workspace. The Investigator, Case Officer and Administrator dashboards also expose the new capabilities.

### Web OSINT note

OSINT results are **leads, not verified facts**. Network access is required on the machine running FastAPI.
