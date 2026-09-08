import React, { useEffect, useState } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { TabBar } from "./TabBar";
import { OverviewTab } from "./tabs/OverviewTab";
import { AuthenticityTab } from "./tabs/AuthenticityTab";
import { MediaDnaTab } from "./tabs/MediaDnaTab";
import { ContextTab } from "./tabs/ContextTab";
import { PropagationTab } from "./tabs/PropagationTab";
import { EvidenceTab } from "./tabs/EvidenceTab";
import { AuditTab } from "./tabs/AuditTab";
import { AudioTab } from "./tabs/AudioTab";
import { CopilotTab } from "./tabs/CopilotTab";
import { OsintTab } from "./tabs/OsintTab";
import { CaseReviewTab } from "./tabs/CaseReviewTab";
import type { InvestigationIntent, ToastTone, UserRole, WorkspaceTabKey } from "../../types";
import { api } from "../../api";

export function Workspace({
  caseId,
  intent,
  role,
  onBack,
  onReport,
  notify,
  onCloseCase,
}: {
  caseId: string;
  intent: InvestigationIntent | null;
  role: UserRole;
  onBack: () => void;
  onReport: () => void;
  notify: (message: string, tone?: ToastTone) => void;
  onCloseCase: () => void | Promise<void>;
}) {
  const [tab, setTab] = useState<WorkspaceTabKey>("overview");
  const [data, setData] = useState<any>(null);

  const loadCase = () => api.case(caseId).then(setData).catch(() => setData(null));

  useEffect(() => {
    setTab("overview");
    loadCase();
  }, [caseId]);

  useEffect(() => {
    if (tab === "audio" && !data?.media?.mimeType?.startsWith("audio/")) setTab("overview");
  }, [tab, data]);

  const addEvidence = async (file: File) => {
    try {
      await api.upload(caseId, file);
      notify(`${file.name} added to the evidence register.`, "success");
      await api.analyze(caseId).catch(() => undefined);
      await loadCase();
    } catch (e: any) {
      notify(e.message || "Unable to add evidence", "warn");
    }
  };

  return (
    <div className="flex h-screen flex-1 flex-col overflow-hidden bg-[#071126]">
      <WorkspaceHeader
        caseId={caseId}
        onBack={onBack}
        onReport={onReport}
        onAddEvidence={addEvidence}
        notify={notify}
        onCloseCase={onCloseCase}
        status={data?.status || "Active"}
        canCloseCase={(role === "admin" || role === "case-officer") && data?.status !== "Closed"}
        canAddEvidence={role !== "case-officer"}
      />
      <TabBar active={tab} onChange={setTab} showAudio={Boolean(data?.media?.mimeType?.startsWith("audio/"))} showReview={role === "case-officer" || role === "admin"} />
      <div className="flex-1 overflow-y-auto">
        {tab === "overview" && <OverviewTab caseId={caseId} intent={intent} />}
        {tab === "authenticity" && <AuthenticityTab caseId={caseId} notify={notify} />}
        {tab === "dna" && <MediaDnaTab caseId={caseId} />}
        {tab === "context" && <ContextTab caseId={caseId} intent={intent} />}
        {tab === "propagation" && <PropagationTab caseId={caseId} />}
        {tab === "evidence" && <EvidenceTab caseId={caseId} />}
        {tab === "audio" && <AudioTab caseId={caseId} />}
        {tab === "copilot" && <CopilotTab caseId={caseId} />}
        {tab === "osint" && <OsintTab caseId={caseId} />}
        {tab === "review" && <CaseReviewTab caseId={caseId} />}
        {tab === "audit" && <AuditTab caseId={caseId} />}
      </div>
    </div>
  );
}
