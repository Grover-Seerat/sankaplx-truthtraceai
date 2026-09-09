import os, uuid, json, shutil, hashlib, secrets
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .db import init_db, q, execute, jdump, jload
from .services.forensics import fingerprint, analyze
from .services.audio_forensics import analyze_audio
from .services.investigation import grounded_chat, osint_search

BASE=Path(__file__).resolve().parents[1]; UPLOAD=Path(os.getenv('UPLOAD_DIR',BASE/'data/uploads')); REPORT=Path(os.getenv('REPORT_DIR',BASE/'data/reports')); UPLOAD.mkdir(parents=True,exist_ok=True); REPORT.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='TruthTrace Forensic API',version='1.0.0')
orig=[x.strip() for x in os.getenv('CORS_ORIGINS', 'https://sankaplx-truthtraceai-frontend.onrender.com','http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()]; app.add_middleware(CORSMiddleware,allow_origins=orig,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

class CaseIn(BaseModel):
    investigationType:str; claim:str; platform:str=''; date:str=''; location:str=''; withMedia:bool=False; notes:str=''; referenceUrl:str=''; priority:str='HIGH'

class LoginIn(BaseModel):
    username:str
    password:str

ROLE_PERMISSIONS = {
    "investigator": {
        "case:create", "case:view", "case:update", "evidence:upload", "evidence:view",
        "evidence:verify", "analysis:run", "analysis:view", "propagation:create",
        "propagation:view", "report:create", "report:view", "audit:view",
    },
    "case-officer": {
        "case:view", "case:update", "evidence:view", "evidence:verify", "analysis:view",
        "propagation:view", "report:view", "audit:view", "case:review",
    },
    "admin": {
        "case:create", "case:view", "case:update", "case:assign", "evidence:upload",
        "evidence:view", "evidence:verify", "analysis:run", "analysis:view",
        "propagation:create", "propagation:view", "report:create", "report:view",
        "audit:view", "users:manage", "system:manage", "case:review",
    },
}

ROLE_LABELS = {
    "investigator": "Investigator",
    "case-officer": "Case Officer",
    "admin": "Administrator",
}

class LoginIn(BaseModel):
    username: str
    password: str

class UserCreateIn(BaseModel):
    username: str
    name: str
    role: str
    password: str

class AssignmentIn(BaseModel):
    userId: str

def now():
    return datetime.now(timezone.utc).isoformat()

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1).hex()
    return f"scrypt${salt.hex()}${digest}"

def password_ok(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest = stored.split("$", 2)
        salt = bytes.fromhex(salt_hex)
        check = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1).hex()
        return secrets.compare_digest(check, digest)
    except Exception:
        return False

def ensure_demo_users():
    defaults = [
        (os.getenv('DEMO_INVESTIGATOR_ID','investigator@truthtrace.local'), os.getenv('DEMO_INVESTIGATOR_PASSWORD','Investigator@123'), 'Investigator', 'investigator'),
        (os.getenv('DEMO_OFFICER_ID','officer@truthtrace.local'), os.getenv('DEMO_OFFICER_PASSWORD','Officer@123'), 'Case Officer', 'case-officer'),
        (os.getenv('DEMO_ADMIN_ID','admin@truthtrace.local'), os.getenv('DEMO_ADMIN_PASSWORD','Admin@123'), 'Administrator', 'admin'),
    ]
    for username, password, name, role in defaults:
        existing = q('SELECT id FROM users WHERE username=?', (username.lower(),), one=True)
        if not existing:
            execute('INSERT INTO users(id,username,name,role,password_hash,active,created_at) VALUES(?,?,?,?,?,?,?)',
                    (f'U-{uuid.uuid4().hex[:10].upper()}', username.lower(), name, role, password_hash(password), 1, now()))

def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(401, 'Authentication required')
    raw = authorization.split(' ', 1)[1].strip()
    user = q('''SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires_at>? AND u.active=1''',
             (token_hash(raw), now()), one=True)
    if not user:
        raise HTTPException(401, 'Session expired or invalid')
    return dict(user)

def require_permission(permission: str):
    def dependency(user=Depends(current_user)):
        if permission not in ROLE_PERMISSIONS.get(user['role'], set()):
            raise HTTPException(403, 'Insufficient permission')
        return user
    return dependency

def can_access_case(cid: str, user: dict, write: bool = False):
    case_row = q('SELECT id,status FROM cases WHERE id=?', (cid,), one=True)
    if not case_row:
        raise HTTPException(404, 'Case not found')
    if write and case_row['status'] == 'Closed':
        raise HTTPException(409, 'Case is closed; write operations are disabled')
    if user['role'] == 'admin':
        return
    assigned = q('SELECT 1 FROM case_assignments WHERE case_id=? AND user_id=?', (cid, user['id']), one=True)
    if not assigned:
        raise HTTPException(403, 'You are not assigned to this case')
    if write and user['role'] == 'case-officer':
        raise HTTPException(403, 'Case officers have read-only forensic access')


@app.on_event('startup')
def startup():
    init_db()
    ensure_demo_users()

def now():return datetime.now(timezone.utc).isoformat()
def audit(cid,event,actor_user_id=None): execute('INSERT INTO audit(case_id,timestamp,event,actor_user_id) VALUES(?,?,?,?)',(cid,now(),event,actor_user_id))

def case_summary(r):
    return {'id':r['id'],'type':r['investigation_type'].replace('-',' ').title(),'priority':r['priority'],'status':r['status'],'updated':r['updated_at']}

def build_case(cid):
    c=q('SELECT * FROM cases WHERE id=?',(cid,),one=True)
    if not c:return None
    ev=q('SELECT * FROM evidence WHERE case_id=? ORDER BY created_at',(cid,)); a=q('SELECT * FROM analysis WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,),one=True); props=q('SELECT * FROM propagation WHERE case_id=? ORDER BY observed_at',(cid,)); logs=q('SELECT * FROM audit WHERE case_id=? ORDER BY id',(cid,))
    analysis=jload(a['result_json'],{}) if a else {}
    fp=analysis.get('fingerprint',{})
    auth=analysis.get('verdict',{'label':'Inconclusive','confidence':0,'reason':'Analysis pending.'})
    similar=[]
    for e in ev:
        if e['phash']:
            for x in q('SELECT * FROM evidence WHERE id!=? AND phash IS NOT NULL',(e['id'],)):
                try:
                    import imagehash; dist=imagehash.hex_to_hash(e['phash'])-imagehash.hex_to_hash(x['phash']); sim=max(0,100-(dist/64*100));
                    if sim>=50: similar.append({'case':x['case_id'],'match':round(sim,1),'platform':q('SELECT platform FROM cases WHERE id=?',(x['case_id'],),one=True)['platform'],'date':q('SELECT date FROM cases WHERE id=?',(x['case_id'],),one=True)['date'],'transform':'Visual similarity'})
                except: pass
    # DINOv2 vector similarity across stored evidence
    if ev and ev[0]['embedding_json']:
        try:
            qv=np.array(json.loads(ev[0]['embedding_json']),dtype='float32')
            for x in q('SELECT * FROM evidence WHERE id!=? AND embedding_json IS NOT NULL',(ev[0]['id'],)):
                xv=np.array(json.loads(x['embedding_json']),dtype='float32'); sim=float(np.dot(qv,xv)/(np.linalg.norm(qv)*np.linalg.norm(xv)+1e-8))*100
                if sim>=50: similar.append({'case':x['case_id'],'match':round(sim,1),'platform':q('SELECT platform FROM cases WHERE id=?',(x['case_id'],),one=True)['platform'],'date':q('SELECT date FROM cases WHERE id=?',(x['case_id'],),one=True)['date'],'transform':'DINOv2 visual embedding'})
        except: pass
    md=fp.get('metadata',{}); claim=c['claim']
    clip=analysis.get('models',{}).get('clip',{}); geo=analysis.get('models',{}).get('geoclip',{}); o=analysis.get('models',{}).get('ocr',{})
    context_rows=[{'label':'Claim','value':claim or 'Not provided','tone':'slate'}]
    if md.get('DateTimeOriginal') or md.get('DateTime'): context_rows.append({'label':'Embedded capture time','value':str(md.get('DateTimeOriginal') or md.get('DateTime')),'tone':'green'})
    else: context_rows.append({'label':'Embedded capture time','value':'No EXIF capture time present','tone':'amber'})
    if c['location']:
        context_rows.append({'label':'Claimed location','value':c['location'],'tone':'slate'})
        if geo.get('predictions'): context_rows.append({'label':'Model-estimated location','value':f"{geo['predictions'][0]['lat']:.4f}, {geo['predictions'][0]['lon']:.4f}",'tone':'amber'})
    if clip.get('claim_alignment') is not None: context_rows.append({'label':'Image/claim semantic alignment','value':f"{clip['claim_alignment']*100:.1f}%",'tone':'green' if clip['claim_alignment']>=.5 else 'amber'})
    if o.get('text'): context_rows.append({'label':'OCR text','value':' '.join(o['text'])[:500],'tone':'slate'})
    temporal=analysis.get('signals',{}).get('temporal',{})
    if temporal.get('status') == 'mismatch':
        context_rows.append({'label':'Capture/claim date consistency','value':f"Mismatch — embedded capture differs by {temporal.get('difference_days')} days",'tone':'red'})
    elif temporal.get('status') == 'consistent':
        context_rows.append({'label':'Capture/claim date consistency','value':'Consistent within the two-day comparison window','tone':'green'})
    else:
        context_rows.append({'label':'Capture/claim date consistency','value':'Not determinable from available timestamps','tone':'amber'})
    # Expose the two actual detector branches and the adaptive fusion result.
    # Keep deepfake/second_detector aliases for compatibility with the existing UI.
    organika=analysis.get('models',{}).get('organika') or analysis.get('models',{}).get('deepfake',{})
    steganographia=analysis.get('models',{}).get('steganographia') or analysis.get('models',{}).get('second_detector',{})
    fusion=analysis.get('models',{}).get('adaptive_fusion',{})
    if organika.get('fake_probability') is not None:
        context_rows.append({'label':'Organika AI-generation detector','value':f"{float(organika['fake_probability'])*100:.1f}% AI-generated probability",'tone':'red' if float(organika['fake_probability'])>=.6 else 'green'})
    if steganographia.get('status') == 'ok' and steganographia.get('fake_probability') is not None:
        context_rows.append({'label':'SteganographIA AI-generation detector','value':f"{float(steganographia['fake_probability'])*100:.1f}% AI-generated probability",'tone':'red' if float(steganographia['fake_probability'])>=.6 else 'green'})
    if fusion.get('ai_probability') is not None:
        context_rows.append({'label':'Adaptive detector fusion','value':f"{float(fusion['ai_probability']):.1f}% final AI probability",'tone':'red' if float(fusion['ai_probability'])>=55 else 'green' if float(fusion['ai_probability'])<=45 else 'amber'})
    manipulation=analysis.get('signals',{}).get('manipulation',{})
    if manipulation.get('index') is not None:
        context_rows.append({'label':'Manipulation signal index','value':f"{float(manipulation['index'])*100:.1f}% (supporting signal)",'tone':'amber' if float(manipulation['index'])>=.35 else 'slate'})
    evidence=[]
    for e in ev: evidence.append({'id':e['id'],'caseId':cid,'type':'Audio' if 'audio' in e['mime_type'] else 'Video' if 'video' in e['mime_type'] else 'Image','dna':e['dna_id'],'hash':'Verified','analysis':'Complete' if a else 'In Progress','added':e['created_at']})
    media_meta = jload(ev[0]['metadata_json'], {}) if ev else {}
    capture_time = media_meta.get('DateTimeOriginal') or media_meta.get('DateTime') or media_meta.get('creation_time')
    media = ({'fileName':ev[0]['file_name'],'fileType':ev[0]['file_type'],'fileSize':f"{ev[0]['file_size']/1048576:.2f} MB",'mimeType':ev[0]['mime_type'],'sha256':ev[0]['sha256'],'width':ev[0]['width'],'height':ev[0]['height'],'duration':ev[0]['duration'],'source':c['platform'] or 'Investigator upload','addedAt':ev[0]['created_at'],'captureTime':str(capture_time) if capture_time else None,'metadata':media_meta} if ev else None)
    return {'id':cid,'investigationType':c['investigation_type'],'intent':{'claim':c['claim'],'platform':c['platform'],'date':c['date'],'location':c['location'],'withMedia':bool(c['with_media'])},'media':media,'dnaId':ev[0]['dna_id'] if ev else None,'fingerprint':{'SHA-256':ev[0]['sha256'],'Perceptual Hash':ev[0]['phash'],'File Name':ev[0]['file_name'],'File Size':str(ev[0]['file_size']),'Format':ev[0]['file_type'],'Dimensions':f"{ev[0]['width']} × {ev[0]['height']}"} if ev else {},'overview':{'authenticity':{'value':auth['label'],'sub':f"{auth['confidence']}% confidence",'tone':'green' if auth['label']=='Likely Authentic' else 'red' if auth['label'] in ['Manipulated','AI-Generated'] else 'amber'},'mediaDna':{'value':f"{max([m['match'] for m in similar],default=0):.1f}%" if similar else 'No match','sub':'Stored evidence similarity','tone':'blue'},'context':{'value':'Review' if context_rows else 'Pending','tone':'amber'},'propagation':{'value':'Traced' if props else 'No events','tone':'blue'},'assessment':auth['reason'],'why':['All displayed forensic values are computed from uploaded evidence or stored investigation observations.'],'nextActions':['Review model evidence and provenance.','Confirm contextual claims with independent sources.']},'authenticity':{'verdict':auth['label'],'confidence':auth['confidence'],'summary':auth['reason'],'aiProbability':auth.get('ai_probability'),'fakeProbability':auth.get('fake_probability',auth.get('ai_probability')),'realProbability':auth.get('real_probability'),'fusionMode':auth.get('fusion_mode'),'detectorAgreement':auth.get('detector_agreement'),'detectorClassAgreement':auth.get('detector_class_agreement'),'detectorProbabilitySpread':auth.get('detector_probability_spread'),'organika':analysis.get('models',{}).get('organika') or analysis.get('models',{}).get('deepfake',{}),'steganographia':analysis.get('models',{}).get('steganographia') or analysis.get('models',{}).get('second_detector',{}),'adaptiveFusion':analysis.get('models',{}).get('adaptive_fusion',{}),'organikaWeight':auth.get('organika_weight'),'steganographiaWeight':auth.get('steganographia_weight'),'adaptiveDisagreement':auth.get('adaptive_disagreement'),'transcodingConsidered':auth.get('transcoding_considered'),'disclaimer':auth.get('disclaimer')},'forensics':{'signals':analysis.get('signals',{}),'models':analysis.get('models',{}),'warnings':analysis.get('warnings',[]),'verdict':auth},'similarMedia':similar[:20],'mediaFamily':[],'context':{'mediaAuthenticity':'HIGH' if auth['label']=='Likely Authentic' else 'LOW' if auth['label'] in ['Manipulated','AI-Generated'] else 'MEDIUM','contextConsistency':'MEDIUM','assessment':'Context assessment is evidence-led; absence of metadata is not proof of manipulation.','claim':claim,'evidenceRows':context_rows},'propagationNodes':[dict(x) for x in props],'propagationLeads':['No propagation observations stored yet.'] if not props else [],'audit':[{'t':x['timestamp'],'e':x['event'],'actor':x['actor_user_id']} for x in logs],'evidence':evidence,'notes':c['notes'],'referenceUrl':c['reference_url']}

@app.post('/api/auth/login')
def login(body: LoginIn):
    user = q('SELECT * FROM users WHERE username=? AND active=1', (body.username.strip().lower(),), one=True)
    if not user or not password_ok(body.password, user['password_hash']):
        raise HTTPException(401, 'Invalid username or password')
    raw_token = secrets.token_urlsafe(48)
    expires = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
    execute('INSERT INTO sessions(id,user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?)',
            (uuid.uuid4().hex, user['id'], token_hash(raw_token), expires, now()))
    return {'ok': True, 'session': raw_token, 'userId': user['id'], 'role': user['role'],
            'name': user['name'], 'username': user['username'], 'expiresAt': expires,
            'permissions': sorted(ROLE_PERMISSIONS[user['role']])}

@app.get('/api/auth/me')
def me(user=Depends(current_user)):
    return {'ok': True, 'userId': user['id'], 'role': user['role'], 'name': user['name'],
            'username': user['username'], 'permissions': sorted(ROLE_PERMISSIONS[user['role']])}

@app.post('/api/auth/logout')
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith('bearer '):
        execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(authorization.split(' ', 1)[1].strip()),))
    return {'ok': True}

@app.get('/api/health')
def health():return {'ok':True,'service':'TruthTrace Forensic API'}
@app.get('/api/cases')
def cases(user=Depends(require_permission('case:view'))):
    if user['role'] == 'admin': rows=q('SELECT * FROM cases ORDER BY updated_at DESC')
    else: rows=q('SELECT c.* FROM cases c JOIN case_assignments a ON a.case_id=c.id WHERE a.user_id=? ORDER BY c.updated_at DESC',(user['id'],))
    return [case_summary(x) for x in rows]
@app.post('/api/cases')
def create_case(body:CaseIn, user=Depends(require_permission('case:create'))):
    if body.investigationType in {'verify-media','media-dna'} and not body.withMedia:
        raise HTTPException(400,'Media evidence is required for this investigation type')
    n=q("SELECT COUNT(*) n FROM cases WHERE id LIKE ?",(f"CASE-{datetime.now().year}-%",),one=True)['n']+1; cid=f"CASE-{datetime.now().year}-{n:04d}"; t=now(); execute('INSERT INTO cases VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(cid,body.investigationType,body.claim,body.platform,body.date,body.location,int(body.withMedia),body.notes,body.referenceUrl,body.priority,'Active',t,t)); execute('INSERT INTO case_assignments(case_id,user_id,assigned_at,assigned_by) VALUES(?,?,?,?)',(cid,user['id'],t,user['id'])); audit(cid,'Investigation case created from investigator input',user['id']); return build_case(cid)
@app.post('/api/cases/{cid}/close')
def close_case(cid: str, user=Depends(require_permission('case:update'))):
    can_access_case(cid, user, write=False)
    if user['role'] not in {'admin','case-officer'}:
        raise HTTPException(403,'Only Case Officers and Administrators can close cases')
    row=q('SELECT status FROM cases WHERE id=?',(cid,),one=True)
    if not row:
        raise HTTPException(404,'Case not found')
    if row['status']=='Closed':
        return {'ok':True,'status':'Closed','alreadyClosed':True}
    t=now()
    execute("UPDATE cases SET status='Closed', updated_at=? WHERE id=?",(t,cid))
    audit(cid,'Case closed by '+ROLE_LABELS.get(user['role'],user['role']),user['id'])
    return {'ok':True,'status':'Closed','alreadyClosed':False,'closedAt':t}

@app.get('/api/cases/{cid}')
def get_case(cid:str, user=Depends(require_permission('case:view'))):
    can_access_case(cid,user)
    x=build_case(cid)
    if not x: raise HTTPException(404,'Case not found')
    if user['role'] != 'admin':
        allowed={r['case_id'] for r in q('SELECT case_id FROM case_assignments WHERE user_id=?',(user['id'],))}
        x['similarMedia']=[m for m in x.get('similarMedia',[]) if m.get('case') in allowed]
    return x
@app.post('/api/cases/{cid}/evidence')
async def upload(cid:str,file:UploadFile=File(...), user=Depends(require_permission('evidence:upload'))):
    can_access_case(cid,user,write=True)
    if not q('SELECT id FROM cases WHERE id=?',(cid,),one=True):raise HTTPException(404,'Case not found')
    eid='EV-'+uuid.uuid4().hex[:10].upper(); ext=Path(file.filename or 'upload.bin').suffix.lower(); dest=UPLOAD/f'{eid}{ext}'
    with open(dest,'wb') as f: shutil.copyfileobj(file.file,f)
    fp=fingerprint(dest); embedding=None
    if fp['mime_type'].startswith('image/'):
        from .services.forensics import dino_embedding
        emb=dino_embedding(dest); embedding=emb if isinstance(emb,list) else None
    execute('INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(eid,cid,file.filename or eid,str(dest),file.content_type or fp['mime_type'],fp['mime_type'].split('/')[-1].upper(),fp['size'],fp['sha256'],fp.get('phash'),fp['dna_id'],json.dumps(embedding) if embedding else None,fp.get('width'),fp.get('height'),fp.get('duration'),jdump(fp.get('metadata',{})),'In Progress',now())); audit(cid,f'Evidence received: {file.filename}',user['id']); audit(cid,'SHA-256 and forensic file fingerprint generated',user['id']); return {'evidenceId':eid,'fileName':file.filename,'sha256':fp['sha256'],'dnaId':fp['dna_id'],'fingerprint':fp}
@app.post('/api/cases/{cid}/analyze')
def run_analysis(cid:str, user=Depends(require_permission('analysis:run'))):
    can_access_case(cid,user,write=True)
    e=q('SELECT * FROM evidence WHERE case_id=? ORDER BY created_at DESC LIMIT 1',(cid,),one=True)
    if not e:raise HTTPException(400,'Upload evidence first')
    c=q('SELECT * FROM cases WHERE id=?',(cid,),one=True); audit(cid,'Forensic analysis started',user['id']);
    audio_exts={'.wav','.mp3','.m4a','.aac','.flac','.ogg','.oga','.opus','.wma','.aiff','.aif','.webm','.mpeg','.mpg','.mp2'}
    is_audio=(e['mime_type'] or '').startswith('audio/') or Path(e['file_name'] or '').suffix.lower() in audio_exts
    if is_audio:
        r=analyze_audio(e['file_path'])
        # Preserve the same top-level contract consumed by the workspace UI.
        r['fingerprint']={'sha256':e['sha256'],'phash':None,'metadata':jload(e['metadata_json'],{})}
    else:
        r=analyze(e['file_path'], c['claim'], c['location'], c['date'])
    execute('INSERT INTO analysis(case_id,evidence_id,result_json,created_at) VALUES(?,?,?,?)',(cid,e['id'],jdump(r),now())); execute('UPDATE evidence SET analysis_status=? WHERE id=?',('Complete',e['id'])); audit(cid,'Forensic analysis completed',user['id']); return r
@app.get('/api/cases/{cid}/analysis')
def get_analysis(cid:str, user=Depends(require_permission('analysis:view'))):
    can_access_case(cid,user)
    a=q('SELECT * FROM analysis WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,),one=True); return jload(a['result_json'],{}) if a else {'status':'pending'}
@app.get('/api/cases/{cid}/evidence/{eid}/file')
def evidence_file(cid:str,eid:str,user=Depends(require_permission('evidence:view'))):
    can_access_case(cid,user)
    e=q('SELECT file_path,mime_type,file_name FROM evidence WHERE id=? AND case_id=?',(eid,cid),one=True)
    if not e: raise HTTPException(404,'Evidence not found')
    path=Path(e['file_path'])
    if not path.exists(): raise HTTPException(404,'Evidence file not found')
    return FileResponse(path,media_type=e['mime_type'] or 'application/octet-stream',filename=e['file_name'])

@app.get('/api/cases/{cid}/evidence')
def evidence(cid:str, user=Depends(require_permission('evidence:view'))):
    can_access_case(cid,user)
    return build_case(cid)['evidence'] if build_case(cid) else []
@app.get('/api/evidence')
def all_evidence(user=Depends(require_permission('evidence:view'))):
    if user['role']=='admin': rows=q('SELECT id,case_id,file_name,mime_type,file_size,sha256,phash,dna_id,analysis_status,created_at FROM evidence ORDER BY created_at DESC')
    else: rows=q('''SELECT e.id,e.case_id,e.file_name,e.mime_type,e.file_size,e.sha256,e.phash,e.dna_id,e.analysis_status,e.created_at FROM evidence e JOIN case_assignments a ON a.case_id=e.case_id WHERE a.user_id=? ORDER BY e.created_at DESC''',(user['id'],))
    return [dict(x) for x in rows]
@app.get('/api/cases/{cid}/propagation')
def propagation(cid:str, user=Depends(require_permission('propagation:view'))):
    can_access_case(cid,user)
    return [dict(x) for x in q('SELECT * FROM propagation WHERE case_id=? ORDER BY observed_at',(cid,))]

@app.post('/api/cases/{cid}/propagation/trace')
def trace_propagation(cid:str,user=Depends(require_permission('propagation:create'))):
    """Build propagation leads only from evidence already stored in TruthTrace."""
    can_access_case(cid,user,write=True)
    current=q('SELECT * FROM evidence WHERE case_id=? ORDER BY created_at DESC LIMIT 1',(cid,),one=True)
    if not current:
        raise HTTPException(400,'Upload and analyze evidence first')
    created=0
    try:
        import imagehash
        current_phash=imagehash.hex_to_hash(current['phash']) if current['phash'] else None
    except Exception:
        current_phash=None
    current_vec=None
    try:
        current_vec=np.array(json.loads(current['embedding_json']),dtype='float32') if current['embedding_json'] else None
    except Exception:
        current_vec=None
    candidates=q('SELECT e.*,c.platform,c.reference_url FROM evidence e JOIN cases c ON c.id=e.case_id WHERE e.id!=?',(current['id'],))
    for x in candidates:
        scores=[]
        if current_phash is not None and x['phash']:
            try:
                dist=current_phash-imagehash.hex_to_hash(x['phash'])
                scores.append(('pHash',max(0.0,100.0-(dist/64.0*100.0))))
            except Exception:
                pass
        if current_vec is not None and x['embedding_json']:
            try:
                xv=np.array(json.loads(x['embedding_json']),dtype='float32')
                sim=float(np.dot(current_vec,xv)/(np.linalg.norm(current_vec)*np.linalg.norm(xv)+1e-8))*100.0
                scores.append(('DINOv2',sim))
            except Exception:
                pass
        if not scores:
            continue
        method, similarity=max(scores,key=lambda z:z[1])
        if similarity < 70:
            continue
        existing=q('SELECT id FROM propagation WHERE case_id=? AND source_url=? AND to_node=?',(cid,x['reference_url'] or '',x['case_id']),one=True)
        if existing:
            continue
        execute('INSERT INTO propagation(case_id,evidence_id,platform,account,observed_at,similarity,transformation,source_url,from_node,to_node,spread,tag) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (cid,current['id'],x['platform'] or 'Stored evidence', '', now(), round(similarity,1), method+' visual similarity', x['reference_url'] or '', cid, x['case_id'], 'stored-evidence match', 'AUTO-SIMILARITY'))
        created+=1
    audit(cid,f'Propagation trace completed: {created} stored-evidence lead(s)',user['id'])
    return {'created':created,'events':[dict(x) for x in q('SELECT * FROM propagation WHERE case_id=? ORDER BY observed_at',(cid,))]}
class PropIn(BaseModel): platform:str; account:str=''; observedAt:str=''; similarity:float=100; transformation:str='Original'; sourceUrl:str=''; fromNode:str=''; toNode:str=''; spread:str=''; tag:str='OBSERVED'
@app.post('/api/cases/{cid}/propagation')
def add_prop(cid:str,b:PropIn,user=Depends(require_permission('propagation:create'))):
    can_access_case(cid,user,write=True)
    execute('INSERT INTO propagation(case_id,platform,account,observed_at,similarity,transformation,source_url,from_node,to_node,spread,tag) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(cid,b.platform,b.account,b.observedAt or now(),b.similarity,b.transformation,b.sourceUrl,b.fromNode,b.toNode,b.spread,b.tag)); audit(cid,f'Propagation observation recorded on {b.platform}',user['id']); return {'ok':True}
@app.get('/api/cases/{cid}/audit')
def audit_get(cid:str, user=Depends(require_permission('audit:view'))):
    can_access_case(cid,user)
    return [{'t':x['timestamp'],'e':x['event'],'actor':x['actor_user_id'] or 'System'} for x in q('SELECT * FROM audit WHERE case_id=? ORDER BY id',(cid,))]

@app.get('/api/cases/{cid}/copilot/history')
def copilot_history(cid:str, user=Depends(require_permission('analysis:view'))):
    can_access_case(cid,user)
    return [dict(x) for x in q('SELECT id,role,message,created_at FROM chat_messages WHERE case_id=? ORDER BY id DESC LIMIT 40',(cid,))][::-1]

class ChatIn(BaseModel):
    message:str

@app.post('/api/cases/{cid}/copilot')
def copilot(cid:str, body:ChatIn, user=Depends(require_permission('analysis:view'))):
    can_access_case(cid,user)
    c=build_case(cid)
    a=q('SELECT * FROM analysis WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,),one=True)
    analysis=jload(a['result_json'],{}) if a else {}
    props=[dict(x) for x in q('SELECT * FROM propagation WHERE case_id=? ORDER BY observed_at',(cid,))]
    evidence=[dict(x) for x in q('SELECT * FROM evidence WHERE case_id=? ORDER BY created_at',(cid,))]
    audit_rows=[dict(x) for x in q('SELECT * FROM audit WHERE case_id=? ORDER BY id',(cid,))]
    # Only retrieve OSINT saved under this exact case_id. No cross-case retrieval.
    latest=q('SELECT result_json FROM osint_results WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,),one=True)
    osint=jload(latest['result_json'],{}) if latest else None
    execute('INSERT INTO chat_messages(case_id,user_id,role,message,created_at) VALUES(?,?,?,?,?)',(cid,user['id'],'user',body.message.strip(),now()))
    answer=grounded_chat(c,analysis,props,body.message,osint,evidence,audit_rows)
    execute('INSERT INTO chat_messages(case_id,user_id,role,message,created_at) VALUES(?,?,?,?,?)',(cid,None,'assistant',answer,now()))
    audit(cid,'Investigator Copilot query answered from case evidence',user['id'])
    return {'answer':answer}

class OsintIn(BaseModel):
    query:str=''

@app.post('/api/cases/{cid}/osint/search')
def osint(cid:str, body:OsintIn, user=Depends(require_permission('analysis:view'))):
    can_access_case(cid,user)
    c=q('SELECT * FROM cases WHERE id=?',(cid,),one=True)
    a=q('SELECT * FROM analysis WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,),one=True)
    analysis=jload(a['result_json'],{}) if a else {}
    o=analysis.get('models',{}).get('ocr',{}) if analysis else {}
    e=q('SELECT id,mime_type,file_name FROM evidence WHERE case_id=? ORDER BY created_at DESC LIMIT 1',(cid,),one=True)
    query=body.query.strip() or c['claim'] or 'TruthTrace investigation'
    ocr=' '.join(o.get('text',[])) if isinstance(o,dict) else ''
    result=osint_search(query, ocr, c['reference_url'] or '')
    if e and (e['mime_type'] or '').startswith('image/'):
        result['imageEvidence']={'evidenceId':e['id'],'fileName':e['file_name'],'reverseSearch':'Google Lens upload available from the browser','duckduckgoImageSearch':True}
    execute('INSERT INTO osint_results(case_id,query,result_json,created_at) VALUES(?,?,?,?)',(cid,query,jdump(result),now()))
    audit(cid,f'Public-web OSINT search executed: {query[:100]}',user['id'])
    return result

@app.get('/api/cases/{cid}/osint')
def get_osint(cid:str, user=Depends(require_permission('analysis:view'))):
    can_access_case(cid,user)
    rows=q('SELECT id,query,result_json,created_at FROM osint_results WHERE case_id=? ORDER BY id DESC LIMIT 10',(cid,))
    return [{'id':x['id'],'query':x['query'],'createdAt':x['created_at'],'result':jload(x['result_json'],{})} for x in rows]


@app.post('/api/cases/{cid}/gemini-media')
def gemini_media(cid:str,user=Depends(require_permission('analysis:view'))):
    can_access_case(cid,user)
    c=q('SELECT * FROM cases WHERE id=?',(cid,),one=True)
    e=q('SELECT * FROM evidence WHERE case_id=? ORDER BY created_at DESC LIMIT 1',(cid,),one=True)
    if not e:
        raise HTTPException(400,'Upload evidence first')
    try:
        from .services.gemini_service import analyze_media
        result=analyze_media(e['file_path'],c['claim'] or '',c['location'] or '',c['date'] or '')
        audit(cid,'Gemini multimodal evidence interpretation executed',user['id'])
        return {'evidenceId':e['id'],'fileName':e['file_name'],'model':os.getenv('GEMINI_MODEL','gemini-3.8-flash'),'result':result}
    except RuntimeError as exc:
        raise HTTPException(503,str(exc))
    except Exception as exc:
        raise HTTPException(502,f'Gemini investigation failed: {str(exc)[:180]}')

class ReviewIn(BaseModel):
    disposition:str
    rationale:str
    evidenceSufficiency:str='Sufficient'
    investigatorFinding:str=''

@app.get('/api/cases/{cid}/review')
def get_case_review(cid:str,user=Depends(require_permission('case:view'))):
    can_access_case(cid,user)
    rows=q("""SELECT r.id,r.disposition,r.rationale,r.evidence_sufficiency,r.investigator_finding,r.created_at,r.reviewer_user_id,u.name as reviewer_name
              FROM case_reviews r LEFT JOIN users u ON u.id=r.reviewer_user_id
              WHERE r.case_id=? ORDER BY r.id DESC""",(cid,))
    return [dict(x) for x in rows]

@app.post('/api/cases/{cid}/review')
def add_case_review(cid:str,body:ReviewIn,user=Depends(require_permission('case:review'))):
    can_access_case(cid,user)
    disposition=body.disposition.strip().upper()
    allowed={'CONFIRM','CHALLENGE','REQUEST_MORE_EVIDENCE'}
    if disposition not in allowed:
        raise HTTPException(400,'Invalid review disposition')
    rationale=body.rationale.strip()
    if len(rationale)<10:
        raise HTTPException(400,'Review rationale must be at least 10 characters')
    created=now()
    execute("""INSERT INTO case_reviews(case_id,reviewer_user_id,disposition,rationale,evidence_sufficiency,investigator_finding,created_at)
               VALUES(?,?,?,?,?,?,?)""",(cid,user['id'],disposition,rationale,body.evidenceSufficiency.strip(),body.investigatorFinding.strip(),created))
    execute("UPDATE cases SET status='Under Review',updated_at=? WHERE id=? AND status!='Closed'",(created,cid))
    audit(cid,f"Case Officer review: {disposition}",user['id'])
    return {'ok':True,'createdAt':created,'disposition':disposition}

@app.get('/api/cases/{cid}/timeline')
def case_timeline(cid:str,user=Depends(require_permission('case:view'))):
    can_access_case(cid,user)
    events=[]
    c=q('SELECT id,created_at FROM cases WHERE id=?',(cid,),one=True)
    if c and c['created_at']:
        events.append({'timestamp':c['created_at'],'type':'CASE','title':'Case created','detail':'Investigation case created'})
    for x in q('SELECT created_at,file_name,mime_type FROM evidence WHERE case_id=? ORDER BY created_at',(cid,)):
        events.append({'timestamp':x['created_at'],'type':'EVIDENCE','title':'Evidence received','detail':f"{x['file_name']} ({x['mime_type'] or 'unknown media'})"})
    for x in q('SELECT created_at,result_json FROM analysis WHERE case_id=? ORDER BY created_at',(cid,)):
        r=jload(x['result_json'],{}) or {}; v=r.get('verdict',{}) or {}
        events.append({'timestamp':x['created_at'],'type':'ANALYSIS','title':'Forensic analysis completed','detail':f"{v.get('label','Inconclusive')} — {v.get('confidence',0)}% confidence"})
    for x in q('SELECT timestamp,event,actor_user_id FROM audit WHERE case_id=? ORDER BY id',(cid,)):
        events.append({'timestamp':x['timestamp'],'type':'AUDIT','title':'Audit event','detail':x['event'],'actor':x['actor_user_id'] or 'System'})
    for x in q('SELECT created_at,disposition,rationale FROM case_reviews WHERE case_id=? ORDER BY created_at',(cid,)):
        events.append({'timestamp':x['created_at'],'type':'REVIEW','title':f"Case review — {x['disposition'].replace('_',' ')}",'detail':x['rationale']})
    for x in q('SELECT created_at,query FROM osint_results WHERE case_id=? ORDER BY created_at',(cid,)):
        events.append({'timestamp':x['created_at'],'type':'OSINT','title':'Public-web OSINT executed','detail':x['query']})
    events.sort(key=lambda e:e.get('timestamp') or '')
    return events

@app.post('/api/cases/{cid}/ai-osint')
def ai_osint(cid:str,user=Depends(require_permission('analysis:view'))):
    can_access_case(cid,user)
    c=q('SELECT * FROM cases WHERE id=?',(cid,),one=True)
    a=q('SELECT * FROM analysis WHERE case_id=? ORDER BY id DESC LIMIT 1',(cid,),one=True)
    analysis=jload(a['result_json'],{}) if a else {}
    o=analysis.get('models',{}).get('ocr',{}) if analysis else {}
    context={'case':{'id':c['id'],'claim':c['claim'],'platform':c['platform'],'location':c['location'],'date':c['date'],'reference_url':c['reference_url']},'ocr':' '.join(o.get('text',[]))[:600] if isinstance(o,dict) else ''}
    try:
        from .services.gemini_service import generate_search_queries
        queries=generate_search_queries(context)
        ai_used=True
    except Exception:
        queries=[]
        ai_used=False
    if not queries:
        queries=[x for x in [c['claim'], context['ocr']] if x][:3]
    results=[]
    errors=[]
    for query in queries[:5]:
        try:
            r=osint_search(query,'','')
            results.extend(r.get('results',[]))
            if r.get('error'): errors.append(r['error'])
        except Exception as exc:
            errors.append(str(exc)[:160])
    seen=set(); dedup=[]
    for r in results:
        if r.get('url') and r['url'] not in seen:
            seen.add(r['url']); dedup.append(r)
    payload={'status':'ok' if dedup else 'error','provider':'Gemini + DuckDuckGo','queries':queries[:5],'results':dedup[:30],'searched_at':now(),'ai_query_generation':ai_used,'error':errors[0] if errors and not dedup else None}
    execute('INSERT INTO osint_results(case_id,query,result_json,created_at) VALUES(?,?,?,?)',(cid,'Gemini-guided web investigation',jdump(payload),now()))
    audit(cid,'Gemini-guided public-web investigation executed',user['id'])
    return payload

@app.get('/api/users')
def users(user=Depends(require_permission('users:manage'))):
    return [{'id':x['id'],'username':x['username'],'name':x['name'],'role':x['role'],'active':bool(x['active']),'createdAt':x['created_at']} for x in q('SELECT * FROM users ORDER BY name')]

@app.post('/api/users')
def create_user(body:UserCreateIn,user=Depends(require_permission('users:manage'))):
    role=body.role.strip().lower()
    if role not in ROLE_PERMISSIONS: raise HTTPException(400,'Invalid role')
    username=body.username.strip().lower()
    if q('SELECT id FROM users WHERE username=?',(username,),one=True): raise HTTPException(409,'Username already exists')
    uid=f'U-{uuid.uuid4().hex[:10].upper()}'
    execute('INSERT INTO users(id,username,name,role,password_hash,active,created_at) VALUES(?,?,?,?,?,?,?)',(uid,username,body.name.strip(),role,password_hash(body.password),1,now()))
    return {'id':uid,'username':username,'name':body.name.strip(),'role':role,'active':True}

@app.post('/api/cases/{cid}/assign')
def assign_case(cid:str,body:AssignmentIn,user=Depends(require_permission('case:assign'))):
    can_access_case(cid,user)
    target=q('SELECT id,role,active FROM users WHERE id=?',(body.userId,),one=True)
    if not target or not target['active']: raise HTTPException(404,'User not found')
    execute('INSERT OR REPLACE INTO case_assignments(case_id,user_id,assigned_at,assigned_by) VALUES(?,?,?,?)',(cid,body.userId,now(),user['id']))
    audit(cid,f"Case assigned to user {body.userId}",user['id'])
    return {'ok':True}

@app.get('/api/dashboard')
def dashboard(user=Depends(current_user)):
    if user['role']=='admin': cases=q('SELECT status,priority,created_at FROM cases ORDER BY created_at')
    else: cases=q('SELECT c.status,c.priority,c.created_at FROM cases c JOIN case_assignments a ON a.case_id=c.id WHERE a.user_id=? ORDER BY c.created_at',(user['id'],))
    if user['role']=='admin':
        ev=q('SELECT * FROM evidence')
        analyses=q('SELECT case_id,result_json,created_at FROM analysis ORDER BY created_at')
    else:
        ev=q('SELECT e.* FROM evidence e JOIN case_assignments a ON a.case_id=e.case_id WHERE a.user_id=?',(user['id'],))
        analyses=q('SELECT an.case_id,an.result_json,an.created_at FROM analysis an JOIN case_assignments a ON a.case_id=an.case_id WHERE a.user_id=? ORDER BY an.created_at',(user['id'],))
    verdict_counts={'Likely Authentic':0,'Manipulated':0,'AI-Generated':0,'Inconclusive':0}
    confidence=[]
    for a in analyses:
        r=jload(a['result_json'],{}) or {}; v=r.get('verdict',{}) or {}; label=v.get('label')
        if label in verdict_counts: verdict_counts[label]+=1
        try: confidence.append(float(v.get('confidence',0)))
        except: pass
    monthly={}
    for a in analyses:
        key=str(a['created_at'])[:10]
        monthly[key]=monthly.get(key,0)+1
    return {
        'activeCases':sum(x['status']!='Closed' for x in cases),
        'completedCases':sum(x['status']=='Closed' for x in cases),
        'underReview':sum(x['status']=='Under Review' for x in cases),
        'criticalCases':sum(x['priority']=='CRITICAL' for x in cases),
        'evidenceProcessed':len(ev),
        'reportsGenerated':q('SELECT COUNT(*) n FROM reports',one=True)['n'],
        'analysisCount':len(analyses),
        'verdictCounts':verdict_counts,
        'averageConfidence':round(sum(confidence)/len(confidence),1) if confidence else 0,
        'activity': [{'date':k,'count':monthly[k]} for k in sorted(monthly)],
        'source':'analysis + forensic reports tables'
    }
@app.get('/api/cases/{cid}/report')
def report(cid:str, user=Depends(require_permission('report:view'))):
    can_access_case(cid,user)
    data=build_case(cid)
    if not data: raise HTTPException(404,'Case not found')
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.units import mm

    path=REPORT/f'{cid}-forensic-report.pdf'
    styles=getSampleStyleSheet()
    title=ParagraphStyle('TTTitle',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=19,leading=23,textColor=colors.HexColor('#10233F'),spaceAfter=8)
    subtitle=ParagraphStyle('TTSub',parent=styles['BodyText'],fontSize=8.5,leading=12,textColor=colors.HexColor('#64748B'),spaceAfter=10)
    h1=ParagraphStyle('TTH1',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=12.5,leading=16,textColor=colors.HexColor('#173A63'),spaceBefore=12,spaceAfter=7)
    h2=ParagraphStyle('TTH2',parent=styles['Heading3'],fontName='Helvetica-Bold',fontSize=9.5,leading=12,textColor=colors.HexColor('#334155'),spaceBefore=7,spaceAfter=5)
    body=ParagraphStyle('TTBody',parent=styles['BodyText'],fontSize=8.7,leading=12,textColor=colors.HexColor('#334155'),spaceAfter=4)
    small=ParagraphStyle('TTSmall',parent=body,fontSize=7.7,leading=10.5,textColor=colors.HexColor('#64748B'))
    cell=ParagraphStyle('TTCell',parent=body,fontSize=7.8,leading=10)
    cell_bold=ParagraphStyle('TTCellBold',parent=cell,fontName='Helvetica-Bold',textColor=colors.HexColor('#173A63'))
    status=ParagraphStyle('TTStatus',parent=cell,fontName='Helvetica-Bold',textColor=colors.HexColor('#087F7B'))

    def esc(v):
        return str(v if v is not None and str(v).strip() else 'N/A').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    def P(v, style=cell): return Paragraph(esc(v).replace('\n','<br/>'), style)
    def timestamp(v):
        if not v: return 'N/A'
        try:
            dt=datetime.fromisoformat(str(v).replace('Z','+00:00'))
            return dt.astimezone(timezone.utc).strftime('%d %b %Y, %H:%M:%S UTC')
        except Exception: return str(v)
    def table(rows, widths, header=True):
        t=Table(rows,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
        cmds=[('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#D7E0EA')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]
        if header:
            cmds += [('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EAF0F7')),('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#173A63')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')]
        t.setStyle(TableStyle(cmds)); return t
    def section(title_text): return [Paragraph(title_text,h1)]

    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=17*mm,bottomMargin=16*mm,title=f'TruthTrace Forensic Report — {cid}',author='TruthTrace')
    story=[Paragraph('TRUTHTRACE AI — FORENSIC CASE REPORT',title),Paragraph(f'Case <b>{esc(cid)}</b>  •  Generated {timestamp(now())}',subtitle)]
    story += [Paragraph('INVESTIGATION SUMMARY',h1),table([[P('Field',cell_bold),P('Value',cell_bold)],
        [P('Investigation type'),P(data['investigationType'])],[P('Claim'),P(data['intent']['claim'])],[P('Platform'),P(data['intent']['platform'])],[P('Claim date'),P(data['intent']['date'])],[P('Known location'),P(data['intent']['location'])],[P('Media submitted'),P('Yes' if data['intent']['withMedia'] else 'No')]], [50*mm,130*mm])]

    story += [Paragraph('AUTHENTICITY ASSESSMENT',h1),table([[P('Verdict',cell_bold),P('Confidence',cell_bold),P('Finding',cell_bold)],[P(data['authenticity']['verdict'],status),P(f"{data['authenticity']['confidence']}%"),P(data['authenticity']['summary'])]],[42*mm,32*mm,106*mm])]

    story += [Paragraph('MEDIA EVIDENCE & CAPTURE METADATA',h1)]
    if data.get('media'):
        m=data['media']; rows=[[P('Field',cell_bold),P('Value',cell_bold)],[P('File name'),P(m['fileName'])],[P('File type / MIME'),P(f"{m['fileType']} / {m.get('mimeType','N/A')}")],[P('File size'),P(m['fileSize'])],[P('SHA-256'),P(m['sha256'])],[P('Dimensions'),P(f"{m.get('width') or 'N/A'} × {m.get('height') or 'N/A'}")],[P('Duration'),P(m.get('duration'))],[P('Capture time (EXIF / embedded)'),P(m.get('captureTime') or 'No embedded capture time present')],[P('Evidence added'),P(timestamp(m['addedAt']))],[P('Source'),P(m.get('source'))]]
        story.append(table(rows,[62*mm,118*mm]))
        meta=m.get('metadata') or {}
        useful=[('Camera make',meta.get('Make')),('Camera model',meta.get('Model')),('Software',meta.get('Software')),('GPS latitude',meta.get('GPSLatitude')),('GPS longitude',meta.get('GPSLongitude'))]
        useful=[(k,v) for k,v in useful if v not in (None,'')]
        if useful:
            story += [Paragraph('Available embedded metadata',h2),table([[P('Metadata field',cell_bold),P('Value',cell_bold)]]+[[P(k),P(v)] for k,v in useful],[62*mm,118*mm])]
    else: story.append(Paragraph('No media file was submitted.',body))

    story += [Paragraph('FORENSIC FINGERPRINT / MEDIA DNA',h1),table([[P('Fingerprint field',cell_bold),P('Value',cell_bold)]]+[[P(k),P(v)] for k,v in data['fingerprint'].items()],[62*mm,118*mm])]
    if data['similarMedia']:
        story += [Paragraph('Related media matches',h2),table([[P('Case',cell_bold),P('Match',cell_bold),P('Platform / Date',cell_bold),P('Transform',cell_bold)]]+[[P(x['case']),P(f"{x['match']}%"),P(f"{x['platform']} / {x['date']}"),P(x['transform'])] for x in data['similarMedia'][:12]],[35*mm,25*mm,58*mm,62*mm])]
    else: story.append(Paragraph('No related media match was identified in the stored evidence set.',body))

    story += [Paragraph('CONTEXT INTEGRITY',h1),Paragraph(data['context']['assessment'],body),table([[P('Signal',cell_bold),P('Observed value',cell_bold),P('Interpretation',cell_bold)]]+[[P(x['label']),P(x['value']),P('Evidence signal recorded')] for x in data['context']['evidenceRows']],[52*mm,88*mm,40*mm])]

    story += [Paragraph('PROPAGATION INTELLIGENCE',h1)]
    if data['propagationNodes']:
        rows=[[P('Observed',cell_bold),P('Platform / Account',cell_bold),P('Similarity',cell_bold),P('Transformation',cell_bold),P('Route / Source',cell_bold)]]
        for x in data['propagationNodes']:
            route=f"{x.get('from') or 'Unknown'} → {x.get('to') or x.get('platform') or 'Unknown'}"
            if x.get('sourceUrl'): route += f"\n{x['sourceUrl']}"
            rows.append([P(timestamp(x.get('observed_at') or x.get('ts'))),P(f"{x.get('platform') or 'N/A'} / {x.get('account') or 'Unknown account'}"),P(f"{x.get('similarity','N/A')}%"),P(x.get('transformation') or x.get('transform') or 'N/A'),P(route)])
        story.append(table(rows,[35*mm,45*mm,25*mm,42*mm,33*mm]))
    else: story.append(Paragraph('No propagation observations have been recorded for this case.',body))
    if data['propagationLeads']:
        story += [Paragraph('Investigation leads',h2)]+[Paragraph(f'• {esc(x)}',body) for x in data['propagationLeads']]

    story += [Paragraph('EVIDENCE REGISTER',h1)]
    if data['evidence']:
        rows=[[P('Evidence ID',cell_bold),P('Type',cell_bold),P('DNA',cell_bold),P('Hash',cell_bold),P('Analysis',cell_bold),P('Added',cell_bold)]]
        for x in data['evidence']: rows.append([P(x['id']),P(x['type']),P(x['dna']),P(x['hash']),P(x['analysis']),P(timestamp(x['added']))])
        story.append(table(rows,[30*mm,22*mm,32*mm,22*mm,28*mm,46*mm]))
    else: story.append(Paragraph('No evidence items registered.',body))

    story += [Paragraph('AUDIT TRAIL / CHAIN OF ACTIONS',h1)]
    if data['audit']:
        rows=[[P('Timestamp (UTC)',cell_bold),P('Actor',cell_bold),P('Event',cell_bold)]]
        for x in data['audit']: rows.append([P(timestamp(x.get('t'))),P(x.get('actor') or 'System'),P(x.get('e'))])
        story.append(table(rows,[43*mm,35*mm,100*mm]))
    else: story.append(Paragraph('No audit events recorded.',body))

    story += [Paragraph('NEXT ACTIONS',h1)]+[Paragraph(f'{i+1}. {esc(x)}',body) for i,x in enumerate(data['overview']['nextActions'])]
    story += [Paragraph('INVESTIGATOR NOTES',h1),Paragraph(esc(data.get('notes') or 'No investigator notes recorded.'),body),Spacer(1,8),Paragraph('DISCLAIMER: AI-assisted findings are provided for investigator review and are not a certified forensic or legal determination.',small)]

    def footer(canvas, doc):
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor('#D7E0EA')); canvas.line(15*mm,11*mm,195*mm,11*mm)
        canvas.setFont('Helvetica',7); canvas.setFillColor(colors.HexColor('#64748B')); canvas.drawString(15*mm,7*mm,'TruthTrace • Forensic Case Report'); canvas.drawRightString(195*mm,7*mm,f'Page {doc.page}')
        canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    execute('INSERT INTO reports(case_id,path,created_at) VALUES(?,?,?)',(cid,str(path),now())); audit(cid,'Forensic PDF report generated')
    return FileResponse(path,media_type='application/pdf',filename=path.name)

