import os, hashlib, mimetypes, subprocess, json, math, re, statistics, struct, traceback
from pathlib import Path
from datetime import datetime, timezone

from PIL import Image
import imagehash
import numpy as np

MODEL_CACHE = {}

ORGANIKA_MODEL = os.getenv('ORGANIKA_MODEL', 'Organika/sdxl-detector')
STEGANOGRAPHIA_MODEL = os.getenv('STEGANOGRAPHIA_MODEL', 'delpot/steganograph-ia-detector')
FORENSIC_VIEWS = max(1, int(os.getenv('FORENSIC_VIEWS', '5')))

_FAKE_KEYWORDS = ('fake', 'ai-generated', 'ai generated', 'artificial', 'synthetic', 'deepfake', 'generated', 'manipulated', 'gan', 'diffusion')
_REAL_KEYWORDS = ('real', 'authentic', 'human', 'pristine', 'natural', 'non-manipulated', 'genuine', 'original')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest().upper()


def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest().upper()


def file_signature(path):
    try:
        with open(path, 'rb') as f:
            head = f.read(16)
        if head.startswith(b'\xff\xd8\xff'):
            return 'JPEG image signature'
        if head.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'PNG image signature'
        if head.startswith(b'GIF87a') or head.startswith(b'GIF89a'):
            return 'GIF image signature'
        if head.startswith(b'RIFF') and head[8:12] == b'WEBP':
            return 'WebP image signature'
        if head[4:8] == b'ftyp':
            return 'ISO BMFF/MP4-family signature'
        return 'Unknown/other file signature'
    except Exception as e:
        return f'Unable to read file signature: {e}'


def _json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return value.decode(errors='replace')
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    try:
        return float(value)
    except Exception:
        return str(value)


def exif_metadata(path):
    out = {}
    try:
        im = Image.open(path)
        out['format'] = im.format
        out['width'] = im.width
        out['height'] = im.height
        out['mode'] = im.mode
        out['has_icc_profile'] = bool(im.info.get('icc_profile'))
        out['info_keys'] = sorted(str(k) for k in im.info.keys())
        exif = im.getexif()
        for k, v in exif.items():
            name = str(k)
            try:
                from PIL.ExifTags import TAGS
                name = TAGS.get(k, str(k))
            except Exception:
                pass
            out[str(name)] = _json_safe(v)
        if getattr(im, 'applist', None):
            out['jpeg_app_markers'] = [str(x[0]) for x in im.applist if isinstance(x, (list, tuple)) and x]
        if getattr(im, 'quantization', None):
            q = im.quantization
            vals = []
            for table_id, table in q.items():
                vals.append({'table': int(table_id), 'length': len(table), 'mean': round(float(np.mean(table)), 3), 'min': int(min(table)), 'max': int(max(table))})
            out['jpeg_quantization_tables'] = vals
        if 'exif' in im.info:
            out['has_exif_block'] = True
    except Exception as e:
        out['image_parse_error'] = str(e)
    return out


def video_metadata(path):
    try:
        p = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(path)],
            capture_output=True, text=True, timeout=20
        )
        if p.returncode == 0:
            data = json.loads(p.stdout)
            fmt = data.get('format', {})
            streams = data.get('streams', [])
            v = next((s for s in streams if s.get('codec_type') == 'video'), {})
            return {
                'format': fmt.get('format_name'),
                'duration': float(fmt['duration']) if fmt.get('duration') else None,
                'size': int(fmt['size']) if fmt.get('size') else None,
                'codec': v.get('codec_name'),
                'width': v.get('width'),
                'height': v.get('height'),
                'fps': v.get('r_frame_rate'),
                'creation_time': fmt.get('tags', {}).get('creation_time'),
                'tags': fmt.get('tags', {}),
            }
    except Exception:
        pass
    return {}


def _media_stream_kind(path):
    """Use ffprobe when available to distinguish audio-only MPEG/container files."""
    try:
        r = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_type','-of','default=nw=1:nk=1',str(path)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15)
        has_video = bool(r.stdout.strip())
        r = subprocess.run(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=codec_type','-of','default=nw=1:nk=1',str(path)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15)
        has_audio = bool(r.stdout.strip())
        if has_audio and not has_video:
            return 'audio'
        if has_video:
            return 'video'
    except Exception:
        pass
    return None


def fingerprint(path):
    mime = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
    kind = _media_stream_kind(path)
    if kind == 'audio' and not mime.startswith('audio/'):
        mime = 'audio/mpeg' if Path(path).suffix.lower() in {'.mpeg','.mpg','.mp2','.mp3'} else 'audio/*'
    stat = Path(path).stat()
    data = {
        'mime_type': mime,
        'sha256': sha256_file(path),
        'md5': md5_file(path),
        'size': stat.st_size,
        'file_signature': file_signature(path),
    }
    if mime.startswith('image/'):
        md = exif_metadata(path)
        data.update({'width': md.get('width'), 'height': md.get('height'), 'metadata': md})
        try:
            im = Image.open(path).convert('RGB')
            data['phash'] = str(imagehash.phash(im))
            data['dhash'] = str(imagehash.dhash(im))
            data['ahash'] = str(imagehash.average_hash(im))
        except Exception:
            data['phash'] = data['dhash'] = data['ahash'] = None
    elif mime.startswith('video/'):
        md = video_metadata(path)
        data.update({'duration': md.get('duration'), 'width': md.get('width'), 'height': md.get('height'), 'metadata': md})
    else:
        data['metadata'] = {}
    data['dna_id'] = 'TT-' + data['sha256'][:10]
    return data


def load_dino():
    key = 'dino'
    if key in MODEL_CACHE:
        return MODEL_CACHE[key]
    from transformers import AutoImageProcessor, AutoModel
    name = os.getenv('DINO_MODEL', 'facebook/dinov2-base')
    proc = AutoImageProcessor.from_pretrained(name)
    model = AutoModel.from_pretrained(name)
    model.eval()
    MODEL_CACHE[key] = (proc, model)
    return proc, model


def dino_embedding(path):
    try:
        import torch
        proc, model = load_dino()
        im = Image.open(path).convert('RGB')
        inputs = proc(images=im, return_tensors='pt')
        with torch.no_grad():
            out = model(**inputs).last_hidden_state[:, 0, :]
        v = out[0].cpu().numpy().astype('float32')
        v /= max(np.linalg.norm(v), 1e-8)
        return v.tolist()
    except Exception as e:
        return {'error': str(e)}


def _cuda_device():
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except Exception:
        return 'cpu'


def _image_views(image, count=5):
    """Aspect-ratio-preserving whole-image + regional forensic views."""
    im = image.convert('RGB')
    if count <= 1: return [im]
    w, h = im.size; side = min(w, h)
    if w == h: return [im]
    boxes = [(0, 0, w, h)]
    if w >= h:
        x = w - side
        boxes += [(0, 0, side, h), (x, 0, w, h), ((w-side)//2, 0, (w-side)//2+side, h)]
    else:
        y = h - side
        boxes += [(0, 0, w, side), (0, y, w, h), (0, (h-side)//2, w, (h-side)//2+side)]
    return [im.crop(b) for b in boxes[:count]]

def _identify_fake_index(id2label):
    fake_idx = real_idx = None
    for i, l in id2label.items():
        ll = str(l).lower()
        if fake_idx is None and any(k in ll for k in _FAKE_KEYWORDS):
            fake_idx = int(i)
        if real_idx is None and any(k in ll for k in _REAL_KEYWORDS):
            real_idx = int(i)
    if fake_idx is None and real_idx is not None and len(id2label) == 2:
        fake_idx = [int(i) for i in id2label if int(i) != real_idx][0]
    if fake_idx is None:
        raise RuntimeError(
            f"Could not identify the 'fake/AI-generated' class from id2label={id2label}. "
            f"Refusing to guess which index is 'fake' to avoid silently inverting predictions."
        )
    return fake_idx

def load_classifier(model_name, cache_key):
    if cache_key in MODEL_CACHE: return MODEL_CACHE[cache_key]
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    processor = AutoImageProcessor.from_pretrained(model_name)
    model = AutoModelForImageClassification.from_pretrained(model_name)
    id2label = getattr(model.config, 'id2label', None) or {}
    num_labels = getattr(model.config, 'num_labels', None) or (len(id2label) if id2label else 1)
    fake_index = _identify_fake_index(id2label) if num_labels and num_labels > 1 else 0
    device = _cuda_device(); model.to(device); model.eval()
    MODEL_CACHE[cache_key] = (processor, model, device, num_labels, fake_index, id2label)
    return MODEL_CACHE[cache_key]

def _classify_one(image, processor, model, device, num_labels, fake_index):
    import torch
    inputs = processor(images=image, return_tensors='pt'); inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad(): logits = model(**inputs).logits
    logits = logits.reshape(-1)
    if num_labels and num_labels > 1:
        probs = torch.softmax(logits, dim=0)
        return float(probs[fake_index].detach().cpu().item())
    return _sigmoid(float(logits[0].detach().cpu().item()))

def _run_classifier(path, model_name, cache_key, scope):
    try:
        import statistics
        image = Image.open(path).convert('RGB')
        processor, model, device, num_labels, fake_index, id2label = load_classifier(model_name, cache_key)
        probs = [_classify_one(v, processor, model, device, num_labels, fake_index) for v in _image_views(image, FORENSIC_VIEWS)]
        fake_p = float(statistics.median(probs))
        spread = round(max(probs) - min(probs), 6) if len(probs) > 1 else None
        out = {'model': model_name, 'status': 'ok', 'output_type': 'softmax_fake_class' if num_labels and num_labels > 1 else 'single_logit_sigmoid',
               'device': device, 'id2label': id2label,
               'fake_probability': round(fake_p, 6), 'real_probability': round(1 - fake_p, 6), 'ai_probability': round(fake_p, 6),
               'predicted_label': 'Fake' if fake_p >= .5 else 'Real', 'views_analyzed': len(probs),
               'view_fake_probabilities': [round(x, 6) for x in probs], 'view_spread': spread,
               'scope': scope}
        if spread is not None and spread < 0.001 and len(probs) > 1:
            out['warning'] = 'Near-zero variance across image views. This can indicate a broken/degenerate model checkpoint rather than a genuine confident prediction.'
        return out
    except Exception as e:
        return {'model': model_name, 'status': 'error', 'error': str(e), 'error_type': type(e).__name__, 'traceback': traceback.format_exc(), 'scope': scope}

def deepfake(path):
    """Run the two AI-image detectors used by the adaptive fusion layer.

    Organika and SteganographIA are both evaluated on the same forensic views.
    The final verdict is produced later by ``fuse()``, which gives extra weight
    to SteganographIA when Organika strongly says "AI" while SteganographIA
    strongly says "real".
    """
    organika = _run_classifier(
        path,
        ORGANIKA_MODEL,
        'organika_detector',
        'AI-vs-real detector; adaptive-fusion input'
    )
    steganographia = _run_classifier(
        path,
        STEGANOGRAPHIA_MODEL,
        'steganographia_detector',
        'AI-vs-real detector; adaptive-fusion input'
    )

    # Keep a compact aggregate object under models['deepfake'] for compatibility
    # with the existing backend. The actual verdict is calculated in fuse().
    return {
        'model': 'adaptive_fusion',
        'status': 'ok' if organika.get('status') == 'ok' and steganographia.get('status') == 'ok' else 'partial',
        'fusion_inputs': {
            'organika': organika,
            'steganographia': steganographia,
        },
        'organika': organika,
        'steganographia': steganographia,
        'scope': 'two-detector adaptive AI-vs-real detection',
    }


def clip_claim_score(path, claim):
    try:
        from transformers import CLIPProcessor, CLIPModel
        key = 'clip'
        if key not in MODEL_CACHE:
            name = os.getenv('CLIP_MODEL', 'openai/clip-vit-base-patch32')
            MODEL_CACHE[key] = (CLIPProcessor.from_pretrained(name), CLIPModel.from_pretrained(name))
        proc, model = MODEL_CACHE[key]
        inputs = proc(text=[claim, 'An unrelated image'], images=Image.open(path).convert('RGB'), return_tensors='pt', padding=True)
        import torch
        with torch.no_grad():
            logits = model(**inputs).logits_per_image.softmax(dim=1)[0]
        return {'claim_alignment': float(logits[0]), 'model': os.getenv('CLIP_MODEL', 'openai/clip-vit-base-patch32')}
    except Exception as e:
        return {'error': str(e)}


def geoclip(path):
    try:
        from geoclip import GeoCLIP
        model = MODEL_CACHE.get('geoclip') or GeoCLIP()
        MODEL_CACHE['geoclip'] = model
        gps, probs = model.predict(path, top_k=5)
        return {'predictions': [{'lat': float(g[0]), 'lon': float(g[1]), 'probability': float(p)} for g, p in zip(gps, probs)]}
    except Exception as e:
        return {'error': str(e)}


def ocr(path):
    try:
        from paddleocr import PaddleOCR
        if 'ocr' not in MODEL_CACHE:
            MODEL_CACHE['ocr'] = PaddleOCR(lang='en')
        result = MODEL_CACHE['ocr'].predict(path)
        texts = []
        for page in result:
            for t in page.get('rec_texts', []):
                if t and str(t).strip():
                    texts.append(str(t).strip())
        return {'text': texts}
    except Exception as e:
        return {'error': str(e)}


def video_frames(path, n=16):
    import cv2, tempfile
    cap = cv2.VideoCapture(str(path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idxs = np.linspace(0, max(total - 1, 0), min(n, max(total, 1))).astype(int)
    frames = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if not ok:
            continue
        p = Path(tempfile.gettempdir()) / f'truthtrace_{os.getpid()}_{idx}.jpg'
        cv2.imwrite(str(p), frame)
        frames.append(str(p))
    cap.release()
    return frames


def ela_score(path):
    try:
        import cv2, tempfile
        im = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if im is None:
            return {'error': 'unreadable image'}
        tmp = Path(tempfile.gettempdir()) / f'truthtrace_ela_{os.getpid()}.jpg'
        cv2.imwrite(str(tmp), im, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        recom = cv2.imread(str(tmp))
        diff = cv2.absdiff(im, recom)
        score = float(np.mean(diff)) / 255.0
        try:
            tmp.unlink()
        except Exception:
            pass
        return {'mean_difference': round(score, 6), 'note': 'ELA is a forensic signal, not proof of editing.'}
    except Exception as e:
        return {'error': str(e)}


def image_noise_stats(path):
    try:
        import cv2
        im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if im is None:
            return {'error': 'unreadable image'}
        blur = cv2.GaussianBlur(im, (3, 3), 0)
        residual = im.astype(np.float32) - blur.astype(np.float32)
        return {
            'residual_std': round(float(np.std(residual)), 5),
            'high_frequency_energy': round(float(np.mean(np.abs(residual))), 5),
            'note': 'Noise statistics are supporting evidence and are not a standalone authenticity test.'
        }
    except Exception as e:
        return {'error': str(e)}


def transcoding_signals(path):
    try:
        im = Image.open(path)
        md = exif_metadata(path)
        reasons = []
        score = 0.0
        if im.format == 'JPEG':
            qtables = md.get('jpeg_quantization_tables', []) or []
            qmeans = [float(x.get('mean')) for x in qtables if x.get('mean') is not None]
            long_edge = max(im.size)
            has_camera = any(md.get(k) for k in ('Make', 'Model', 'DateTimeOriginal'))
            if not md.get('has_exif_block') and not has_camera:
                score += 0.30
                reasons.append('JPEG has no camera EXIF metadata; common after messaging-app recompression.')
            if long_edge <= 1600:
                score += 0.25
                reasons.append(f'JPEG long edge is {long_edge}px, consistent with a resized/shared copy.')
            if qmeans and max(qmeans) >= 25:
                score += 0.25
                reasons.append('JPEG quantization indicates noticeable lossy compression.')
            if len(qtables) == 1:
                score += 0.10
                reasons.append('Single JPEG quantization table observed.')
        score = min(score, 1.0)
        return {
            'likely_transcoded': score >= 0.55,
            'score': round(score, 4),
            'source': 'file-level heuristics; cannot identify WhatsApp specifically',
            'reasons': reasons,
            'note': 'Transcoding/recompression is not evidence of AI generation or authenticity.'
        }
    except Exception as e:
        return {'likely_transcoded': False, 'score': 0.0, 'reasons': [], 'error': str(e)}


def manipulation_signals(path):
    try:
        im = Image.open(path)
        md = exif_metadata(path)
        software = str(md.get('Software', '') or '')
        exif_present = bool(getattr(im, 'getexif', lambda: {})())
        quant = md.get('jpeg_quantization_tables', [])
        score = 0.0
        reasons = []
        if software:
            score += 0.25
            reasons.append(f'Embedded software tag: {software}')
        if not exif_present and im.format in {'JPEG', 'TIFF'}:
            reasons.append('No EXIF block present; this is common after recompression and is not proof of editing.')
        if im.format == 'JPEG' and len(quant) == 1:
            reasons.append('Single JPEG quantization table observed.')
        if md.get('has_icc_profile'):
            reasons.append('Embedded ICC color profile present.')
        ela = ela_score(path)
        if isinstance(ela, dict) and ela.get('mean_difference') is not None:
            e = float(ela['mean_difference'])
            if e > 0.08:
                score += 0.20
                reasons.append('Higher recompression difference observed by ELA.')
        score = min(score, 1.0)
        return {'index': round(score, 4), 'reasons': reasons, 'note': 'Manipulation index is a supporting signal, not proof.'}
    except Exception as e:
        return {'error': str(e)}


def c2pa_verify(path):
    try:
        import c2pa
        if hasattr(c2pa, 'Reader'):
            reader = c2pa.Reader(str(path))
            manifest = reader.json()
            return {'available': True, 'present': True, 'manifest': manifest}
        return {'available': True, 'present': False, 'note': 'c2pa-python installed but Reader API is unavailable in this build.'}
    except Exception as e:
        return {'available': False, 'present': False, 'error': str(e)}


def _date_from_any(value):
    if not value:
        return None
    s = str(value).strip().replace('Z', '+00:00')
    s = re.sub(r'^(\d{4}):(\d{2}):(\d{2})', r'\1-\2-\3', s)
    for fmt in (None, '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S%z'):
        try:
            return datetime.fromisoformat(s) if fmt is None else datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def temporal_consistency(metadata, claimed_date):
    capture = metadata.get('DateTimeOriginal') or metadata.get('DateTime') or metadata.get('creation_time')
    cap_dt = _date_from_any(capture)
    claim_dt = _date_from_any(claimed_date)
    if not claim_dt or not cap_dt:
        return {'status': 'unknown', 'capture_time': str(capture) if capture else None, 'claimed_date': claimed_date or None}
    if cap_dt.tzinfo is None:
        cap_dt = cap_dt.replace(tzinfo=timezone.utc)
    if claim_dt.tzinfo is None:
        claim_dt = claim_dt.replace(tzinfo=timezone.utc)
    delta_days = abs((cap_dt - claim_dt).total_seconds()) / 86400.0
    return {
        'status': 'consistent' if delta_days <= 2 else 'mismatch',
        'capture_time': cap_dt.isoformat(),
        'claimed_date': claim_dt.isoformat(),
        'difference_days': round(delta_days, 2),
        'note': 'Embedded timestamps can be edited or stripped; use as contextual evidence only.'
    }


# Adaptive two-detector verdict
# -----------------------------
# Organika + SteganographIA are both used as AI-vs-real detectors.
# Under strong disagreement, SteganographIA receives more weight because
# the target failure mode is false AI positives on genuine/recompressed photos.

DETECTOR_FAKE_THRESHOLD = float(os.getenv('DETECTOR_FAKE_THRESHOLD', '0.50'))
STRONG_FAKE_THRESHOLD = float(os.getenv('STRONG_FAKE_THRESHOLD', '0.75'))
STRONG_REAL_THRESHOLD = float(os.getenv('STRONG_REAL_THRESHOLD', '0.25'))

ORGANIKA_WEIGHT_NORMAL = float(os.getenv('ORGANIKA_WEIGHT_NORMAL', '0.50'))
STEGANOGRAPHIA_WEIGHT_NORMAL = float(os.getenv('STEGANOGRAPHIA_WEIGHT_NORMAL', '0.50'))
ORGANIKA_WEIGHT_DISAGREE = float(os.getenv('ORGANIKA_WEIGHT_DISAGREE', '0.20'))
STEGANOGRAPHIA_WEIGHT_DISAGREE = float(os.getenv('STEGANOGRAPHIA_WEIGHT_DISAGREE', '0.80'))
ORGANIKA_WEIGHT_TRANSCODE_DISAGREE = float(os.getenv('ORGANIKA_WEIGHT_TRANSCODE_DISAGREE', '0.10'))
STEGANOGRAPHIA_WEIGHT_TRANSCODE_DISAGREE = float(os.getenv('STEGANOGRAPHIA_WEIGHT_TRANSCODE_DISAGREE', '0.90'))

STRONG_DISAGREEMENT_FAKE = float(os.getenv('STRONG_DISAGREEMENT_FAKE', '0.80'))
STRONG_DISAGREEMENT_REAL = float(os.getenv('STRONG_DISAGREEMENT_REAL', '0.30'))

def _detector_score(detector):
    if not isinstance(detector, dict) or detector.get('status') != 'ok':
        return None
    score = detector.get('fake_probability', detector.get('ai_probability'))
    if score is None:
        return None
    return max(0.0, min(1.0, float(score)))


def fuse(r):
    aggregate = r.get('models', {}).get('deepfake', {}) or {}
    organika = aggregate.get('organika', {}) or {}
    steganographia = aggregate.get('steganographia', {}) or {}
    o_score = _detector_score(organika)
    s_score = _detector_score(steganographia)

    if o_score is None and s_score is None:
        return {
            'label': 'Inconclusive',
            'confidence': 0,
            'ai_probability': None,
            'fake_probability': None,
            'real_probability': None,
            'fusion_mode': 'adaptive_two_detector',
            'detectors': [ORGANIKA_MODEL, STEGANOGRAPHIA_MODEL],
            'reason': 'Neither AI-image detector returned a usable prediction.',
            'disclaimer': 'AI detectors provide evidence, not mathematical proof of authenticity.'
        }

    # Graceful degradation if one detector fails.
    if o_score is None:
        final_score = s_score
        mode = 'steganographia_only_fallback'
        weights = {'organika': 0.0, 'steganographia': 1.0}
    elif s_score is None:
        final_score = o_score
        mode = 'organika_only_fallback'
        weights = {'organika': 1.0, 'steganographia': 0.0}
    else:
        strong_disagreement = (
            o_score >= STRONG_DISAGREEMENT_FAKE
            and s_score <= STRONG_DISAGREEMENT_REAL
        )
        reverse_disagreement = (
            s_score >= STRONG_DISAGREEMENT_FAKE
            and o_score <= STRONG_DISAGREEMENT_REAL
        )

        likely_transcoded = bool(
            r.get('signals', {}).get('transcoding', {}).get('likely_transcoded')
        )

        if strong_disagreement:
            if likely_transcoded:
                ow = ORGANIKA_WEIGHT_TRANSCODE_DISAGREE
                sw = STEGANOGRAPHIA_WEIGHT_TRANSCODE_DISAGREE
                mode = 'strong_disagreement_transcoded_photo'
                reason_prefix = (
                    'Strong detector disagreement detected: Organika reports a high synthetic signal, '
                    'while SteganographIA reports a strong real signal. Transcoding/recompression evidence '
                    'is also present, so the final score gives substantially more weight to SteganographIA.'
                )
            else:
                ow = ORGANIKA_WEIGHT_DISAGREE
                sw = STEGANOGRAPHIA_WEIGHT_DISAGREE
                mode = 'strong_disagreement_steganographia_favored'
                reason_prefix = (
                    'Strong detector disagreement detected: Organika reports a high synthetic signal, '
                    'while SteganographIA reports a strong real signal. The final score therefore gives '
                    'more weight to SteganographIA rather than allowing one extreme Organika score to dominate.'
                )
        elif reverse_disagreement:
            # Be cautious in the opposite direction: SteganographIA is favored,
            # but not with the aggressive 90% weighting used for the known false-
            # positive direction.
            ow = 0.30
            sw = 0.70
            mode = 'reverse_disagreement_steganographia_favored'
            reason_prefix = (
                'The detectors disagree in the opposite direction. SteganographIA is given a modestly higher '
                'weight, while Organika remains a substantial counter-signal.'
            )
        else:
            ow = ORGANIKA_WEIGHT_NORMAL
            sw = STEGANOGRAPHIA_WEIGHT_NORMAL
            mode = 'normal_two_detector_fusion'
            reason_prefix = (
                'The detectors do not show the strong disagreement pattern targeted by the adaptive rule, '
                'so their probabilities are combined using the normal fusion weights.'
            )

        weight_sum = ow + sw
        ow, sw = ow / weight_sum, sw / weight_sum
        final_score = ow * o_score + sw * s_score
        weights = {'organika': round(ow, 4), 'steganographia': round(sw, 4)}

    final_score = max(0.0, min(1.0, float(final_score)))
    real_score = 1.0 - final_score

    if final_score >= STRONG_FAKE_THRESHOLD:
        label = 'AI-Generated'
        confidence = final_score
        strength = 'strong synthetic-image signal'
    elif final_score >= DETECTOR_FAKE_THRESHOLD:
        label = 'AI-Generated'
        confidence = final_score
        strength = 'more evidence for AI-generated content than authentic content'
    elif final_score <= STRONG_REAL_THRESHOLD:
        label = 'Likely Authentic'
        confidence = real_score
        strength = 'strong authentic-image signal'
    else:
        label = 'Likely Authentic'
        confidence = real_score
        strength = 'more evidence for authentic content than AI generation, but not a high-confidence real classification'

    if o_score is not None and s_score is not None:
        reason = f'{reason_prefix} Final adaptive AI probability is {final_score:.1%} ({strength}).'
    else:
        reason = f'One detector was unavailable, so TruthTrace used the available detector as a fallback. Final AI probability is {final_score:.1%} ({strength}).'

    return {
        'label': label,
        'confidence': round(confidence, 6),
        'ai_probability': round(final_score, 6),
        'fake_probability': round(final_score, 6),
        'real_probability': round(real_score, 6),
        'fusion_mode': mode,
        'detectors': [ORGANIKA_MODEL, STEGANOGRAPHIA_MODEL],
        'organika_probability': round(o_score, 6) if o_score is not None else None,
        'steganographia_probability': round(s_score, 6) if s_score is not None else None,
        'weights': weights,
        'detector_probability': round(final_score, 6),
        'reason': reason,
        'disclaimer': (
            'TruthTrace provides evidence-based classification. Detector probabilities are model outputs, '
            'not calibrated probabilities of truth. Metadata, compression signals, and detector scores cannot '
            'mathematically prove that an image is authentic or AI-generated.'
        )
    }

def analyze(path, claim='', claimed_location='', claimed_date=''):
    fp = fingerprint(path)
    mime = fp['mime_type']
    result = {'fingerprint': fp, 'signals': {}, 'models': {}, 'warnings': []}
    is_image = mime.startswith('image/')
    is_video = mime.startswith('video/')

    if is_image:
        result['signals']['dino_embedding'] = dino_embedding(path)

        # Compute transcoding heuristics for context only. They do NOT decide
        # which detector is used, because file-level compression clues cannot
        # reliably distinguish a shared real photo from a downloaded AI image.
        result['signals']['transcoding'] = transcoding_signals(path)

        # Run both AI-vs-real detectors. fuse() applies adaptive weighting.
        result['models']['deepfake'] = deepfake(path)
        result['models']['deepfake']['role'] = 'adaptive_two_detector_fusion'
        result['models']['organika'] = result['models']['deepfake']['organika']
        result['models']['steganographia'] = result['models']['deepfake']['steganographia']

        result['models']['clip'] = clip_claim_score(path, claim) if claim else {'skipped': 'no claim'}
        result['models']['geoclip'] = geoclip(path)
        result['models']['ocr'] = ocr(path)
        result['models']['c2pa'] = c2pa_verify(path)
        result['signals']['ela'] = ela_score(path)
        result['signals']['noise'] = image_noise_stats(path)
        result['signals']['manipulation'] = manipulation_signals(path)
        md = fp.get('metadata', {})
        result['signals']['temporal'] = temporal_consistency(md, claimed_date)
        result['signals']['metadata_summary'] = {
            'exif_present': bool(md.get('has_exif_block') or any(k in md for k in ('Make', 'Model', 'DateTimeOriginal'))),
            'camera_make': md.get('Make'),
            'camera_model': md.get('Model'),
            'software': md.get('Software'),
            'icc_profile': bool(md.get('has_icc_profile')),
            'jpeg_quantization_tables': md.get('jpeg_quantization_tables', []),
            'file_signature': fp.get('file_signature'),
            'likely_transcoded': bool(result['signals'].get('transcoding', {}).get('likely_transcoded')),
            'transcoding_score': result['signals'].get('transcoding', {}).get('score'),
            'ai_detector': f'{ORGANIKA_MODEL} + {STEGANOGRAPHIA_MODEL}',
            'detector_architecture': 'adaptive-two-detector',
        }
    elif is_video:
        frames = video_frames(path)
        per = []
        for f in frames:
            d = deepfake(f)
            per.append(d)
            try:
                os.remove(f)
            except Exception:
                pass
        frame_probs = [float(x.get('ai_probability', x.get('fake_probability'))) for x in per if x.get('status') == 'ok' and x.get('ai_probability', x.get('fake_probability')) is not None]
        result['models']['video_frame_deepfake'] = {
            'frames_analyzed': len(per),
            'successful_frames': len(frame_probs),
            'results': per,
            'median_fake_probability': round(float(statistics.median(frame_probs)), 6) if frame_probs else None,
            'max_fake_probability': round(max(frame_probs), 6) if frame_probs else None,
        }
        if frame_probs:
            result['models']['deepfake'] = {
                'model': STEGANOGRAPHIA_MODEL,
                'status': 'ok',
                'ai_probability': round(float(statistics.median(frame_probs)), 6),
                'fake_probability': round(float(statistics.median(frame_probs)), 6),
                'real_probability': round(1.0 - float(statistics.median(frame_probs)), 6),
                'output_type': 'video_frame_median',
            }
    else:
        result['warnings'].append('Unsupported media type for vision models')

    result['verdict'] = fuse(result)
    return result