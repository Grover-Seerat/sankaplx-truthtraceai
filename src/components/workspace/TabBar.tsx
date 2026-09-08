import React from "react";
import type { WorkspaceTabKey } from "../../types";

const TABS: { key: WorkspaceTabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "authenticity", label: "Authenticity • PRIMARY" },
  { key: "dna", label: "Media DNA" },
  { key: "context", label: "Context" },
  { key: "propagation", label: "Propagation" },
  { key: "evidence", label: "Evidence" },
  { key: "audio", label: "Audio Forensics" },
  { key: "copilot", label: "Investigator Copilot" },
  { key: "osint", label: "Web OSINT" },
  { key: "review", label: "Case Officer Review" },
  { key: "audit", label: "Audit Trail" },
];

export function TabBar({
  active,
  onChange,
  showAudio = true,
  showReview = false,
}: {
  active: WorkspaceTabKey;
  onChange: (key: WorkspaceTabKey) => void;
  showAudio?: boolean;
  showReview?: boolean;
}) {
  let visibleTabs = showAudio === false ? TABS.filter(t => t.key !== "audio") : TABS;
  if (!showReview) visibleTabs = visibleTabs.filter(t => t.key !== "review");
  return (
    <div className="flex gap-0 border-b border-white/10 bg-[#101316] px-6">
      {visibleTabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`relative px-3 py-2.5 text-[12px] font-medium transition-colors ${
            active === t.key ? "text-blue-300" : "text-slate-500 hover:text-slate-200"
          }`}
        >
          {t.label}
          {active === t.key && <span className="absolute inset-x-0 -bottom-px h-px bg-blue-300" />}
        </button>
      ))}
    </div>
  );
}
