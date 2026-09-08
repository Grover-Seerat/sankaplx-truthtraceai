import React,{useEffect,useState} from 'react';
import {Sidebar} from './components/Sidebar';
import {ToastStack} from './components/ToastStack';
import {Dashboard} from './components/dashboard/Dashboard';
import {StepIntent} from './components/newInvestigation/StepIntent';
import {StepEvidence} from './components/newInvestigation/StepEvidence';
import {Workspace} from './components/workspace/Workspace';
import {MediaDnaTab} from './components/workspace/tabs/MediaDnaTab';
import {PropagationTab} from './components/workspace/tabs/PropagationTab';
import {ContextTab} from './components/workspace/tabs/ContextTab';
import {AuditTab} from './components/workspace/tabs/AuditTab';
import {CopilotTab} from './components/workspace/tabs/CopilotTab';
import {OsintTab} from './components/workspace/tabs/OsintTab';
import {ActiveCasesPage} from './components/pages/ActiveCasesPage';
import {EvidenceVaultPage} from './components/pages/EvidenceVaultPage';
import {ForensicReportsPage} from './components/pages/ForensicReportsPage';
import {CaseScopedPage} from './components/pages/CaseScopedPage';
import {SettingsPage} from './components/pages/SettingsPage';
import {UsersRolesPage} from './components/pages/UsersRolesPage';
import {ReportModal} from './components/workspace/ReportModal';
import {useToasts} from './hooks/useToasts';
import {api} from './api';
import {Login} from './components/Login';
import {INVESTIGATION_TYPE_LABEL} from './config';
import type {AppView,CaseSummary,InvestigationIntent,InvestigationTypeKey,UserRole,UserSession} from './types';
export default function App(){
 const [session,setSession]=useState<UserSession|null>(()=>{try{return JSON.parse(localStorage.getItem('truthtrace-session')||'null')}catch{return null}});
 const [view,setView]=useState<AppView>('dashboard'); const role:UserRole=session?.role || 'investigator'; const [cases,setCases]=useState<CaseSummary[]>([]); const [flowType,setFlowType]=useState<InvestigationTypeKey|null>(null); const [flowStep,setFlowStep]=useState<1|2>(1); const [intent,setIntent]=useState<InvestigationIntent|null>(null); const [activeCaseId,setActiveCaseId]=useState<string|null>(null); const [reportCaseId,setReportCaseId]=useState<string|null>(null); const {toasts,push}=useToasts();
 const refresh=()=>api.cases().then(setCases).catch(e=>push(e.message,'warn'));
 useEffect(()=>{if(session){api.me().then(s=>{const next={...session,...s};localStorage.setItem('truthtrace-session',JSON.stringify(next));setSession(next)}).catch(()=>{localStorage.removeItem('truthtrace-token');localStorage.removeItem('truthtrace-session');setSession(null)})}},[]);
 useEffect(()=>{if(session?.session) refresh()},[session?.session]);
 const startFlow=(t:InvestigationTypeKey)=>{setFlowType(t);setFlowStep(1);setIntent(null);setView('new-flow')};
 const launchWorkspace=async(draft:{file?:File;notes?:string;referenceUrl?:string})=>{if(!flowType||!intent)return; if((flowType==='verify-media'||flowType==='media-dna')&&!draft.file){push('Media evidence is required for this investigation type.','warn');return;} try{const c=await api.createCase({...intent,withMedia:Boolean(draft.file)},flowType,draft.notes,draft.referenceUrl); if(draft.file){await api.upload(c.id,draft.file); push('Evidence uploaded and fingerprinted by backend','success'); await api.analyze(c.id).catch(e=>push(`Analysis queued/failed: ${e.message}`,'warn'));} await refresh(); setActiveCaseId(c.id);setIntent(c.intent);setView('workspace');push(`${INVESTIGATION_TYPE_LABEL[flowType]} workspace opened — ${c.id}`,'success')}catch(e:any){push(e.message||'Unable to create case','warn')}};
 const selectCase=async(id:string)=>{if(!id){setActiveCaseId(null);return} try{const c=await api.case(id);setActiveCaseId(id);setIntent(c.intent)}catch(e:any){push(e.message,'warn')}};
 const openExisting=(c:CaseSummary)=>{selectCase(c.id);setView('workspace')};const navigate=(k:AppView|'new')=>k==='new'?startFlow(role==='admin'?'verify-claim':'verify-claim'):setView(k);
 const scoped=(title:string,subtitle:string,child:(id:string)=>React.ReactNode)=><CaseScopedPage title={title} subtitle={subtitle} cases={cases} selectedCaseId={activeCaseId} onSelectCase={selectCase}>{id=>child(id)}</CaseScopedPage>;
 let content:React.ReactNode; switch(view){
 case 'dashboard':content=<Dashboard cases={cases} onStart={startFlow} onOpenCase={openExisting} role={role}/>;break;
 case 'new-flow': if(!flowType)content=null; else if(flowStep===1)content=<StepIntent typeKey={flowType} onBack={()=>setView('dashboard')} onNext={i=>{setIntent(i);setFlowStep(2)}}/>; else if(intent)content=<StepEvidence typeKey={flowType} intent={intent} onBack={()=>setFlowStep(1)} onLaunch={launchWorkspace}/>; else content=null;break;
 case 'workspace':content=activeCaseId?<Workspace caseId={activeCaseId} intent={intent} role={role} onBack={()=>setView('dashboard')} onReport={()=>setReportCaseId(activeCaseId)} notify={push} onCloseCase={async()=>{if(!window.confirm('Close this case? The case will be marked Closed and write operations will be disabled.'))return;try{const r=await api.closeCase(activeCaseId);await refresh();push(r.alreadyClosed?'Case was already closed.':'Case closed successfully.','success');setActiveCaseId(null);setView('dashboard')}catch(e:any){push(e.message||'Unable to close case','warn')}}}/>:null;break;
 case 'active':content=<ActiveCasesPage cases={cases} onOpenCase={openExisting} title={role==='admin'?'All Cases':role==='case-officer'?'Assigned Cases':'My Cases'} subtitle={role==='admin'?'All investigations across the platform.':role==='case-officer'?'Cases assigned to this Case Officer account.':'Investigations assigned to this Investigator account.'}/>;break;
 case 'dna-network':content=scoped('Media DNA Network','Backend-computed visual similarity and evidence identity.',id=><MediaDnaTab caseId={id}/>);break;
 case 'propagation':content=scoped('Propagation Intelligence','Stored observations and similarity links.',id=><PropagationTab caseId={id}/>);break;
 case 'context':content=scoped('Context Verification','Evidence-led contextual consistency.',id=><ContextTab caseId={id} intent={intent}/>);break;
 case 'vault':content=<EvidenceVaultPage/>;break;
 case 'reports':content=<ForensicReportsPage cases={cases} onPreviewCase={id=>setReportCaseId(id)}/>;break;
 case 'audit':content=scoped('Audit Trail','Timestamped backend investigation events.',id=><AuditTab caseId={id}/>);break;
 case 'copilot':content=scoped('Investigator Copilot','Evidence-grounded case assistant.',id=><CopilotTab caseId={id}/>);break;
 case 'osint':content=scoped('Web Investigation','Public-web research leads linked to this case.',id=><OsintTab caseId={id}/>);break;
 case 'settings':content=<SettingsPage/>;break;
 case 'users':content=<UsersRolesPage/>;break; default:content=null;}
 if(!session) return <Login onLogin={s=>{localStorage.setItem('truthtrace-token',s.session);localStorage.setItem('truthtrace-session',JSON.stringify(s));setActiveCaseId(null);setReportCaseId(null);setIntent(null);setFlowType(null);setFlowStep(1);setView('dashboard');setSession(s)}}/>;
 return <div className="flex h-screen w-full bg-[#0b0d0f] font-sans text-slate-200 antialiased"><Sidebar onSignOut={async()=>{try{await api.logout()}catch{} localStorage.removeItem('truthtrace-token');localStorage.removeItem('truthtrace-session');setActiveCaseId(null);setReportCaseId(null);setIntent(null);setFlowType(null);setFlowStep(1);setView('dashboard');setSession(null)}} name={session.name} activeView={view==='new-flow'?'new':view==='workspace'?'active':view} onNavigate={navigate} role={role}/><main className="min-w-0 flex-1 overflow-y-auto">{content}</main><ToastStack toasts={toasts}/>{reportCaseId&&<ReportModal caseId={reportCaseId} onClose={()=>setReportCaseId(null)} notify={push}/>}</div>
}
