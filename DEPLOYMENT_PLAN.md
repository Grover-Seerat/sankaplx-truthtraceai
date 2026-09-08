# TruthTrace deployment plan

## Recommended architecture
- Frontend: Vite + React on Vercel as a static site.
- Backend: FastAPI on Render or Railway as a long-running Python service.
- Database: move SQLite to PostgreSQL before production.
- File storage: move local `data/uploads` and `data/reports` to object storage (S3-compatible storage) before production.

## Why not put the ML backend on Vercel?
Vercel can run FastAPI, but TruthTrace performs heavyweight Python ML inference. A long-running container service is easier to control for model loading, memory, CPU/GPU needs, ffmpeg and future worker processes.

## Demo authentication
- Admin: `admin@truthtrace.local` / `Admin@123`
- Investigator: `investigator@truthtrace.local` / `Investigator@123`

These are demo credentials only. The current login returns a demo session identifier. Replace this with JWT/OIDC and hashed passwords before production.

## Model strategy
- Primary authenticity detector remains `buildborderless/CommunityForensics-DeepfakeDet-ViT` for the first deployment so model behavior remains comparable to the existing system.
- DINOv2, GeoCLIP, OCR and CLIP should be optional/on-demand rather than mandatory for every Verify Claim request.
- Model names are environment-configurable, so a smaller detector can be benchmarked later without rewriting the UI/API.
