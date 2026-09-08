import type { LucideIcon } from "lucide-react";

/** Investigation-type keys used to drive the guided intake flow. */
export type InvestigationTypeKey =
  | "verify-media"
  | "media-dna"
  | "verify-claim"
  | "trace-propagation";

export interface InvestigationTypeConfig {
  label: string;
  icon: LucideIcon;
  prompt: string;
  question: string;
  placeholder: string;
}

export type UserRole = "investigator" | "case-officer" | "admin";
export type Permission =
  | "case:create" | "case:view" | "case:update" | "case:close" | "case:assign"
  | "evidence:upload" | "evidence:view" | "evidence:verify"
  | "analysis:run" | "analysis:view" | "propagation:create" | "propagation:view"
  | "report:create" | "report:view" | "audit:view" | "users:manage" | "system:manage";

export interface UserSession {
  session: string;
  userId: string;
  username: string;
  name: string;
  role: UserRole;
  expiresAt?: string;
  permissions?: Permission[];
}

export type Priority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type CaseStatus = "Active" | "Under Review" | "Closed";

export interface CaseSummary {
  id: string;
  type: string;
  priority: Priority;
  status: CaseStatus;
  updated: string;
}

/** Everything captured in Step 1 of the guided intake flow. */
export interface InvestigationIntent {
  claim: string;
  platform: string;
  date: string;
  location: string;
  withMedia: boolean;
}

export interface SimilarMediaMatch {
  case: string;
  match: number;
  platform: string;
  date: string;
  transform: string;
}

export interface PropagationNode {
  id: string;
  label: string;
  platform: string;
  ts: string;
  similarity: string;
  account: string;
  transform: string;
  spread: string;
  tag: string;
  /** Optional source/destination fields used to reconstruct media movement. */
  from?: string;
  to?: string;
  activity?: string;
  observedAt?: string;
  sourceUrl?: string;
}

export interface AuditEntry {
  t: string;
  e: string;
}

export interface EvidenceItem {
  id: string;
  caseId: string;          // ← added
  type: "Image" | "Video" | "Audio" | "Screenshot" | "URL";
  dna: string;
  hash: "Verified" | "N/A";
  analysis: "Complete" | "In Progress";
  added: string;
}

export type ToneKey = "green" | "blue" | "amber" | "red";

export interface OverviewSummary {
  authenticity: { value: string; sub: string; tone: ToneKey };
  mediaDna: { value: string; sub: string; tone: ToneKey };
  context: { value: string; tone: ToneKey };
  propagation: { value: string; tone: ToneKey };
  assessment: string;
  why: string[];
  nextActions: string[];
}

export interface AuthenticityResult {
  verdict: "Likely Authentic" | "Manipulated" | "AI-Generated" | "Inconclusive";
  confidence: number;
  summary: string;
}

export interface ContextEvidenceRow {
  label: string;
  value: string;
  tone: "amber" | "red" | "green" | "slate";
}

export interface ContextResult {
  mediaAuthenticity: "HIGH" | "MEDIUM" | "LOW";
  contextConsistency: "HIGH" | "MEDIUM" | "LOW";
  assessment: string;
  claim: string;
  evidenceRows: ContextEvidenceRow[];
}

/** Toast notification tone, mirrors the styling variants available. */
export type ToastTone = "info" | "success" | "warn";

export interface ToastItem {
  id: string;
  message: string;
  tone: ToastTone;
}

/** Top-level app views the sidebar can route to. */
export type AppView =
  | "dashboard"
  | "new-flow"
  | "workspace"
  | "active"
  | "dna-network"
  | "propagation"
  | "context"
  | "vault"
  | "reports"
  | "audit"
  | "settings"
  | "users"
  | "copilot"
  | "osint"
  | "review";

export type WorkspaceTabKey =
  | "overview"
  | "authenticity"
  | "dna"
  | "context"
  | "propagation"
  | "evidence"
  | "audit"
  | "audio"
  | "copilot"
  | "osint"
  | "review";

export interface CaseMedia {
  fileName: string;
  fileType: string;
  fileSize: string;
  mimeType?: string;
  sha256: string;
  width?: number;
  height?: number;
  duration?: string;
  source?: string;
  addedAt: string;
}

export interface MediaFamilyItem {
  label: string;
  relation: string;
}

export interface CaseData {
  id: string;
  investigationType: InvestigationTypeKey;
  intent: InvestigationIntent;

  overview: OverviewSummary;
  authenticity: AuthenticityResult;

  dnaId: string;
  fingerprint: Record<string, string>;
  media?: CaseMedia;

  similarMedia: SimilarMediaMatch[];
  mediaFamily?: MediaFamilyItem[];
  context: ContextResult;
  propagationNodes: PropagationNode[];
  propagationLeads: string[];
  audit: AuditEntry[];
  evidence: EvidenceItem[];

  notes?: string;
  referenceUrl?: string;
  forensics?: any;
}