import React, { useState } from "react";
import { ArrowLeft, ChevronDown } from "lucide-react";
import { INVESTIGATION_TYPES } from "../../config";
import type { InvestigationIntent, InvestigationTypeKey } from "../../types";

const PLATFORM_OPTIONS = ["Instagram", "X / Twitter", "Facebook", "WhatsApp", "Telegram", "News Website", "Other"];

export function StepIntent({
  typeKey,
  onBack,
  onNext,
}: {
  typeKey: InvestigationTypeKey;
  onBack: () => void;
  onNext: (intent: InvestigationIntent) => void;
}) {
  const cfg = INVESTIGATION_TYPES[typeKey];
  const Icon = cfg.icon;
  const [claim, setClaim] = useState("");
  const [platform, setPlatform] = useState("");
  const [date, setDate] = useState("");
  const [location, setLocation] = useState("");

  const canContinue = claim.trim().length > 0;

  const submit = () => {
    // Media selection happens on the dedicated Evidence Board. This keeps
    // the intent step focused on the claim and prevents a second upload step.
    onNext({ claim, platform, date, location, withMedia: false });
  };

  return (
    <div className="mx-auto max-w-2xl px-8 py-10">
      <button onClick={onBack} className="flex items-center gap-1.5 text-[13px] text-slate-500 hover:text-slate-300">
        <ArrowLeft size={14} /> Back to dashboard
      </button>

      <div className="mt-6 flex items-center gap-2.5 text-blue-600">
        <Icon size={18} />
        <span className="text-[12px] font-semibold uppercase tracking-wide">{cfg.label}</span>
      </div>
      <h1 className="mt-1 text-2xl font-bold text-white">{cfg.prompt}</h1>
      <p className="mt-1 text-sm text-slate-500">
        Tell us what you know so far. You will add or review digital evidence on the next step.
      </p>

      <div className="mt-8 flex flex-col gap-6">
        <div>
          <label className="text-[13px] font-semibold text-slate-300">{cfg.question}</label>
          <textarea
            value={claim}
            onChange={(e) => setClaim(e.target.value)}
            placeholder={cfg.placeholder}
            rows={4}
            className="mt-2 w-full resize-none rounded-md border border-white/10 bg-[#0b1628] px-3 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div className="grid grid-cols-2 gap-5">
          <div>
            <label className="text-[13px] font-semibold text-slate-300">Where did you encounter this?</label>
            <div className="relative mt-2">
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full appearance-none rounded-md border border-white/10 bg-[#0d1830] px-3 py-2.5 text-sm text-slate-200 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Select platform</option>
                {PLATFORM_OPTIONS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="pointer-events-none absolute right-3 top-3 text-slate-500" />
            </div>
          </div>
          <div>
            <label className="text-[13px] font-semibold text-slate-300">Approximate date of the claim</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="mt-2 w-full rounded-md border border-white/10 bg-[#0d1830] px-3 py-2.5 text-sm text-slate-200 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 [&::-webkit-calendar-picker-indicator]:invert"
            />
          </div>
        </div>

        <div>
          <label className="text-[13px] font-semibold text-slate-300">Known location</label>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Chandigarh, India"
            className="mt-2 w-full rounded-md border border-white/10 bg-[#0b1628] px-3 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div className="rounded-lg border border-blue-400/10 bg-blue-400/[.03] p-4">
          <div className="text-[10px] font-bold uppercase tracking-[.16em] text-blue-300">Next step</div>
          <p className="mt-1 text-[12px] leading-5 text-slate-400">Continue to the Evidence Board to add media when the investigation requires it. You will not be asked to upload the same media again.</p>
          <button
            type="button"
            disabled={!canContinue}
            onClick={submit}
            className="mt-3 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Continue to Evidence Board <span className="ml-1">→</span>
          </button>
        </div>
      </div>
    </div>
  );
}
