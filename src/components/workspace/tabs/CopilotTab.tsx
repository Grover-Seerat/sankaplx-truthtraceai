import React,{useEffect,useMemo,useState} from 'react';
import {Bot,CheckCircle2,Lightbulb,ShieldCheck,Sparkles} from 'lucide-react';
import {Panel} from '../../ui/Primitives';
import {api} from '../../../api';

export function CopilotTab({caseId}:{caseId:string}){
 const[rows,setRows]=useState<any[]>([]);const[busy,setBusy]=useState(false);const[geminiBusy,setGeminiBusy]=useState(false);const[geminiResult,setGeminiResult]=useState<any>(null);const[data,setData]=useState<any>(null);
 useEffect(()=>{Promise.all([api.copilotHistory(caseId),api.case(caseId)]).then(([h,c])=>{setRows(h||[]);setData(c)}).catch(()=>{})},[caseId]);
 const prompts=useMemo(()=>{
   const mime=String(data?.media?.mimeType||'').toLowerCase();
   const base:any[]=[
    ['🔍','Evidence Interpretation','What forensic signals support the current assessment?'],
    ['⚠','Risk / Suspicion Analysis','Which aspects of this evidence are most suspicious or uncertain?'],
    ['🧠','Explain the Verdict','Explain the current verdict using the strongest stored evidence.'],
    ['🧭','Recommended Direction','What should the investigator verify next, based on this case?'],
    ['🌐','Propagation Review','What public-source leads and propagation observations have been found?'],
    ['🕒','Chronology Check','What does the case timeline tell us about evidence and analysis?'],
    ['🧬','Media DNA','What fingerprints, hashes, or related-media signals are available?'],
    ['📋','Case Brief','Give a concise investigative brief for this case.'],
   ];
   if(mime.startsWith('audio/')) base.splice(2,0,['🎙','Audio Integrity','What audio-specific signals should the reviewer pay attention to?']);
   if(mime.startsWith('video/')) base.splice(2,0,['🎬','Cross-Modal Check','What visual/audio inconsistencies should be checked in this video case?']);
   if(mime.startsWith('image/')) base.splice(2,0,['🖼','Visual Clues','What visible text, landmarks, objects, or visual clues are important here?']);
   return base;
 },[data]);
 const runGemini=async()=>{setGeminiBusy(true);setGeminiResult(null);try{const r=await api.geminiMedia(caseId);setGeminiResult(r.result||r)}catch(e:any){setGeminiResult({error:e.message||'Gemini evidence interpretation failed.'})}finally{setGeminiBusy(false)}};
 const ask=async(text:string)=>{if(busy)return;setBusy(true);setRows(r=>[...r,{role:'user',message:text}]);try{const x=await api.copilot(caseId,text);setRows(r=>[...r,{role:'assistant',message:x.answer}])}finally{setBusy(false)}};
 return <div className="mx-auto max-w-5xl px-8 py-8">
  <div className="text-[10px] font-bold uppercase tracking-[.16em] text-blue-300">AI / CONTEXT-AWARE COPILOT</div>
  <h2 className="mt-1 text-lg font-bold text-white">TruthTrace Investigation Copilot</h2>
  <p className="max-w-3xl text-[13px] leading-6 text-slate-400">Guided, case-specific investigative actions based on the selected evidence, stored forensic findings, OSINT leads, propagation observations and audit history.</p>
  <Panel className="mt-5 border-white/10 bg-white p-5">
   <div className="flex items-center justify-between gap-4"><div className="flex items-center gap-2 text-[11px] text-emerald-300"><ShieldCheck size={14}/> Evidence-grounded mode</div><div className="text-[10px] text-slate-600">Case {caseId}</div></div>
   <div className="mt-5 flex flex-col gap-3 rounded-lg border border-emerald-400/10 bg-emerald-400/[.025] p-4 sm:flex-row sm:items-center sm:justify-between"><div><div className="text-[10px] font-bold uppercase tracking-[.12em] text-emerald-300">Multimodal Gemini layer</div><div className="mt-1 text-[11px] leading-5 text-slate-500">Interpret the latest uploaded image, video, or audio using the claim and case context. TruthTrace forensic verdicts remain authoritative.</div></div><button disabled={geminiBusy} onClick={runGemini} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-[11px] font-semibold text-emerald-200 disabled:opacity-50"><Sparkles size={13}/>{geminiBusy?'Running Gemini…':'Run Gemini evidence interpretation'}</button></div>
   {geminiResult&&<div className="mt-3 rounded-lg border border-white/[.06] bg-white p-4"><div className="text-[10px] font-bold uppercase tracking-[.12em] text-blue-300">Gemini investigation result</div>{geminiResult.error?<div className="mt-2 text-[11px] text-red-200">{geminiResult.error}</div>:<div className="mt-3 space-y-2 text-[11px] leading-5 text-slate-300"><div><span className="text-slate-500">Summary:</span> {geminiResult.summary||'No summary returned.'}</div>{Array.isArray(geminiResult.visible_text)&&geminiResult.visible_text.length>0&&<div><span className="text-slate-500">Visible/OCR text:</span> {geminiResult.visible_text.join(' · ')}</div>}{Array.isArray(geminiResult.possible_manipulation)&&geminiResult.possible_manipulation.length>0&&<div><span className="text-slate-500">Possible manipulation:</span> {geminiResult.possible_manipulation.join(' · ')}</div>}</div>}</div>}
   <div className="mt-5 grid gap-3 sm:grid-cols-2">{prompts.map(([icon,title,q])=><button key={title} disabled={busy} onClick={()=>ask(q)} className="group rounded-lg border border-white/[.07] bg-[#091226] p-4 text-left hover:border-blue-400/25 hover:bg-blue-400/[.03] disabled:opacity-60"><div className="flex items-start justify-between gap-3"><div className="text-lg">{icon}</div><CheckCircle2 size={14} className="text-slate-700 group-hover:text-blue-300"/></div><div className="mt-3 text-[11px] font-bold uppercase tracking-[.1em] text-slate-200">{title}</div><div className="mt-2 text-[11px] leading-5 text-slate-500 group-hover:text-slate-400">{q}</div><div className="mt-3 inline-flex items-center gap-1 text-[9px] font-semibold uppercase tracking-[.12em] text-blue-300"><Sparkles size={10}/> Guided investigation</div></button>)}</div>
   <div className="mt-5 flex items-center gap-2 border-t border-white/5 pt-4 text-[10px] text-slate-600"><Lightbulb size={12}/> Investigation prompts are tailored to the active case and media type. Free-form text entry has been removed for the guided evaluator workflow.</div>
   {rows.length>0&&<div className="mt-5 space-y-3 border-t border-white/5 pt-5 max-h-[360px] overflow-y-auto">{rows.slice(-8).map((r,i)=><div key={i} className={`flex ${r.role==='user'?'justify-end':'justify-start'}`}><div className={`max-w-[86%] rounded-lg border px-4 py-3 text-[11px] leading-5 ${r.role==='user'?'border-blue-400/15 bg-blue-40０/[.０5] text-slate-2０':'border-white/5 bg-[#０８１１２３] text-slate-３００'}`}><div className={`mb-１ text-[９px] font-bold uppercase tracking-[.１２em] ${r.role==='user'?'text-blue-３００':'text-emerald-３００'}`}>{r.role==='user'?'Investigation action':'TruthTrace AI'}</div>{r.message}</div></div>)}</div>}
  </Panel>
 </div>;
}
