import { Search, Fingerprint, AlertTriangle, Share2 } from "lucide-react";
import type { InvestigationTypeKey } from "../../types";

export interface DashboardCardConfig {
  key: InvestigationTypeKey;
  icon: typeof Search;
  title: string;
  desc: string;
  action: string;
}

export const DASHBOARD_CARDS: DashboardCardConfig[] = [
  {
    key: "verify-media",
    icon: Search,
    title: "Verify Media",
    desc: "I have suspicious media and want to investigate its authenticity and evidence.",
    action: "Start Media Investigation",
  },
  {
    key: "media-dna",
    icon: Fingerprint,
    title: "Media DNA Search",
    desc: "Have we encountered this or a similar piece of media before?",
    action: "Search Evidence Network",
  },
  {
    key: "verify-claim",
    icon: AlertTriangle,
    title: "Verify a Claim",
    desc: "Is authentic media being used with a misleading date, location, or story?",
    action: "Check Context",
  },
  {
    key: "trace-propagation",
    icon: Share2,
    title: "Trace Propagation",
    desc: "How did this content spread and where was it first observed?",
    action: "Start Trace",
  },
];
