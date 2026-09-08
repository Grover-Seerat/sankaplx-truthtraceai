import React, { useRef, useState } from "react";
import {
  ArrowLeft, ChevronRight, Upload, Image as ImageIcon, Video, Camera,
  Link as LinkIcon, X, Loader2, MessageSquare, Globe, Calendar, MapPin, FileCheck,
} from "lucide-react";
import { Panel, SectionLabel } from "../ui/Primitives";
import { INVESTIGATION_TYPES } from "../../config";
import type { InvestigationIntent, InvestigationTypeKey } from "../../types";

const EVIDENCE_ADD_BUTTONS = [
  { label: "Image", icon: ImageIcon, accept: "image/*" },
  { label: "Video", icon: Video, accept: "video/*" },
  { label: "Audio", icon: MessageSquare, accept: "audio/*,.mpeg,.mpg,.mp2,.mp3,.wav,.m4a,.aac,.flac,.ogg,.oga,.opus,.wma,.aiff,.aif,.webm" },
  { label: "Screenshot", icon: Camera, accept: "image/*" },
];

export function StepEvidence({
  typeKey,
  intent,
  onBack,
  onLaunch,
}: {
  typeKey: InvestigationTypeKey;
  intent: InvestigationIntent;
  onBack: () => void;
  onLaunch: (draft: { file?: File; notes?: string; referenceUrl?: string }) => void;
}) {
  const cfg = INVESTIGATION_TYPES[typeKey];
  const [media, setMedia] = useState<{file: File; name: string; size: number; type: string} | undefined>();
  const [notes, setNotes] = useState("");
  const [url, setUrl] = useState("");
  const [launching, setLaunching] = useState(false);
  const requiresMedia = typeKey === "verify-media" || typeKey === "media-dna";
  const [hashing, setHashing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const summaryCards = [
    { label: "Claim", icon: MessageSquare, value: intent.claim || "Not specified" },
    { label: "Platform", icon: Globe, value: intent.platform || "Not specified" },
    { label: "Date", icon: Calendar, value: intent.date || "Not specified" },
    { label: "Location", icon: MapPin, value: intent.location || "Not specified" },
  ];

  const selectFile = async (file: File) => {
    setHashing(true);
    try { setMedia({file,name:file.name,size:file.size,type:file.type}); } finally { setHashing(false); }
  };

  const launch = () => {
    if (requiresMedia && !media) return;
    setLaunching(true);
    window.setTimeout(() => onLaunch({ file: media?.file, notes, referenceUrl: url }), 350);
  };

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <button onClick={onBack} className="flex items-center gap-1.5 text-[13px] text-slate-500 hover:text-white">
        <ArrowLeft size={14} /> Edit investigation intent
      </button>

      <h1 className="mt-4 text-2xl font-bold text-white">Evidence Board</h1>
      <p className="mt-1 text-sm text-slate-400">Everything collected for this {cfg.label.toLowerCase()} investigation is attached to the case. {requiresMedia ? "A media file is required for this investigation type." : "Media is optional and can be added here or later from the workspace."}</p>

      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {summaryCards.map((c) => {
          const Icon = c.icon;
          return (
            <Panel key={c.label} className="border-white/10 bg-[#0d1830] p-3.5">
              <div className="flex items-center gap-1.5 text-slate-500"><Icon size={13} /><SectionLabel>{c.label}</SectionLabel></div>
              <div className="mt-1.5 line-clamp-3 text-[13px] text-slate-200">{c.value}</div>
            </Panel>
          );
        })}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-5">
        <Panel className="border-white/10 bg-[#0d1830] p-4">
          <SectionLabel>Media Evidence</SectionLabel>
          {media ? (
            <div className="mt-2.5 flex items-center gap-3 rounded-md border border-emerald-400/20 bg-emerald-400/5 p-3">
              <div className="flex h-10 w-10 items-center justify-center rounded bg-blue-500/10 text-blue-300"><FileCheck size={17} /></div>
              <div className="min-w-0 text-[13px]">
                <div className="truncate font-medium text-slate-200">{media.name}</div>
                <div className="text-slate-500">{formatBytes(media.size)} · {media.type || "FILE"} · backend fingerprint on upload</div>
              </div>
              <button onClick={() => setMedia(undefined)} className="ml-auto text-slate-500 hover:text-white"><X size={14} /></button>
            </div>
          ) : (
            <button onClick={() => inputRef.current?.click()} className="mt-2.5 flex w-full flex-col items-center gap-1.5 rounded-md border border-dashed border-white/10 py-6 text-slate-500 hover:border-blue-400/40 hover:text-blue-300">
              <Upload size={18} />
              <span className="text-[13px]">{hashing ? "Generating SHA-256…" : "Choose image, video, audio, or screenshot"}</span>
            </button>
          )}
          <input ref={inputRef} type="file" accept="image/*,video/*,audio/*,.mpeg,.mpg,.mp2,.mp3,.wav,.m4a,.aac,.flac,.ogg,.oga,.opus,.wma,.aiff,.aif,.webm" className="hidden" onChange={(e) => e.target.files?.[0] && selectFile(e.target.files[0])} />
          <div className="mt-3 flex flex-wrap gap-2">
            {EVIDENCE_ADD_BUTTONS.map(({ label, icon: Icon, accept }) => (
              <button type="button" key={label} onClick={() => { if (inputRef.current) { inputRef.current.accept = accept; inputRef.current.click(); } }} className="flex items-center gap-1.5 rounded border border-white/10 px-2.5 py-1.5 text-[12px] text-slate-400 hover:border-blue-400/30 hover:text-blue-300">
                <Icon size={13} /> {label}
              </button>
            ))}
          </div>
        </Panel>

        <div className="flex flex-col gap-5">
          <Panel className="border-white/10 bg-[#0d1830] p-4">
            <SectionLabel>URL / Reference</SectionLabel>
            <div className="mt-2.5 flex items-center gap-2 rounded-md border border-white/10 bg-[#091226] px-3 py-2">
              <LinkIcon size={14} className="text-slate-500" />
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." className="w-full bg-transparent text-[13px] text-slate-200 placeholder:text-slate-600 focus:outline-none" />
            </div>
          </Panel>
          <Panel className="border-white/10 bg-[#0d1830] p-4">
            <SectionLabel>Case Notes</SectionLabel>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Add investigator notes or observations…" rows={3} className="mt-2.5 w-full resize-none rounded-md border border-white/10 bg-[#091226] px-3 py-2 text-[13px] text-slate-200 placeholder:text-slate-600 focus:border-blue-400 focus:outline-none" />
          </Panel>
        </div>
      </div>

      <div className="mt-8 flex items-center justify-between gap-4">
        {requiresMedia && !media ? <p className="text-[11px] text-amber-300">Add media evidence before opening this investigation.</p> : <span />}
        <button type="button" onClick={launch} disabled={launching || hashing || (requiresMedia && !media)} className="flex items-center gap-2 rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-70">
          {launching ? <><Loader2 size={15} className="animate-spin" /> Opening investigation workspace…</> : <>Open Investigation Workspace <ChevronRight size={15} /></>}
        </button>
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let size = bytes / 1024;
  let unit = units[0];
  for (let i = 1; i < units.length && size >= 1024; i++) {
    size /= 1024;
    unit = units[i];
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${unit}`;
}
