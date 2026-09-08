import { useCallback, useState } from "react";
import type { ToastItem, ToastTone } from "../types";

/**
 * Lightweight in-memory toast queue. Each toast auto-dismisses after ~4.2s.
 * Swap this out for a shared notification store if the app grows multi-panel.
 */
export function useToasts() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const push = useCallback((message: string, tone: ToastTone = "info") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((current) => [...current, { id, message, tone }]);
    setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 4200);
  }, []);

  return { toasts, push };
}
