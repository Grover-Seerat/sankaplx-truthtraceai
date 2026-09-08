import type { CaseData, CaseSummary, InvestigationIntent, UserSession } from './types';
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('truthtrace-token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path:string, init:RequestInit = {}):Promise<T>{
  const headers = new Headers(init.headers);
  Object.entries(authHeaders()).forEach(([k,v]) => headers.set(k,String(v)));
  const r=await fetch(`${API}${path}`,{...init,headers});
  if(!r.ok){let msg='API request failed'; try{msg=(await r.json()).detail||msg}catch{}; if(r.status===401){localStorage.removeItem('truthtrace-token');localStorage.removeItem('truthtrace-session')} throw new Error(msg)}
  return r.json();
}
export const api={
 login:(username:string,password:string)=>request<UserSession>('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})}),
 me:()=>request<UserSession>('/auth/me'),
 logout:()=>request<{ok:boolean}>('/auth/logout',{method:'POST'}),
 cases:()=>request<CaseSummary[]>('/cases'),
 case:(id:string)=>request<CaseData>(`/cases/${encodeURIComponent(id)}`),
 closeCase:(id:string)=>request<{ok:boolean;status:string;alreadyClosed?:boolean;closedAt?:string}>(`/cases/${encodeURIComponent(id)}/close`,{method:'POST'}),
 createCase:(intent:InvestigationIntent,type:string,notes='',referenceUrl='')=>request<CaseData>('/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({investigationType:type,claim:intent.claim,platform:intent.platform,date:intent.date,location:intent.location,withMedia:intent.withMedia,notes,referenceUrl,priority:'HIGH'})}),
 upload:async(id:string,file:File)=>{const fd=new FormData();fd.append('file',file);return request<any>(`/cases/${encodeURIComponent(id)}/evidence`,{method:'POST',body:fd})},
 analyze:(id:string)=>request<any>(`/cases/${encodeURIComponent(id)}/analyze`,{method:'POST'}),
 evidence:()=>request<any[]>('/evidence'),
 propagation:(id:string)=>request<any[]>(`/cases/${encodeURIComponent(id)}/propagation`),
 copilotHistory:(id:string)=>request<any[]>(`/cases/${encodeURIComponent(id)}/copilot/history`),
 copilot:(id:string,message:string)=>request<{answer:string}>(`/cases/${encodeURIComponent(id)}/copilot`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message})}),
 osint:(id:string,query:string)=>request<any>(`/cases/${encodeURIComponent(id)}/osint/search`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query})}),
 osintHistory:(id:string)=>request<any[]>(`/cases/${encodeURIComponent(id)}/osint`),
 evidenceFile:(caseId:string,evidenceId:string)=>`${API}/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(evidenceId)}/file`,
 tracePropagation:(id:string)=>request<any>(`/cases/${encodeURIComponent(id)}/propagation/trace`,{method:'POST'}),
 audit:(id:string)=>request<any[]>(`/cases/${encodeURIComponent(id)}/audit`),
 dashboard:()=>request<any>('/dashboard'),
 users:()=>request<any[]>('/users'),
 createUser:(data:{username:string;name:string;role:string;password:string})=>request<any>('/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),
 assignCase:(caseId:string,userId:string)=>request<any>(`/cases/${encodeURIComponent(caseId)}/assign`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({userId})}),
 report:(id:string)=>fetch(`${API}/cases/${encodeURIComponent(id)}/report`,{headers:authHeaders()}),
};
