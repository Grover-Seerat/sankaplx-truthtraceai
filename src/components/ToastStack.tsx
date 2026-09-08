import React from "react";
import type { ToastItem, ToastTone } from "../types";

const TONE_STYLES: Record<ToastTone, string> = {
  info: "border-blue-400/20 bg-blue-500/10 text-blue-200",
  success: "border-green-200 bg-green-50 text-green-800",
  warn: "border-amber-400/20 bg-amber-500/10 text-amber-200",
};

export function ToastStack({ toasts }: { toasts: ToastItem[] }) {
  return (
    <div className="fixed bottom-5 right-5 z-50 flex w-80 flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`animate-slideIn rounded-md border px-3 py-2.5 text-sm shadow-lg ${TONE_STYLES[toast.tone]}`}
        >
          {toast.message}
        </div>
      ))}
    </div>
  );
}
