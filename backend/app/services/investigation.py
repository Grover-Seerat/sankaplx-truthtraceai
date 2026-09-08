import os, re, json, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone


def _clean_html(value):
    value=re.sub(r'<script.*?</script>|<style.*?</style>', ' ', value, flags=re.S|re.I)
    value=re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def _search_duckduckgo(query, limit=8):
    q=urllib.parse.quote_plus(query.strip())
    endpoints=[f'https://html.duckduckgo.com/html/?q={q}',f'https://lite.duckduckgo.com/lite/?q={q}']
    last_error='Search provider unavailable'
    for url in endpoints:
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36','Accept-Language':'en-US,en;q=0.9'})
            with urllib.request.urlopen(req,timeout=15) as response: html=response.read().decode('utf-8','ignore')
            items=[]
            for m in re.finditer(r'<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',html,re.S|re.I):
                href=urllib.parse.unquote(m.group(1)); title=_clean_html(m.group(2))
                if href.startswith('//'): href='https:'+href
                if href and title: items.append({'title':title,'url':href,'query':query})
                if len(items)>=limit: break
            if not items:
                for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',html,re.S|re.I):
                    href=urllib.parse.unquote(m.group(1)); title=_clean_html(m.group(2))
                    if href.startswith('//'): href='https:'+href
                    if not href.startswith(('http://','https://')) or 'duckduckgo.com' in urllib.parse.urlparse(href).netloc or len(title)<3: continue
                    items.append({'title':title,'url':href,'query':query})
                    if len(items)>=limit: break
            if items: return {'status':'ok','provider':'DuckDuckGo','query':query,'results':items}
            last_error='Search provider returned no parseable results'
        except Exception as e: last_error=str(e)[:220]
    return {'status':'error','provider':'DuckDuckGo','query':query,'results':[],'error':last_error}


def _reference_lead(reference_url, query):
    if not reference_url: return None
    try:
        u=urllib.parse.urlparse(reference_url)
        if u.scheme in ('http','https') and u.netloc:
            return {'title':f'Reference URL for case: {u.netloc}','url':reference_url,'query':query,'source':'case reference'}
    except Exception: pass
    return None


def osint_search(claim='', ocr_text='', reference_url=''):
    queries=[]
    if claim.strip(): queries.append(claim.strip())
    if ocr_text.strip():
        clean=' '.join(ocr_text.split())[:180]
        if clean and clean not in queries: queries.append(clean)
    results=[]
    for q in queries[:3]: results.extend(_search_duckduckgo(q).get('results',[]))
    ref=_reference_lead(reference_url, queries[0] if queries else 'case reference')
    if ref: results.insert(0,ref)
    seen=set(); dedup=[]
    for x in results:
        if x.get('url') not in seen: seen.add(x.get('url')); dedup.append(x)
    error='Public search did not return parseable results. Check internet access and try again.' if not dedup and queries else None
    return {'status':'ok' if dedup else 'error','queries':queries[:3],'results':dedup[:20],'searched_at':datetime.now(timezone.utc).isoformat(),'error':error}


def _num(v, default=None):
    try: return float(v)
    except: return default


def _case_facts(case, analysis, propagation, osint, evidence, audit):
    """Build a compact, database-derived fact set. No external facts are added."""
    a=analysis or {}; v=a.get('verdict',{}) or {}; models=a.get('models',{}) or {}; signals=a.get('signals',{}) or {}
    facts={
        'case': {k: case.get(k) for k in ['id','investigation_type','claim','platform','date','location','status','notes','reference_url','created_at','updated_at']},
        'evidence': [], 'analysis': {'verdict':v,'warnings':a.get('warnings',[]),'models':models,'signals':signals},
        'propagation': propagation or [], 'osint': (osint or {}).get('results',[]) if isinstance(osint,dict) else [],
        'audit': audit or []
    }
    for e in evidence or []:
        facts['evidence'].append({k:e[k] for k in ['id','file_name','mime_type','file_type','file_size','sha256','phash','dna_id','width','height','duration','analysis_status','created_at'] if k in e})
    return facts


def _case_summary(f):
    c=f['case']; v=f['analysis'].get('verdict') or {}
    ev=f['evidence']; props=f['propagation']; osr=f['osint']; aud=f['audit']
    lines=[f"Case {c.get('id') or 'unknown'} is {c.get('status') or 'unknown'}."]
    lines.append(f"Claim: {c.get('claim') or 'Not provided'}.")
    if c.get('investigation_type'): lines.append(f"Investigation type: {c['investigation_type']}.")
    if c.get('platform'): lines.append(f"Platform: {c['platform']}.")
    if c.get('date'): lines.append(f"Claim/event date: {c['date']}.")
    if c.get('location'): lines.append(f"Location: {c['location']}.")
    lines.append(f"Evidence items: {len(ev)}. Latest forensic assessment: {v.get('label','Inconclusive')} ({v.get('confidence',0)}% confidence).")
    if v.get('reason'): lines.append(f"Assessment reason: {v['reason']}")
    if v.get('ai_probability') is not None: lines.append(f"AI probability: {v['ai_probability']}%.")
    ad=models=f['analysis'].get('models',{}) or {}
    audio=ad.get('audio_detector') or {}
    if audio.get('ai_probability') is not None: lines.append(f"Audio detector AI probability: {float(audio['ai_probability']):.1f}%.")
    if props: lines.append(f"Propagation observations: {len(props)}.")
    if osr: lines.append(f"Stored OSINT leads: {len(osr)} from the latest saved web search.")
    lines.append(f"Audit events: {len(aud)}.")
    return ' '.join(lines)


def grounded_chat(case, analysis, propagation, message, osint=None, evidence=None, audit=None):
    """Answer strictly from the selected case's database context."""
    f=_case_facts(case or {},analysis,propagation,osint,evidence,audit)
    c=f['case']; msg=(message or '').lower().strip()
    if not c.get('id'): return 'No case was found. Select a valid case before using Investigator Copilot.'
    if not (message or '').strip(): return 'Ask a question about the selected case.'

    # Prefer Gemini for natural-language reasoning when configured; fall back to the
    # deterministic evidence-grounded responder below if Gemini is unavailable.
    try:
        from .gemini_service import answer_case_question
        return answer_case_question(message.strip(), f)
    except Exception:
        pass

    if any(k in msg for k in ['summary','summarize','overview','everything','whole case','complete case']):
        return _case_summary(f)

    if any(k in msg for k in ['evidence','file','media','upload','sha','hash','dna']):
        if not f['evidence']: return f"Case {c['id']} has no evidence records in the database."
        out=[f"Case {c['id']} has {len(f['evidence'])} evidence item(s):"]
        for e in f['evidence']:
            size=e.get('file_size'); size_txt=f"{size/1048576:.2f} MB" if isinstance(size,(int,float)) else 'size unavailable'
            out.append(f"• {e.get('id')}: {e.get('file_name')} ({e.get('file_type') or e.get('mime_type')}, {size_txt}, analysis {e.get('analysis_status') or 'unknown'}). SHA-256 {e.get('sha256') or 'not recorded'}.")
        return '\n'.join(out)

    if any(k in msg for k in ['verdict','authentic','fake','manipulat','ai probability','detector','forensic']):
        v=f['analysis'].get('verdict') or {}; models=f['analysis'].get('models',{}) or {}
        parts=[f"Case {c['id']} forensic verdict: {v.get('label','Inconclusive')} ({v.get('confidence',0)}% confidence).",v.get('reason','No forensic reason is stored.')]
        for name,label,key in [('audio_detector','Audio synthetic probability','ai_probability'),('organika','Organika synthetic probability','fake_probability'),('steganographia','SteganographIA synthetic probability','fake_probability')]:
            m=models.get(name) or {}
            if m.get(key) is not None:
                val=float(m[key]); val=val*100 if key=='fake_probability' and val<=1 else val
                parts.append(f"{label}: {val:.1f}%.")
        warnings=f['analysis'].get('warnings') or []
        if warnings: parts.append('Warnings: '+'; '.join(map(str,warnings[:5])))
        return ' '.join(parts)

    if any(k in msg for k in ['propagation','spread','similar','related','trace']):
        p=f['propagation']
        if not p: return f"No propagation observations are stored for case {c['id']}. Run the propagation trace to create database observations."
        lines=[f"Case {c['id']} has {len(p)} stored propagation observation(s)."]
        for x in p[:12]: lines.append(f"• {x.get('platform') or 'Unknown platform'} — similarity {x.get('similarity','n/a')}%, {x.get('transformation') or 'observation'}, source {x.get('source_url') or 'not recorded'}.")
        lines.append('These are database observations/leads and do not by themselves prove original source or chronology.')
        return '\n'.join(lines)

    if any(k in msg for k in ['web','source','osint','search','earliest']):
        r=f['osint']
        if not r: return f"No saved OSINT results are currently associated with case {c['id']}. Run Web OSINT for this case first."
        lines=[f"The latest saved OSINT search for case {c['id']} contains {len(r)} lead(s):"]
        for x in r[:10]: lines.append(f"• {x.get('title') or 'Untitled'} — {x.get('url') or 'URL unavailable'}")
        lines.append('OSINT entries are public-web leads and should be independently verified.')
        return '\n'.join(lines)

    if any(k in msg for k in ['audit','timeline','history','closed','status']):
        lines=[f"Case {c['id']} status: {c.get('status') or 'unknown'}.",f"Created: {c.get('created_at') or 'not recorded'}; updated: {c.get('updated_at') or 'not recorded'}. Audit events: {len(f['audit'])}."]
        for x in f['audit'][-10:]: lines.append(f"• {x.get('timestamp')}: {x.get('event')} (actor {x.get('actor_user_id') or 'system'}).")
        return '\n'.join(lines)

    if any(k in msg for k in ['next','investigate','recommend','should i']):
        actions=[]
        if not analysis: actions.append('Run forensic analysis for the selected evidence.')
        if not propagation: actions.append('Run propagation trace against stored evidence.')
        if not osint or not osint.get('results'): actions.append('Run Web OSINT using the case claim/OCR and review the saved leads.')
        actions += ['Review the evidence-level forensic reasoning.','Verify important provenance/chronology claims independently before reporting.']
        return 'Recommended next steps for this case: ' + ' '.join(f'{i+1}. {a}' for i,a in enumerate(actions))

    return (_case_summary(f)+"\n\nI can answer questions about this case's evidence, forensic results, propagation, OSINT, audit history, status, or recommended next steps. I will not use information from another case.")
