import React, { useEffect, useState } from "react";
import { Panel, SectionLabel } from "../../ui/Primitives";
import { api } from "../../../api";

function toneClass(t:string){
  return t==='green'?'text-emerald-700 bg-emerald-50 border-emerald-200':
    t==='amber'?'text-amber-800 bg-amber-50 border-amber-200':
    t==='red'?'text-red-700 bg-red-50 border-red-200':'text-slate-700 bg-slate-50 border-slate-200';
}
function toneLabel(t:string){return t==='green'?'Consistent':t==='amber'?'Needs Review':t==='red'?'Mismatch':'Observed'}
function mediaLabel(v:string){return v==='HIGH'?'Strong authenticity signal':v==='LOW'?'Weak authenticity signal':'Mixed authenticity signal'}
function consistencyLabel(v:string){return v==='HIGH'?'Consistent':v==='LOW'?'Inconsistent':'Needs review'}

export function ContextTab({caseId,intent}:{caseId:string;intent:any}){
  const[d,setD]=useState<any>();
  useEffect(()=>{api.case(caseId).then(setD)},[caseId]);
  if(!d)return <div className="p-8 text-sm text-slate-400">Loading context analysis…</div>;
  return <div className="mx-auto max-w-5xl px-8 py-8">
    <div>
      <div className="text-[10px] font-bold uppercase tracking-[.16em] text-blue-300">FORENSIC INTELLIGENCE / CONTEXT</div>
      <h2 className="mt-1 text-lg font-bold text-white">Context Integrity</h2>
      <p className="max-w-3xl text-[13px] leading-6 text-slate-400">Compare the submitted claim with extracted evidence signals, embedded capture metadata and model-derived contextual indicators.</p>
    </div>
    <div className="mt-5 grid gap-4 md:grid-cols-2">
      <Panel className="border-white/10 bg-[#0d1830] p-5"><SectionLabel>Media Authenticity</SectionLabel><div className="mt-2 text-xl font-black text-white">{mediaLabel(d.context.mediaAuthenticity)}</div><p className="mt-1 text-[11px] text-slate-600">How strongly the available evidence supports media authenticity.</p></Panel>
      <Panel className="border-white/10 bg-[#0d1830] p-5"><SectionLabel>Context Consistency</SectionLabel><div className="mt-2 text-xl font-black text-white">{consistencyLabel(d.context.contextConsistency)}</div><p className="mt-1 text-[11px] text-slate-600">Whether the claim is consistent with the available contextual evidence.</p></Panel>
    </div>
    <Panel className="mt-5 border-white/10 bg-[#0d1830] p-5"><SectionLabel>Claim Under Review</SectionLabel><div className="mt-3 rounded-md border border-white/5 bg-[#091226] p-4 text-[13px] leading-6 text-slate-200">{intent?.claim||d.context.claim||'Not provided'}</div></Panel>
    <Panel className="mt-5 border-white/10 bg-[#0d1830] p-5">
      <div className="flex items-end justify-between"><div><SectionLabel>Evidence Signals</SectionLabel><p className="mt-1 text-[11px] text-slate-500">Each row is an observed or model-derived signal; values are not presented as independent proof.</p></div></div>
      <div className="mt-4 overflow-hidden rounded-md border border-white/5">
        <div className="grid grid-cols-[minmax(190px,260px)_1fr_130px] gap-4 border-b border-white/10 bg-[#091226] px-4 py-3 text-[10px] font-bold uppercase tracking-[.12em] text-slate-500"><span>Signal</span><span>Observed value</span><span>Status</span></div>
        {(d.context.evidenceRows||[]).map((r:any)=><div key={r.label} className="grid grid-cols-[minmax(190px,260px)_1fr_130px] items-center gap-4 border-b border-white/5 px-4 py-3.5 last:border-0"><span className="text-[12px] font-medium text-slate-400">{r.label}</span><span className="min-w-0 break-words text-[12.5px] leading-5 text-slate-200">{r.value}</span><span className={`inline-flex w-fit items-center rounded border px-2 py-1 text-[10px] font-bold tracking-[.04em] ${toneClass(r.tone||'slate')}`}>{toneLabel(r.tone||'slate')}</span></div>)}
      </div>
    </Panel>
    <Panel className="mt-5 border-white/10 bg-[#0d1830] p-5"><SectionLabel>Assessment</SectionLabel><div className="mt-3 rounded-md border border-blue-400/10 bg-blue-400/[.03] p-4 text-[12.5px] leading-6 text-slate-300">{d.context.assessment||'Context assessment is evidence-led; absence of metadata is not proof of manipulation.'}</div></Panel>
  </div>
}
