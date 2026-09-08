import React from "react";
import { Settings } from "lucide-react";
import { Panel } from "../ui/Primitives";
import { SimplePage } from "./SimplePage";

export function SettingsPage() {
  return (
    <SimplePage title="Settings" subtitle="Platform preferences and integrations." icon={Settings}>
      <Panel className="p-5 text-[13px] text-slate-500">
        Configuration options for detection sensitivity, retention policy, and connector APIs will appear here.
      </Panel>
    </SimplePage>
  );
}
