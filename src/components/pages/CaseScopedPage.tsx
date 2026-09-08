import React from "react";
import { ChevronDown, FolderOpen } from "lucide-react";
import type { CaseSummary } from "../../types";
import { monoClass, Panel } from "../ui/Primitives";

export function CaseScopedPage({
  title,
  subtitle,
  cases,
  selectedCaseId,
  onSelectCase,
  children,
}: {
  title: string;
  subtitle: string;
  cases: CaseSummary[];
  selectedCaseId: string | null;
  onSelectCase: (caseId: string) => void;
  children: (caseId: string) => React.ReactNode;
}) {
  if (!selectedCaseId) {
    return (
      <div className="mx-auto max-w-4xl px-8 py-12">
        <div className="flex items-center gap-2 text-blue-300">
          <FolderOpen size={18} />
          <span className="text-xs font-semibold uppercase tracking-wider">Case required</span>
        </div>
        <h1 className="mt-2 text-2xl font-bold text-white">{title}</h1>
        <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        <Panel className="mt-7 border-white/10 bg-[#0d1830] p-5">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Select investigation case
          </label>
          <div className="relative mt-2">
            <select
              defaultValue=""
              onChange={(e) => e.target.value && onSelectCase(e.target.value)}
              className="w-full appearance-none rounded-lg border border-white/10 bg-[#091226] px-3 py-3 pr-10 text-sm text-white outline-none focus:border-blue-400"
            >
              <option value="">Choose a case…</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} — {c.type} — {c.status}
                </option>
              ))}
            </select>
            <ChevronDown size={16} className="pointer-events-none absolute right-3 top-3.5 text-slate-500" />
          </div>
        </Panel>
      </div>
    );
  }

  return (
    <div className="min-h-full">
      <div className="sticky top-0 z-20 border-b border-white/10 bg-[#071126]/95 px-8 py-3 backdrop-blur">
        <div className="flex items-center gap-3 text-xs">
          <span className="text-slate-500">CASE</span>
          <span className={`font-semibold text-blue-200 ${monoClass}`}>{selectedCaseId}</span>
          <span className="text-slate-700">·</span>
          <button
            onClick={() => onSelectCase("")}
            className="text-slate-400 transition-colors hover:text-white"
          >
            Switch case
          </button>
        </div>
      </div>
      {children(selectedCaseId)}
    </div>
  );
}
