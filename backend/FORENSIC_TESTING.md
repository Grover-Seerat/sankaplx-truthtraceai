# TruthTrace content-agnostic forensic testing

Test the same build with at least these categories:

1. Camera photograph — person
2. Camera photograph — animal/object
3. Camera photograph — landscape/building
4. AI-generated photorealistic person
5. AI-generated photorealistic landscape/object
6. AI-generated illustration/anime/artwork
7. Real painting/illustration
8. Screenshot or UI capture
9. Real image with normal social-media recompression
10. Edited/composited photograph

For every test record:
- SHA-256
- Community Forensics fake probability
- NPR fake probability
- per-view probabilities and spread
- detector class agreement
- manipulation index
- C2PA/metadata state
- final verdict

Important: a detector returning a low fake probability does **not** prove an image is real. If detectors disagree or the content is outside the benchmark domain, the expected result is `Inconclusive`.

The application is designed to classify every uploaded supported image into a forensic outcome (`AI-Generated`, `Likely Authentic`, `Manipulated`, or `Inconclusive`), but it must not claim universal accuracy.
