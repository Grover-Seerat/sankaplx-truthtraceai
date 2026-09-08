import React, { useEffect, useState } from 'react';
import { CheckCircle2, ClipboardCheck, Clock3, ShieldAlert, Sparkles, XCircle } from 'lucide-react';
import { Panel, SectionLabel } from '../../ui/Primitives';
import { api } from '../../../api';
import { formatIST } from '../../../utils/dates';

export function CaseReviewTab({ caseId }: { caseId: string }) {
  const [reviews, setReviews] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [disposition, setDisposition] = useState('CONFIRM');
  const [sufficiency, setSufficiency] = useState('Sufficient');
  const [rationale, setRationale] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  const load = async () => {
    const [r, t] = await Promise.all([api.caseReview(caseId), api.timeline(caseId)]);
    setReviews(r || []);
    setTimeline(t || []);
  };

  useEffect(() => { load().catch(() => {}); }, [caseId]);

  const submit = async () => {
    if (rationale.trim().length < 10) {
      setMessage('Add a short rationale (at least 10 characters).');
      return;
    }
    setBusy(true); setMessage('');
    try {
      await api.caseReviewSubmit(caseId, {
        disposition,
        rationale,
        evidenceSufficiency: sufficiency,
      });
      setRationale('');
      await load();
      setMessage('Independent case review recorded in the audit trail.');
    } catch (e: any) {
      setMessage(e.message || 'Unable to record case review.');
    } finally { setBusy(false); }
  };

  return <div className="mx-auto max-w-6xl px-8 py-8">
    <div className="text-[10px] font-bold uppercase tracking-[.16em] text-blue-300">CASE OFFICER / ADJUDICATION</div>
    <h2 className="mt-1 text-lg font-bold text-white">Independent Case Review</h2>
    <p className="max-w-3xl text-[13px] leading-6 text-slate-400">Review the investigator's evidence, assess sufficiency, record an independent disposition, and keep a chronological case record.</p>

    <div className="mt-5 grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
      <Panel className="border-white/10 bg-[#0d1830] p-5">
        <div className="flex items-center gap-2"><ClipboardCheck size={15} className="text-blue-300"/><SectionLabel>Officer disposition</SectionLabel></div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {[['CONFIRM','Confirm finding',CheckCircle2],['CHALLENGE','Challenge finding',XCircle],['REQUEST_MORE_EVIDENCE','Request more evidence',ShieldAlert]].map(([v,label,Icon]: any)=><button key={v} onClick={()=>setDisposition(v)} className={`rounded-md border p-4 text-left ${disposition===v?'border-blue-400/30 bg-blue-400/10':'border-white/5 bg-[#091226]'}`}><Icon size={16} className={v==='CONFIRM'?'text-emerald-300':v==='CHALLENGE'?'text-red-300':'text-amber-300'}/><div className="mt-3 text-[11px] font-semibold text-white">{label}</div></button>)}
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div><label className="text-[10px] uppercase tracking-[.12em] text-slate-500">Evidence sufficiency</label><select value={sufficiency} onChange={e=>setSufficiency(e.target.value)} className="mt-2 w-full rounded-md border border-white/10 bg-[#091226] px-3 py-2.5 text-[12px] text-white"><option>Sufficient</option><option>Partially sufficient</option><option>Insufficient</option></select></div>
          <div className="rounded-md border border-white/5 bg-[#091226] p-3"><div className="text-[10px] uppercase tracking-[.12em] text-slate-500">Role boundary</div><div className="mt-2 text-[11px] leading-5 text-slate-300">Case Officer reviews and adjudicates. Forensic evidence modification remains protected.</div></div>
        </div>
        <label className="mt-4 block text-[10px] uppercase tracking-[.12em] text-slate-500">Officer rationale</label>
        <textarea value={rationale} onChange={e=>setRationale(e.target.value)} rows={4} placeholder="Explain why the evidence is sufficient, challenged, or requires further investigation…" className="mt-2 w-full resize-none rounded-md border border-white/10 bg-[#091226] px-3 py-3 text-[12px] text-white outline-none" />
        <button onClick={submit} disabled={busy} className="mt-3 rounded-md bg-blue-600 px-4 py-2.5 text-[12px] font-semibold text-white disabled:opacity-50">{busy?'Recording review…':'Record officer decision'}</button>
        {message && <div className="mt-3 rounded-md border border-white/5 bg-[#091226] px-3 py-2 text-[11px] text-slate-400">{message}</div>}
      </Panel>

      <Panel className="border-white/10 bg-[#0d1830] p-5">
        <div className="flex items-center gap-2"><Sparkles size={15} className="text-blue-300"/><SectionLabel>Review history</SectionLabel></div>
        <div className="mt-4 space-y-3">{reviews.length ? reviews.map((r,i)=><div key={i} className="rounded-md border border-white/5 bg-[#091226] p-4"><div className="flex items-center justify-between gap-3"><span className={`rounded-full px-2 py-1 text-[9px] font-bold ${r.disposition==='CONFIRM'?'bg-emerald-400/10 text-emerald-300':r.disposition==='CHALLENGE'?'bg-red-400/10 text-red-300':'bg-amber-400/10 text-amber-300'}`}>{r.disposition.replaceAll('_',' ')}</span><span className="text-[9px] text-slate-600">{formatIST(r.created_at)}</span></div><div className="mt-2 text-[11px] text-slate-300">{r.rationale}</div><div className="mt-2 text-[9px] uppercase tracking-[.1em] text-slate-600">Reviewer: {r.reviewer_name || r.reviewer_user_id || 'System'} · {r.evidence_sufficiency}</div></div>) : <div className="py-10 text-center text-[11px] text-slate-600">No officer review recorded yet.</div>}</div>
      </Panel>
    </div>

    <Panel className="mt-5 border-white/10 bg-[#0d1830] p-5">
      <div className="flex items-center gap-2"><Clock3 size={15} className="text-blue-300"/><SectionLabel>Case timeline · IST</SectionLabel></div>
      <div className="mt-4 space-y-2">{timeline.length ? timeline.slice(-16).reverse().map((x,i)=><div key={i} className="grid gap-2 rounded-md border border-white/5 bg-[#091226] px-4 py-3 md:grid-cols-[180px_130px_1fr]"><div className="text-[10px] text-slate-500">{formatIST(x.timestamp)}</div><div className="text-[9px] font-bold uppercase tracking-[.12em] text-blue-300">{x.type}</div><div><div className="text-[11px] font-semibold text-white">{x.title}</div><div className="mt-1 text-[10px] leading-5 text-slate-500">{x.detail}</div></div></div>) : <div className="py-8 text-center text-[11px] text-slate-600">Timeline data will appear as the case progresses.</div>}</div>
    </Panel>
  </div>;
}
