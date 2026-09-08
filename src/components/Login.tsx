import React, { useState } from 'react';
import { ScanLine, ShieldCheck, UserRound, LockKeyhole, ArrowRight, Fingerprint } from 'lucide-react';
import { api } from '../api';
import type { UserSession } from '../types';

const demos = [
  ['Investigator','investigator@truthtrace.local','Investigator@123'],
  ['Case Officer','officer@truthtrace.local','Officer@123'],
  ['Administrator','admin@truthtrace.local','Admin@123'],
] as const;

export function Login({ onLogin }: { onLogin: (session: UserSession) => void }) {
  const [username,setUsername]=useState(''); const [password,setPassword]=useState(''); const [error,setError]=useState(''); const [loading,setLoading]=useState(false);
  const submit=async(e:React.FormEvent)=>{e.preventDefault();setLoading(true);setError('');try{const s=await api.login(username,password);localStorage.setItem('truthtrace-token',s.session);localStorage.setItem('truthtrace-session',JSON.stringify(s));onLogin(s)}catch(err:any){setError(err.message||'Unable to sign in')}finally{setLoading(false)}};
  const fill=(d:typeof demos[number])=>{setUsername(d[1]);setPassword(d[2]);setError('')};
  return <div className="min-h-screen bg-[#0b0d0f] text-slate-200 flex items-center justify-center px-5 relative overflow-hidden">
    
    <div className="relative w-full max-w-[980px] grid lg:grid-cols-[1.1fr_.9fr] overflow-hidden rounded-md border border-white/[.10] bg-[#111417]">
      <div className="hidden lg:flex p-10 flex-col justify-between border-r border-white/[.07]"><div><div className="flex items-center gap-3"><div className="brand-mark"><ScanLine size={18}/></div><div><div className="text-sm font-black tracking-[.18em] text-white">TRUTHTRACE</div><div className="text-[10px] text-slate-500">Digital Forensics Platform</div></div></div><div className="mt-20"><div className="eyebrow"><span className="eyebrow-line"/> SECURE INVESTIGATION ACCESS</div><h1 className="mt-4 text-4xl font-black leading-tight text-white">Investigate the claim.<br/><span className="text-blue-300">Follow the evidence.</span></h1><p className="mt-5 max-w-md text-sm leading-7 text-slate-400">TruthTrace assigns access from the authenticated account. Investigative permissions are enforced by the backend and scoped to authorized cases.</p></div></div><div className="text-[11px] text-slate-600">Local development environment • Server-assigned roles</div></div>
      <div className="p-7 sm:p-10"><div className="lg:hidden flex items-center gap-3 mb-10"><div className="brand-mark"><ScanLine size={18}/></div><div className="text-sm font-black tracking-[.18em] text-white">TRUTHTRACE</div></div>
        <div className="eyebrow"><span className="eyebrow-line"/> SIGN IN</div><h2 className="mt-3 text-2xl font-bold text-white">Secure access</h2><p className="mt-2 text-xs text-slate-500">Enter your TruthTrace account. Your role is resolved by the server.</p>
        <form onSubmit={submit} className="mt-7 space-y-4"><label className="block"><span className="field-label">Account ID</span><div className="relative"><UserRound size={15} className="field-icon"/><input required value={username} onChange={e=>setUsername(e.target.value)} className="field-input field-input-icon" placeholder="name@truthtrace.local" autoComplete="username"/></div></label><label className="block"><span className="field-label">Password</span><div className="relative"><LockKeyhole size={15} className="field-icon"/><input required type="password" value={password} onChange={e=>setPassword(e.target.value)} className="field-input field-input-icon" placeholder="••••••••" autoComplete="current-password"/></div></label>{error&&<div className="rounded-md border border-red-400/20 bg-red-400/5 px-3 py-2 text-xs text-red-300">{error}</div>}<button disabled={loading} className="w-full rounded-md bg-blue-500 px-4 py-3 text-xs font-bold text-white hover:bg-blue-400 disabled:opacity-50">{loading?'Authenticating…':'Sign in'} <ArrowRight size={14} className="inline ml-2"/></button></form>
        <div className="mt-6"><div className="flex items-center gap-2 text-[10px] uppercase tracking-[.16em] text-slate-600"><Fingerprint size={13}/> Development demo accounts</div><div className="mt-2 grid gap-2">{demos.map(d=><button key={d[0]} type="button" onClick={()=>fill(d)} className="flex items-center justify-between rounded-md border border-white/[.08] bg-[#15191d] px-3 py-2.5 text-left hover:border-blue-400/20 hover:bg-blue-400/[.04]"><span><span className="block text-[11px] font-semibold text-slate-300">{d[0]}</span><span className="block text-[10px] text-slate-600">{d[1]}</span></span><span className="text-[10px] text-blue-300">Use</span></button>)}</div></div>
      </div>
    </div>
  </div>
}
