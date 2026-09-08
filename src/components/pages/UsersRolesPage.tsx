import React, { useEffect, useState } from "react";
import { Users, UserPlus, ShieldCheck, ClipboardCheck, Search, KeyRound, UserRound, Link2 } from "lucide-react";
import { Panel } from "../ui/Primitives";
import { SimplePage } from "./SimplePage";
import { api } from "../../api";
import type { CaseSummary } from "../../types";

const labels: Record<string, string> = {
  investigator: "Investigator",
  "case-officer": "Case Officer",
  admin: "Administrator",
};

export function UsersRolesPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [form, setForm] = useState({ username: "", name: "", role: "investigator", password: "" });
  const [assignment, setAssignment] = useState({ userId: "", caseId: "" });
  const [msg, setMsg] = useState("");
  const [assignmentMsg, setAssignmentMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [userRows, caseRows] = await Promise.all([api.users(), api.cases()]);
      setUsers(userRows);
      setCases(caseRows);
    } catch (e: any) {
      setMsg(e.message || "Unable to load account directory");
    }
  };

  useEffect(() => { load(); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg("");
    setBusy(true);
    try {
      await api.createUser(form);
      setForm({ username: "", name: "", role: "investigator", password: "" });
      setMsg("User created successfully. Share the account ID and temporary password securely with the user.");
      await load();
    } catch (e: any) {
      setMsg(e.message || "Unable to create user");
    } finally {
      setBusy(false);
    }
  };

  const assign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignment.userId || !assignment.caseId) return;
    setAssignmentMsg("");
    setBusy(true);
    try {
      await api.assignCase(assignment.caseId, assignment.userId);
      setAssignmentMsg("Case assigned successfully. If it was closed, it has been reopened and is now Active.");
      setAssignment({ userId: "", caseId: "" });
    } catch (e: any) {
      setAssignmentMsg(e.message || "Unable to assign case");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SimplePage title="Users & Roles" subtitle="Provision server-controlled accounts and assign investigations without changing the forensic record." icon={Users}>
      <div className="grid gap-5 xl:grid-cols-[1.25fr_.9fr]">
        <Panel className="overflow-hidden">
          <div className="border-b border-white/[.06] px-5 py-4">
            <div className="text-[10px] uppercase tracking-[.16em] text-slate-500">Active accounts</div>
            <div className="mt-1 text-sm font-semibold text-white">Identity directory</div>
          </div>
          <div className="divide-y divide-white/[.05]">
            {users.map((u) => (
              <div key={u.id} className="flex items-center gap-3 px-5 py-4">
                <div className="metric-icon">
                  {u.role === "admin" ? <ShieldCheck size={15} /> : u.role === "case-officer" ? <ClipboardCheck size={15} /> : <Search size={15} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[12px] font-semibold text-white">{u.name}</div>
                  <div className="truncate text-[10px] text-slate-600">{u.username}</div>
                </div>
                <span className="rounded-md border border-blue-400/10 bg-blue-400/[.04] px-2 py-1 text-[10px] text-blue-200">{labels[u.role]}</span>
                <span className="text-[9px] uppercase tracking-wider text-emerald-300">{u.active ? "Active" : "Disabled"}</span>
              </div>
            ))}
          </div>
        </Panel>

        <div className="space-y-5">
          <Panel className="p-5">
            <div className="flex items-center gap-2">
              <UserPlus size={16} className="text-blue-300" />
              <div>
                <div className="text-[10px] uppercase tracking-[.16em] text-slate-500">Provision account</div>
                <div className="text-sm font-semibold text-white">Create login ID</div>
              </div>
            </div>
            <p className="mt-3 text-[11px] leading-5 text-slate-500">Administrators create accounts here. The server assigns the role; users never select their own role on the login page.</p>
            <form onSubmit={submit} className="mt-5 space-y-3">
              <div className="relative">
                <UserRound size={14} className="field-icon" />
                <input required className="field-input field-input-icon" placeholder="Full name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              </div>
              <input required type="email" className="field-input" placeholder="Account email / login ID" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} />
              <select className="field-input" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}>
                <option value="investigator">Investigator</option>
                <option value="case-officer">Case Officer</option>
                <option value="admin">Administrator</option>
              </select>
              <div className="relative">
                <KeyRound size={14} className="field-icon" />
                <input required minLength={10} type="password" className="field-input field-input-icon" placeholder="Temporary password (10+ characters)" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
              </div>
              <button disabled={busy} type="submit" className="w-full rounded-lg bg-blue-500 px-4 py-3 text-xs font-bold text-white hover:bg-blue-400 disabled:opacity-50">{busy ? "Creating…" : "Create account"}</button>
              {msg && <div className="rounded-md border border-white/[.06] bg-white/[.02] px-3 py-2 text-[11px] leading-5 text-slate-400">{msg}</div>}
            </form>
          </Panel>

          <Panel className="p-5">
            <div className="flex items-center gap-2">
              <Link2 size={16} className="text-blue-300" />
              <div>
                <div className="text-[10px] uppercase tracking-[.16em] text-slate-500">Case assignment</div>
                <div className="text-sm font-semibold text-white">Assign an investigation</div>
              </div>
            </div>
            <p className="mt-3 text-[11px] leading-5 text-slate-500">Assign an investigation to a Case Officer or Investigator. Closed cases remain available here so an Administrator can reopen one through reassignment.</p>
            <form onSubmit={assign} className="mt-4 space-y-3">
              <select required className="field-input" value={assignment.userId} onChange={e => setAssignment({ ...assignment, userId: e.target.value })}>
                <option value="">Select user</option>
                {users.filter(u => u.role !== "admin").map(u => <option key={u.id} value={u.id}>{u.name} — {labels[u.role]}</option>)}
              </select>
              <select required className="field-input" value={assignment.caseId} onChange={e => setAssignment({ ...assignment, caseId: e.target.value })}>
                <option value="">Select case</option>
                {cases.map(c => <option key={c.id} value={c.id}>{c.id} — {c.type} — {c.status}</option>)}
              </select>
              <button disabled={busy || !assignment.userId || !assignment.caseId} type="submit" className="w-full rounded-lg border border-blue-400/20 bg-blue-400/[.06] px-4 py-3 text-xs font-bold text-blue-200 hover:bg-blue-400/[.1] disabled:opacity-50">{busy ? "Assigning…" : "Assign case"}</button>
              {assignmentMsg && <div className="text-[11px] leading-5 text-slate-400">{assignmentMsg}</div>}
            </form>
          </Panel>
        </div>
      </div>
    </SimplePage>
  );
}
