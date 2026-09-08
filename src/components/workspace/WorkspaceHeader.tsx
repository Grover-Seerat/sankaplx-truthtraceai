import React, { useRef } from "react";
import { ChevronLeft, Plus, FileText } from "lucide-react";
import { Pill, monoClass } from "../ui/Primitives";
import type { ToastTone } from "../../types";

export function WorkspaceHeader({
  caseId,
  onBack,
  onReport,
  onAddEvidence,
  notify,
  onCloseCase,
  status = "Active",
  canCloseCase = true,
  canAddEvidence = true,
}: {
  caseId: string;
  onBack: () => void;
  onReport: () => void;
  onAddEvidence: (file: File) => void | Promise<void>;
  notify: (message: string, tone?: ToastTone) => void;
  onCloseCase: () => void | Promise<void>;
  status?: "Active" | "Under Review" | "Closed";
  canCloseCase?: boolean;
  canAddEvidence?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="sticky top-0 z-10 border-b border-white/10 bg-[#071126]/95 px-6 py-3">
      <div className="flex items-center justify-between gap-5">
        <div className="flex items-center gap-4">
          <button type="button" onClick={onBack} className="text-slate-500 hover:text-white" aria-label="Back">
            <ChevronLeft size={18} />
          </button>
          <div>
            <div className="mb-1 text-[9px] font-bold uppercase tracking-[0.14em] text-blue-300">Digital Media Forensic Workspace</div>
            <div className={`text-[16px] font-semibold text-white ${monoClass}`}>{caseId}</div>
            <div className="mt-0.5 flex items-center gap-2 text-[12px]">
              <Pill className={status === "Closed" ? "border-slate-300 bg-slate-100 text-slate-600" : "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"}>STATUS: {status.toUpperCase()}</Pill>
            </div>
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          {canAddEvidence && status !== "Closed" && (
            <>
              <input
                ref={inputRef}
                type="file"
                accept="image/*,video/*,audio/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onAddEvidence(file);
                  e.currentTarget.value = "";
                }}
              />
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="flex items-center gap-1.5 rounded-md border border-white/10 px-3 py-2 text-[13px] font-medium text-slate-300 hover:border-blue-400/30 hover:bg-blue-400/[.04] hover:text-white"
              >
                <Plus size={14} /> Add Evidence
              </button>
            </>
          )}
          <button
            type="button"
            onClick={onReport}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-[13px] font-semibold text-white hover:bg-blue-700"
          >
            <FileText size={14} /> Generate Report
          </button>
          {canCloseCase && status !== "Closed" && <button
            type="button"
            onClick={onCloseCase}
            className="flex items-center gap-1.5 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[13px] font-medium text-red-700 hover:border-red-300 hover:bg-red-100"
          >
            Close Case
          </button>}
        </div>
      </div>
    </div>
  );
}
