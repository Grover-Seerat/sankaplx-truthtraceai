import type { CaseData } from "../types";

function clean(value: unknown): string {
  return String(value ?? "N/A")
    .replace(/[^\x20-\x7E]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function escapePdf(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function wrap(text: string, width = 92): string[] {
  const words = clean(text).split(" ");
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    if (!word) continue;
    if ((line + " " + word).trim().length > width && line) {
      lines.push(line);
      line = word;
    } else {
      line = (line + " " + word).trim();
    }
  }
  if (line) lines.push(line);
  return lines.length ? lines : [""];
}

function makePdf(pageLines: string[][]): Blob {
  const bodies: string[] = [];
  const pageNumbers: number[] = [];
  const contentNumbers: number[] = [];

  bodies.push("<< /Type /Catalog /Pages 2 0 R >>");
  bodies.push(""); // pages object filled after page count is known
  bodies.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");

  pageLines.forEach((lines, index) => {
    const pageObject = 4 + index * 2;
    const contentObject = pageObject + 1;
    pageNumbers.push(pageObject);
    contentNumbers.push(contentObject);

    const commands = [
      "BT",
      "/F1 9 Tf",
      "40 760 Td",
      "11 TL",
      ...lines.map((line) => `(${escapePdf(line)}) Tj T*`),
      "ET",
    ].join("\n");

    bodies.push(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${contentObject} 0 R >>`
    );
    bodies.push(`<< /Length ${commands.length} >>\nstream\n${commands}\nendstream`);
  });

  bodies[1] = `<< /Type /Pages /Kids [${pageNumbers.map((n) => `${n} 0 R`).join(" ")}] /Count ${pageNumbers.length} >>`;

  const chunks: string[] = ["%PDF-1.4\n%\xFF\xFF\xFF\xFF\n"];
  const offsets: number[] = [0];
  let position = chunks[0].length;

  bodies.forEach((body, index) => {
    offsets.push(position);
    const chunk = `${index + 1} 0 obj\n${body}\nendobj\n`;
    chunks.push(chunk);
    position += chunk.length;
  });

  const xrefOffset = position;
  chunks.push(`xref\n0 ${bodies.length + 1}\n`);
  chunks.push("0000000000 65535 f \n");
  for (let i = 1; i <= bodies.length; i++) {
    chunks.push(`${String(offsets[i]).padStart(10, "0")} 00000 n \n`);
  }
  chunks.push(`trailer\n<< /Size ${bodies.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`);

  return new Blob(chunks, { type: "application/pdf" });
}

export function buildForensicReportPdf(data: CaseData): Blob {
  const lines: string[] = [];
  const add = (heading: string, value?: unknown) => {
    lines.push(heading.toUpperCase());
    if (value !== undefined) wrap(String(value)).forEach((line) => lines.push(`  ${line}`));
    lines.push("");
  };
  const addField = (label: string, value: unknown) => {
    wrap(`${label}: ${clean(value)}`).forEach((line) => lines.push(line));
  };

  lines.push("TRUTHTRACE AI — FORENSIC CASE REPORT", `CASE ID: ${clean(data.id)}`, `GENERATED: ${new Date().toISOString()}`, "");
  addField("Investigation type", data.investigationType);
  addField("Claim", data.intent.claim);
  addField("Platform", data.intent.platform);
  addField("Claim date", data.intent.date);
  addField("Known location", data.intent.location);
  addField("Media submitted", data.intent.withMedia ? "Yes" : "No");
  lines.push("");

  add("MEDIA EVIDENCE");
  if (data.referenceUrl) addField("Reference URL", data.referenceUrl);
  if (data.media) {
    addField("File name", data.media.fileName);
    addField("File type", data.media.fileType);
    addField("File size", data.media.fileSize);
    addField("MIME type", data.media.mimeType);
    addField("SHA-256", data.media.sha256);
    addField("Dimensions", data.media.width && data.media.height ? `${data.media.width} x ${data.media.height}` : "N/A");
    addField("Duration", data.media.duration);
    addField("Source", data.media.source);
    addField("Added at", data.media.addedAt);
  } else {
    lines.push("No media file was submitted.");
  }
  lines.push("");

  add("AUTHENTICITY ASSESSMENT");
  addField("Verdict", data.authenticity.verdict);
  addField("Confidence", `${data.authenticity.confidence}%`);
  wrap(data.authenticity.summary).forEach((line) => lines.push(line));
  lines.push("");

  add("OVERVIEW");
  addField("Authenticity", `${data.overview.authenticity.value} — ${data.overview.authenticity.sub}`);
  addField("Media DNA", `${data.overview.mediaDna.value} — ${data.overview.mediaDna.sub}`);
  addField("Context", data.overview.context.value);
  addField("Propagation", data.overview.propagation.value);
  wrap(data.overview.assessment).forEach((line) => lines.push(line));
  data.overview.why.forEach((item, i) => wrap(`${i + 1}. ${item}`).forEach((line) => lines.push(line)));
  lines.push("");

  add("MEDIA DNA / FORENSIC FINGERPRINT");
  addField("Media DNA ID", data.dnaId);
  Object.entries(data.fingerprint).forEach(([key, value]) => addField(key, value));
  if (data.similarMedia.length) {
    lines.push("RELATED MEDIA");
    data.similarMedia.forEach((m) => addField(`${m.case} (${m.match}% match)`, `${m.platform} | ${m.date} | ${m.transform}`));
  } else {
    lines.push("RELATED MEDIA: No match identified.");
  }
  lines.push("");

  add("CONTEXT INTEGRITY");
  addField("Media authenticity", data.context.mediaAuthenticity);
  addField("Context consistency", data.context.contextConsistency);
  addField("Claim", data.context.claim);
  wrap(data.context.assessment).forEach((line) => lines.push(line));
  data.context.evidenceRows.forEach((row) => addField(row.label, `${row.value} [${row.tone}]`));
  lines.push("");

  add("PROPAGATION TIMELINE");
  if (data.propagationNodes.length) {
    const timeline = [...data.propagationNodes].sort(
      (a, b) => new Date(a.observedAt ?? a.ts).getTime() - new Date(b.observedAt ?? b.ts).getTime()
    );
    timeline.forEach((node, i) => {
      addField(`${i + 1}. ${node.label}`, `Observed: ${node.observedAt ?? node.ts}`);
      addField("  Activity", node.activity ?? "Media observed");
      addField("  Platform", node.platform);
      addField("  Account / Ref", node.account);
      addField("  Route", `${node.from ?? "Unknown source"} -> ${node.to ?? node.platform}`);
      addField("  Similarity", node.similarity);
      addField("  Transformation", node.transform);
      addField("  Spread", node.spread);
      addField("  Status", node.tag);
      if (node.sourceUrl) addField("  Source URL", node.sourceUrl);
      lines.push("");
    });
  } else {
    lines.push("No propagation observations identified.");
  }
  lines.push("INVESTIGATION LEADS");
  data.propagationLeads.forEach((lead, i) => wrap(`${i + 1}. ${lead}`).forEach((line) => lines.push(line)));
  lines.push("");

  add("EVIDENCE REGISTER");
  if (data.evidence.length) {
    data.evidence.forEach((ev) => {
      addField(ev.id, `Case ${ev.caseId} | ${ev.type} | DNA ${ev.dna} | Hash ${ev.hash} | Analysis ${ev.analysis} | Added ${ev.added}`);
    });
  } else {
    lines.push("No evidence items registered.");
  }
  lines.push("");

  add("AUDIT TRAIL");
  data.audit.forEach((entry) => addField(entry.t, entry.e));
  lines.push("");
  add("NEXT ACTIONS");
  data.overview.nextActions.forEach((item, i) => wrap(`${i + 1}. ${item}`).forEach((line) => lines.push(line)));
  lines.push("");
  add("INVESTIGATOR NOTES", data.notes ?? "No investigator notes recorded.");
  lines.push("DISCLAIMER: AI-assisted findings are provided for investigator review and are not a certified forensic or legal determination.");

  const pages: string[][] = [];
  const pageSize = 55;
  for (let i = 0; i < lines.length; i += pageSize) {
    pages.push(lines.slice(i, i + pageSize));
  }
  return makePdf(pages);
}

export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
