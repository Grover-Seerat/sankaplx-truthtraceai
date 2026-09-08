import React from "react";
import { FolderOpen } from "lucide-react";
import { Panel, StatusPill, monoClass } from "../ui/Primitives";
import { SimplePage } from "./SimplePage";
import type { CaseSummary } from "../../types";
import { formatIST } from "../../utils/dates";

export function ActiveCasesPage({ cases, onOpenCase, title='Active Cases', subtitle='All investigations currently open across the platform.' }: { cases: CaseSummary[]; onOpenCase: (c: CaseSummary) => void; title?: string; subtitle?: string }) {
  const openCases = cases.filter((c) => c.status !== "Closed");

  return (
    <SimplePage
      title={title}
      subtitle={subtitle}
      icon={FolderOpen}
    >
      <Panel className="overflow-hidden">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="border-b border-white/5 bg-[#091226] text-[11px] uppercase tracking-wide text-slate-500">
              <th className="px-4 py-2.5 font-semibold">Case ID</th>
              <th className="px-4 py-2.5 font-semibold">Investigation Type</th>
              <th className="px-4 py-2.5 font-semibold">Status</th>
              <th className="px-4 py-2.5 font-semibold">Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {openCases.map((c) => (
              <tr
                key={c.id}
                onClick={() => onOpenCase(c)}
                className="cursor-pointer border-b border-slate-50 last:border-0 hover:bg-[#091226]"
              >
                <td className={`px-4 py-3 font-semibold text-white ${monoClass}`}>{c.id}</td>
                <td className="px-4 py-3 text-slate-400">{c.type}</td>
                <td className="px-4 py-3">
                  <StatusPill status={c.status} />
                </td>
                <td className="px-4 py-3 text-slate-500">{formatIST(c.updated)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </SimplePage>
  );
}
