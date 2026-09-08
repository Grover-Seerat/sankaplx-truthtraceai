# TruthTrace Backend

## What is real
- Cases are created in SQLite by API input; no demo cases are seeded.
- Evidence is uploaded as the original file.
- SHA-256, pHash, dimensions, MIME type and metadata are extracted from the uploaded file.
- DINOv2 embeddings are computed from uploaded images and stored for visual similarity.
- Synas Detect 1 is loaded from Hugging Face on first image analysis as the primary AI-generated-image detector. CommunityForensics remains available as an optional second detector.
- CLIP, GeoCLIP and PaddleOCR are invoked from the analysis service.
- Video analysis samples real frames and runs the deepfake detector on those frames.
- Reports are generated from database results.

## Run

From `backend`:

```powershell
python -m venv venv
.\\venv\\Scripts\\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

The first AI inference downloads model weights. DINOv2 is about 346 MB for the safetensors weights; the other models can also be large. A GPU is recommended for practical demo latency.

### PaddleOCR on Windows

PaddleOCR 3.x requires PaddlePaddle 3.0+. Follow the official PaddlePaddle wheel instructions for your CPU/GPU, then install `paddleocr`. If the core stack installs but PaddleOCR does not, the rest of TruthTrace still runs and the API reports the OCR model error rather than fabricating OCR text.

### ffprobe

Install FFmpeg and ensure `ffprobe` is on PATH for video container metadata. If unavailable, video analysis can still sample frames through OpenCV but some container metadata fields will be absent.
