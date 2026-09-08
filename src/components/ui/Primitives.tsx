import React from "react";
import type { Priority, CaseStatus } from "../../types";

export const monoClass = "font-mono";

const PRIORITY_STYLES: Record<Priority, string> = {
  CRITICAL: "bg-red-500/10 text-red-300 border-red-400/20",
  HIGH: "bg-orange-500/10 text-orange-300 border-orange-400/20",
  MEDIUM: "bg-amber-500/10 text-amber-300 border-amber-400/20",
  LOW: "bg-slate-500/10 text-slate-300 border-white/10",
};

const STATUS_STYLES: Record<CaseStatus, string> = {
  Active: "bg-emerald-500/10 text-emerald-300 border-emerald-400/20",
  "Under Review": "bg-amber-500/10 text-amber-300 border-amber-400/20",
  Closed: "bg-slate-500/10 text-slate-400 border-white/10",
};

export function Pill({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-semibold tracking-wide ${className}`}
    >
      {children}
    </span>
  );
}

export function PriorityPill({ level }: { level: Priority }) {
  return <Pill className={PRIORITY_STYLES[level]}>{level}</Pill>;
}

export function StatusPill({ status }: { status: CaseStatus }) {
  return <Pill className={STATUS_STYLES[status]}>{status}</Pill>;
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
      {children}
    </div>
  );
}

export function Panel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-md border border-white/10 bg-[#0d1830] ${className}`}>
      {children}
    </div>
  );
}

type DialTone = "green" | "amber" | "red" | "blue";

export function ScoreDial({
  value,
  label,
  tone = "blue",
  size = 84,
}: {
  value: number;
  label?: string;
  tone?: DialTone;
  size?: number;
}) {
  const toneMap: Record<DialTone, string> = {
    green: "bg-emerald-400",
    amber: "bg-amber-400",
    red: "bg-red-400",
    blue: "bg-blue-400",
  };

  return (
    <div className="w-full" style={{ maxWidth: size * 2.3 }}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-2xl font-semibold tracking-tight text-white">{value}%</span>
        {label && <span className="text-[10px] uppercase tracking-[.12em] text-slate-500">{label}</span>}
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-sm bg-[#252b31]">
        <div
          className={`h-full ${toneMap[tone]}`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%`, transition: "width 600ms ease" }}
        />
      </div>
    </div>
  );
}
