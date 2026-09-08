import React,{useEffect,useState}from'react';
import{Globe2,Search,ExternalLink,Clock3,Image as ImageIcon,ScanSearch,Loader2,Sparkles}from'lucide-react';
import{Panel,SectionLabel}from'../../ui/Primitives';
import{api}from'../../../api';

async function searchUploadedImage(caseId:string,evidenceId:string){
  const token=localStorage.getItem('truthtrace-token')||'';
  const r=await fetch(api.evidenceFile(caseId,evidenceId),{headers:token?{Authorization:`Bearer ${token}`}:{}});
  if(!r.ok) throw new Error('Unable to retrieve the investigated image.');
  const blob=await r.blob();
  const file=new File([blob],'truthtrace-evidence.jpg',{type:blob.type||'image/jpeg'});
  const input=document.createElement('input'); input.type='file'; input.name='encoded_image';
  const dt=new DataTransfer(); dt.items.add(file); input.files=dt.files;
  const form=document.createElement('form'); form.method='POST'; form.action=`https://lens.google.com/v3/upload?ep=ccm&s=&st=${Date.now()}`; form.enctype='multipart/form-data'; form.target='_blank'; form.style.display='none';
  form.appendChild(input);
  const dims=document.createElement('input'); dims.type='hidden'; dims.name='processed_image_dimensions'; dims.value='1000,1000'; form.appendChild(dims);
  document.body.appendChild(form); form.submit(); form.remove();
}

export function OsintTab({caseId}:{caseId:string}){
 const[q,setQ]=useState('');const[results,setResults]=useState<any[]>([]);const[busy,setBusy]=useState(false);const[imageBusy,setImageBusy]=useState(false);const[aiBusy,setAiBusy]=useState(false);const[error,setError]=useState('');const[queries,setQueries]=useState<string[]>([]);const[data,setData]=useState<any>(null);
 useEffect(()=>{let on=true;api.case(caseId).then(x=>{if(on)setData(x)}).catch(()=>{});api.osintHistory(caseId).then(xs=>{const latest=xs[0]?.result||{};setResults(latest.results||[])}).catch(()=>{});return()=>{on=false}},[caseId]);
 const isImage=String(data?.media?.mimeType||'').startsWith('image/');
 const run=async()=>{setBusy(true);setError('');try{const r=await api.osint(caseId,q.trim());setResults(r.results||[]);if(r.status==='error'||!(r.results||[]).length)setError(r.error||'No public-web results were returned. Check the backend internet connection and try again.')}catch(e:any){setError(e.message||'Web investigation request failed.')}finally{setBusy(false)}};
 const runAiSearch=async()=>{setAiBusy(true);setError('');try{const r=await api.aiOsint(caseId);setResults(r.results||[]);setQueries(r.queries||[]);if(r.status==='error'||!(r.results||[]).length)setError(r.error||'No public-web leads were returned.')}catch(e:any){setError(e.message||'AI-guided web investigation failed.')}finally{setAiBusy(false)}};
 const runImage=async()=>{if(!data?.evidence?.[data.evidence.length-1]?.id){setError('No image evidence is available for this case.');return}setImageBusy(true);setError('');try{await searchUploadedImage(caseId,data.evidence[data.evidence.length-1].id)}catch(e:any){setError(e.message||'Image search failed.')}finally{setImageBusy(false)}};
 return <div className="mx-auto max-w-5xl px-8 py-8">
  <div className="text-[10px] font-bold uppercase tracking-[.16em] text-blue-300">OPEN-SOURCE INTELLIGENCE</div>
  <h2 className="mt-1 text-lg font-bold text-white">Web Investigation</h2>
  <p className="text-[13px] leading-6 text-slate-400">Search the claim and OCR text on the public web, and send the investigated image directly to visual-search engines for similar-image and source discovery.</p>
  {isImage&&<Panel className="mt-5 border-blue-400/20 bg-blue-400/[.04] p-5"><div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between"><div className="flex items-start gap-3"><ImageIcon size={18} className="mt-0.5 text-blue-300"/><div><div className="text-sm font-semibold text-white">Investigated image</div><div className="mt-1 text-[11px] text-slate-400">{data.media?.fileName||'Uploaded image'} · Search the actual evidence image, not only its claim.</div></div></div><button onClick={runImage} disabled={imageBusy} className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{imageBusy?<Loader2 size={15} className="animate-spin"/>:<ScanSearch size={15}/>} {imageBusy?'Opening visual search…':'Search uploaded image'}</button></div><div className="mt-3 text-[10px] leading-5 text-slate-500">Visual search opens Google Lens with the exact uploaded evidence image. DuckDuckGo is used as the public-web discovery layer for claim/OCR/AI-generated search queries; exact visual matching is opened through Google Lens.</div></Panel>}
  <div className="mt-5 flex flex-col gap-2 sm:flex-row"><button onClick={runAiSearch} disabled={aiBusy} className="inline-flex items-center justify-center gap-2 rounded-md border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm font-semibold text-emerald-200 disabled:opacity-50"><Sparkles size={15}/>{aiBusy?'AI searching…':'AI-guided web search'}</button><input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')run()}} placeholder="Search claim, event, location or phrase…" className="flex-1 rounded-md border border-white/10 bg-[#091226] px-3 py-3 text-sm text-white outline-none"/><button onClick={run} disabled={busy} className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 text-sm font-semibold text-white disabled:opacity-50"><Search size={15}/>{busy?'Searching…':'Search web'}</button></div>
  {queries.length>0&&<div className="mt-3 flex flex-wrap gap-2">{queries.map(x=><span key={x} className="rounded-full border border-blue-400/10 bg-blue-400/[.04] px-2.5 py-1 text-[9px] text-blue-200">{x}</span>)}</div>}
  {error&&<div className="mt-4 rounded-md border border-red-400/20 bg-red-400/[.05] px-4 py-3 text-[11px] leading-5 text-red-200">{error}</div>}
  <Panel className="mt-5 border-white/10 bg-[#0d1830] p-5"><div className="flex items-center gap-2"><Globe2 size={15} className="text-blue-300"/><SectionLabel>Public propagation leads</SectionLabel></div>{results.length?<div className="mt-4 space-y-2">{results.map((r,i)=><a key={i} href={r.url} target="_blank" rel="noreferrer" className="block rounded-md border border-white/5 bg-[#091226] p-4 hover:border-blue-400/20"><div className="flex items-start gap-3"><div className="min-w-0 flex-1"><div className="text-[12px] font-semibold text-white">{r.title}</div><div className="mt-1 break-all text-[10px] text-blue-300">{r.url}</div><div className="mt-2 flex items-center gap-1 text-[9px] text-slate-600"><Clock3 size={10}/> Query: {r.query}</div></div><ExternalLink size={13} className="shrink-0 text-slate-600"/></div></a>)}</div>:<div className="py-12 text-center text-sm text-slate-600">No web leads yet. Run a search to create an investigation lead set.</div>}</Panel>
  <div className="mt-4 text-[10px] text-slate-600">Coverage: search-provider results represent discoverable/indexed public-web leads, not the entire internet. Visual matches are investigative leads, not verified original-source proof.</div>
 </div>
}
