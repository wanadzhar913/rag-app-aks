import type {
  AiInsightPayload,
  DocumentExtraction,
  DraftModel,
  OffenceOption,
  PrecedentSuggestion,
} from "../types";

export const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || "/api/v1";

export const offenceCatalog: OffenceOption[] = [
  {
    value: "section-41-1",
    title: "Section 41(1)",
    subtitle: "Reckless and dangerous driving causing death",
    precedentSeed: [
      {
        title: "PP v. Tan Boon (2021)",
        rationale:
          "Useful where visibility and road conditions affect the quality of the enforcement record.",
      },
      {
        title: "Public Prosecutor v. Ahmad",
        rationale:
          "Helpful where calibration and equipment integrity are central to the representation.",
      },
    ],
  },
  {
    value: "section-45a-1",
    title: "Section 45A(1)",
    subtitle: "Driving under the influence of alcohol or drugs",
    precedentSeed: [
      {
        title: "PP v. Siva Kumar",
        rationale: "Often cited on strict compliance with testing and sample handling procedures.",
      },
      {
        title: "R v. Ismail",
        rationale: "Useful when the chain of custody or timing of specimen collection is disputed.",
      },
    ],
  },
  {
    value: "administrative-penalty",
    title: "Administrative Penalty",
    subtitle: "Licensing and registration appeals",
    precedentSeed: [
      {
        title: "JPJ Appeals Board Circular 3/2022",
        rationale:
          "Relevant where renewal history and administrative fairness support a reduction or warning.",
      },
      {
        title: "Director General of Transport v. Lee",
        rationale: "Useful for proportionality arguments in non-criminal penalty review.",
      },
    ],
  },
];

export function getOffenceByValue(value: string): OffenceOption {
  return offenceCatalog.find((item) => item.value === value) ?? offenceCatalog[0];
}

export function buildDraftModel(input: {
  referenceNumber: string;
  incidentDate: string;
  incidentLocation: string;
  mitigatingCircumstances: string;
  offence: OffenceOption;
  extraction: DocumentExtraction | null;
}): DraftModel {
  const referenceNumber = input.referenceNumber.trim() || "UNSPECIFIED-REFERENCE";
  const incidentLocation = input.incidentLocation.trim() || "the relevant jurisdiction";
  const mitigatingCircumstances = input.mitigatingCircumstances.trim();
  const readableDate = formatLongDate(input.incidentDate);
  const internalReference = buildInternalReference(
    referenceNumber,
    incidentLocation,
    input.incidentDate,
  );
  const documentId = buildDocumentId(referenceNumber, input.incidentDate, input.extraction?.id);
  const extractionSummary = buildExtractionNarrative(input.extraction);

  return {
    referenceNumber,
    letterDate: formatLongDate(new Date().toISOString().slice(0, 10)),
    openingParagraph: `We act on behalf of the registered owner / driver and respectfully submit this representation concerning Notice ${referenceNumber}, issued in connection with an alleged ${input.offence.title} matter said to have occurred on ${readableDate} near ${incidentLocation}.`,
    contextParagraph: input.extraction
      ? `This draft has been grounded in backend evidence from "${input.extraction.document_name}"${
          input.extraction.page_number === null || input.extraction.page_number === undefined
            ? ""
            : `, page ${input.extraction.page_number}`
        }, together with the instructions entered into this drafting workspace.`
      : "This draft has been prepared from the citation details entered in the drafting workspace, pending attachment of backend source material.",
    closingParagraph:
      "In light of the foregoing, we respectfully request that the Department review the notice, take the supporting material into account, and consider withdrawal, reduction, or conversion of the penalty to an appropriate warning.",
    arguments: [
      {
        title: "Statutory framing",
        body: `The representation should be considered as a plea for discretionary review under Section 120 of the Road Transport Act 1987, with particular regard to the procedural and evidentiary context of ${input.offence.subtitle.toLowerCase()}.`,
      },
      {
        title: "Factual matrix",
        body:
          mitigatingCircumstances ||
          "The available instructions indicate that the surrounding circumstances materially reduce culpability and justify a measured administrative response instead of strict enforcement.",
      },
      {
        title: "Supporting material",
        body: extractionSummary,
      },
    ],
    internalReference,
    documentId,
  };
}

export function buildFallbackInsight(input: {
  backendReady: boolean;
  selectedDocumentName: string;
  extraction: DocumentExtraction | null;
  mitigatingCircumstances: string;
  incidentLocation: string;
  incidentDate: string;
  offence: OffenceOption;
  sessionId: string;
  apiBaseUrl: string;
}): {
  strengthText: string;
  recommendation: string;
  precedents: PrecedentSuggestion[];
  backendNotes: string;
} {
  let score = 46;

  if (input.backendReady) score += 8;
  if (input.selectedDocumentName) score += 8;
  if (input.extraction?.raw_text) score += 8;
  if (Object.keys(input.extraction?.metadata ?? {}).length) score += 8;
  if (input.mitigatingCircumstances.trim().length > 80) score += 12;
  if (input.incidentLocation.trim()) score += 4;
  if (input.incidentDate) score += 4;

  score = Math.max(32, Math.min(88, score));

  const strengthText = input.extraction
    ? `Fallback strength estimate: ${score}%. The appeal is better grounded because backend extraction #${input.extraction.id} is available and can be cited alongside the manually entered mitigation.`
    : `Fallback strength estimate: ${score}%. Attach an ingested backend document to move this from a purely manual draft to an evidence-backed representation.`;

  const recommendation = input.extraction
    ? Object.keys(input.extraction.metadata ?? {}).length
      ? "Use the extraction metadata and the cited page text as annexures, then ask Counsel AI for a more formal authority-based refinement."
      : "Pair the selected extraction with a maintenance log, timeline, or calibration record so the representation carries both narrative and documentary support."
    : "Upload or select a backend PDF first. The drafting flow becomes much stronger once the appeal is anchored to extracted text or metadata.";

  const backendNotes = [
    `API base: ${input.apiBaseUrl}`,
    `Backend reachable: ${input.backendReady ? "yes" : "no"}`,
    `Document selected: ${input.selectedDocumentName || "none"}`,
    `Extraction selected: ${input.extraction ? `#${input.extraction.id}` : "none"}`,
    `Session id: ${input.sessionId || "not created yet"}`,
  ].join("\n");

  return {
    strengthText,
    recommendation,
    precedents: input.offence.precedentSeed,
    backendNotes,
  };
}

export function buildAiPrompt(input: {
  model: DraftModel;
  offence: OffenceOption;
  incidentDate: string;
  incidentLocation: string;
  mitigatingCircumstances: string;
  selectedDocumentName: string;
  extraction: DocumentExtraction | null;
}): string {
  return [
    "Analyze the following Malaysian road transport appeal draft context.",
    "Return JSON only with this exact shape:",
    JSON.stringify(
      {
        strength_summary: "string",
        success_probability: 0,
        precedents: [{ title: "string", rationale: "string" }],
        recommendation: "string",
        notes: "string",
      },
      null,
      2,
    ),
    "",
    `Reference number: ${input.model.referenceNumber}`,
    `Offence: ${input.offence.title} - ${input.offence.subtitle}`,
    `Incident date: ${input.incidentDate || "not provided"}`,
    `Location: ${input.incidentLocation.trim() || "not provided"}`,
    `Mitigating circumstances: ${input.mitigatingCircumstances.trim() || "not provided"}`,
    `Backend document: ${input.selectedDocumentName || "not selected"}`,
    `Backend extraction id: ${input.extraction?.id || "not selected"}`,
    `Extraction metadata: ${JSON.stringify(input.extraction?.metadata || {})}`,
    `Extraction text: ${buildSnippet(input.extraction?.raw_text, 1800)}`,
  ].join("\n");
}

export function parseAiInsightPayload(value: string): AiInsightPayload | null {
  if (!value) {
    return null;
  }

  const fencedMatch = value.match(/```json\s*([\s\S]*?)```/i);
  const candidate = fencedMatch ? fencedMatch[1] : value;

  try {
    return JSON.parse(candidate) as AiInsightPayload;
  } catch {
    const objectMatch = candidate.match(/\{[\s\S]*\}/);
    if (!objectMatch) {
      return null;
    }

    try {
      return JSON.parse(objectMatch[0]) as AiInsightPayload;
    } catch {
      return null;
    }
  }
}

export function formatLongDate(value: string): string {
  if (!value) {
    return "the relevant date";
  }

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-MY", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

export function buildSnippet(value?: string | null, maxLength = 200): string {
  const normalized = (value || "").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return "No extracted text snippet is available yet.";
  }

  return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1)}...` : normalized;
}

export function getTopSentences(value?: string | null, count = 2): string[] {
  const normalized = (value || "").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return ["The selected extraction does not yet contain readable text."];
  }

  const sentences = normalized
    .split(/(?<=[.?!])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);

  return sentences.slice(0, count).length
    ? sentences.slice(0, count)
    : [buildSnippet(normalized, 200)];
}

export function humanizeKey(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "appeal-draft";
}

export function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function buildExtractionNarrative(extraction: DocumentExtraction | null): string {
  if (!extraction) {
    return "No backend extraction has been attached yet. The appeal can be strengthened by selecting an ingested document and citing any factual findings, maintenance records, or timeline details surfaced there.";
  }

  const sentences = getTopSentences(extraction.raw_text, 2);
  const metadataEntries = Object.entries(extraction.metadata || {});
  const metadataSummary = metadataEntries.length
    ? `Structured metadata notes ${metadataEntries
        .slice(0, 3)
        .map(([key, value]) => `${humanizeKey(key)} ${String(value)}`)
        .join(", ")}.`
    : "The extraction contains primarily unstructured text rather than tagged metadata.";

  return `${sentences.join(" ")} ${metadataSummary}`.trim();
}

function buildInternalReference(
  referenceNumber: string,
  location: string,
  incidentDate: string,
): string {
  const year = (incidentDate || new Date().toISOString().slice(0, 10)).slice(0, 4);
  const locationCode =
    location
      .toUpperCase()
      .replace(/[^A-Z0-9 ]/g, "")
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 3) || "MY";
  const tail = referenceNumber.replace(/[^A-Z0-9]/gi, "").slice(-4).toUpperCase() || "0001";

  return `GC/RT/${year}/${locationCode}-${tail}`;
}

function buildDocumentId(
  referenceNumber: string,
  incidentDate: string,
  extractionId?: number | null,
): string {
  const seed = `${referenceNumber}|${incidentDate || "undated"}|${extractionId || "manual"}`;
  let hash = 0;

  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  }

  return `GC-AUTO-APP-${String(hash).padStart(10, "0").slice(0, 10)}`;
}
