import React from "react";
import { Database } from "lucide-react";
import { EvidenceTab } from "../workspace/tabs/EvidenceTab";
import { SimplePage } from "./SimplePage";

export function EvidenceVaultPage() {
  return (
    <SimplePage
      title="Evidence Vault"
      subtitle="All evidence collected across every investigation."
      icon={Database}
    >
      <EvidenceTab />
    </SimplePage>
  );
}
