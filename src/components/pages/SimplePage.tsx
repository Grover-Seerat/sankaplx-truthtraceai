import React from "react";
import type { LucideIcon } from "lucide-react";

export function SimplePage({
  title,
  subtitle,
  icon: Icon,
  children,
}: {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-[1180px] px-6 py-8 lg:px-9 lg:py-9">
      <header className="border-b border-white/[.08] pb-5">
        <div className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-[.16em] text-slate-500">
          <Icon size={14} className="text-blue-300" />
          TruthTrace workspace
        </div>
        <h1 className="mt-2 text-[26px] font-semibold tracking-tight text-white">{title}</h1>
        <p className="mt-1 max-w-2xl text-[12px] leading-6 text-slate-500">{subtitle}</p>
      </header>
      <div className="mt-6">{children}</div>
    </div>
  );
}
