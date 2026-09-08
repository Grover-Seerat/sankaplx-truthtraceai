"""Audio forensic analysis for TruthTrace.

The service has a dependency-light acoustic baseline and an optional Hugging Face
Audio Classification model selected with TRUTHTRACE_AUDIO_MODEL. This keeps the
feature usable on a clean hackathon install while allowing AASIST/RawNet-style
models to be plugged in without changing the API.
"""
import os, wave, subprocess, json
from pathlib import Path
import numpy as np


def _ffmpeg_wav(path: Path):
    out = path.with_suffix('.truthtrace.wav')
    try:
        subprocess.run(['ffmpeg','-y','-i',str(path),'-ac','1','-ar','16000',str(out)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=True)
        return out
    except Exception:
        return path


def _load_audio(path: Path):
    wav = _ffmpeg_wav(path)
    try:
        with wave.open(str(wav),'rb') as w:
            sr=w.getframerate(); ch=w.getnchannels(); n=w.getnframes(); raw=w.readframes(n)
            x=np.frombuffer(raw,dtype=np.int16).astype('float32')/32768.0
            if ch>1: x=x.reshape(-1,ch).mean(axis=1)
            return x,sr
    except Exception:
        return np.zeros(16000,dtype='float32'),16000


def _acoustic_baseline(x, sr):
    x=x.astype('float32');
    if len(x)==0: return {'synthetic_probability':0.5,'signal_quality':'Unavailable'}
    rms=float(np.sqrt(np.mean(x*x))+1e-9)
    zcr=float(np.mean(np.abs(np.diff(np.sign(x)))>0))
    # Frame-level spectral flatness. Synthetic speech often has unusually stable
    # spectra; this is a supporting signal only, not a trained detector.
    n=min(len(x), sr*20); x=x[:n]
    win=np.hanning(min(2048,len(x)))
    frames=[]
    hop=max(256,len(win)//2)
    for i in range(0,max(1,len(x)-len(win)+1),hop):
        f=np.abs(np.fft.rfft(x[i:i+len(win)]*win))+1e-8
        gm=float(np.exp(np.mean(np.log(f)))); am=float(np.mean(f)); frames.append(gm/am)
    sf=float(np.mean(frames)) if frames else 0.5
    # Conservative acoustic prior. Keep it near 0.5 because this is not a trained model.
    p=float(np.clip(0.50 + (0.45-sf)*0.30 + (0.025-zcr)*1.2,0.05,0.95))
    return {'synthetic_probability':round(p,4),'signal_quality':'Good' if 0.005<rms<0.35 else 'Low/atypical','rms':round(rms,5),'zero_crossing_rate':round(zcr,5),'spectral_flatness':round(sf,5)}


def _optional_model(x, sr):
    model_id=os.getenv('TRUTHTRACE_AUDIO_MODEL','Hemgg/Deepfake-audio-detection').strip()
    if not model_id: return None
    try:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        import torch
        extractor=AutoFeatureExtractor.from_pretrained(model_id)
        model=AutoModelForAudioClassification.from_pretrained(model_id)
        inputs=extractor(x,sampling_rate=sr,return_tensors='pt',padding=True)
        with torch.no_grad(): logits=model(**inputs).logits
        probs=torch.softmax(logits,dim=-1)[0].cpu().numpy()
        labels=model.config.id2label
        pairs=[{'label':labels.get(i,str(i)),'probability':round(float(p),4)} for i,p in enumerate(probs)]
        # Heuristic label mapping for common spoof/deepfake models.
        spoof=sum(v['probability'] for v in pairs if any(k in v['label'].lower() for k in ['spoof','fake','synthetic','deepfake','bonafide_false','attack']))
        return {'status':'ok','model':model_id,'synthetic_probability':round(float(np.clip(spoof,0,1)),4),'labels':pairs}
    except Exception as e:
        return {'status':'error','model':model_id,'error':str(e)[:240]}


def analyze_audio(path: str):
    p=Path(path); x,sr=_load_audio(p); baseline=_acoustic_baseline(x,sr); learned=_optional_model(x,sr)
    final=float(learned['synthetic_probability']) if learned and learned.get('status')=='ok' else float(baseline['synthetic_probability'])
    if final>=0.65: label='AI-Generated'
    elif final<=0.35: label='Likely Authentic'
    else: label='Inconclusive'
    return {
        'kind':'audio','verdict':{'label':label,'confidence':round(max(final,1-final)*100,1),'ai_probability':round(final*100,1),'reason':('A trained audio classification model produced a synthetic/spoof signal; review its labels and training domain.' if learned and learned.get('status')=='ok' else 'Audio was assessed with a conservative acoustic forensic baseline. A trained anti-spoof model can be enabled with TRUTHTRACE_AUDIO_MODEL.'),'disclaimer':'Audio detection is probabilistic. It is decision-support evidence, not proof of synthetic origin.'},
        'models':{'audio_baseline':baseline,'audio_detector':learned or {'status':'baseline-only','model':'acoustic-support'}},
        'signals':{'audio':baseline},
        'warnings':([] if learned and learned.get('status')=='ok' else ['No trained audio model configured; baseline acoustic signals are supporting evidence only.'])
    }
