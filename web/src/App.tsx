import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  buildAiPrompt,
  buildDraftModel,
  buildFallbackInsight,
  buildSnippet,
  DEFAULT_API_BASE_URL,
  getOffenceByValue,
  humanizeKey,
  offenceCatalog,
  parseAiInsightPayload,
  slugify,
  wait,
} from "./lib/drafting";
import type {
  AiInsightPayload,
  ChatResponse,
  DocumentExtraction,
  DocumentSummary,
  ExtractionResponse,
  IngestionJobResponse,
  IngestionUploadResponse,
  Message,
  OffenceOption,
  PrecedentSuggestion,
  SessionResponse,
} from "./types";

type StatusState = "loading" | "ready" | "error";
type AppPage = "docket" | "archive" | "counsel-ai" | "drafting-suite" | "settings";

type HealthResponse = {
  status: string;
  postgres?: boolean;
};

type NavItem = {
  page: AppPage;
  label: string;
  icon: string;
  title: string;
  subtitle: string;
};

const navItems: NavItem[] = [
  {
    page: "docket",
    label: "The Docket",
    icon: "gavel",
    title: "The Docket",
    subtitle: "MATTER MANAGEMENT",
  },
  {
    page: "archive",
    label: "The Archive",
    icon: "folder_managed",
    title: "The Archive",
    subtitle: "SOURCE MATERIALS",
  },
  {
    page: "counsel-ai",
    label: "Counsel AI",
    icon: "smart_toy",
    title: "Counsel AI",
    subtitle: "SESSION-BASED LEGAL ASSISTANCE",
  },
  {
    page: "drafting-suite",
    label: "Drafting Suite",
    icon: "edit_note",
    title: "Appeal Generator",
    subtitle: "ROAD TRANSPORT ACT 1987 - SECTION 120",
  },
  {
    page: "settings",
    label: "Settings",
    icon: "settings",
    title: "Settings",
    subtitle: "WORKSPACE PREFERENCES",
  },
];

function App() {
  const [activePage, setActivePage] = useState<AppPage>("drafting-suite");
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [statusState, setStatusState] = useState<StatusState>("loading");
  const [statusMessage, setStatusMessage] = useState("Preparing your workspace...");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [extractions, setExtractions] = useState<DocumentExtraction[]>([]);
  const [selectedDocumentName, setSelectedDocumentName] = useState("");
  const [selectedExtractionId, setSelectedExtractionId] = useState("");
  const [uploadStatus, setUploadStatus] = useState(
    "Upload a PDF to add supporting material to your workspace.",
  );
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [matterNameDraft, setMatterNameDraft] = useState("");
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatStatus, setChatStatus] = useState("Choose a matter to start a conversation.");
  const [showThinkingSummary, setShowThinkingSummary] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [offenceReference, setOffenceReference] = useState("POL-JPJ/2023/88921-X");
  const [incidentDate, setIncidentDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [incidentLocation, setIncidentLocation] = useState("Kuala Lumpur");
  const [mitigatingCircumstances, setMitigatingCircumstances] = useState("");
  const [selectedOffenceValue, setSelectedOffenceValue] = useState(offenceCatalog[0].value);
  const [strengthAnalysis, setStrengthAnalysis] = useState(
    "Waiting for source materials before scoring this appeal.",
  );
  const [recommendation, setRecommendation] = useState(
    "Select a source document or add mitigation details to improve the draft.",
  );
  const [precedents, setPrecedents] = useState<PrecedentSuggestion[]>([
    {
      title: "Awaiting analysis",
      rationale: "Choose a source material and generate the preview to request tailored suggestions.",
    },
  ]);
  const [insightSummary, setInsightSummary] = useState(
    "No source summary yet. Choose a document extraction to ground the appeal.",
  );

  useEffect(() => {
    const storedApiBaseUrl = window.localStorage.getItem("lawyer-jalan.api-base-url");
    if (storedApiBaseUrl) {
      setApiBaseUrl(storedApiBaseUrl);
    }

    const syncPageFromHash = () => {
      const hash = window.location.hash.replace(/^#/, "") as AppPage;
      if (navItems.some((item) => item.page === hash)) {
        setActivePage(hash);
      } else {
        window.location.hash = "#drafting-suite";
      }
    };

    syncPageFromHash();
    window.addEventListener("hashchange", syncPageFromHash);
    return () => window.removeEventListener("hashchange", syncPageFromHash);
  }, []);

  useEffect(() => {
    window.localStorage.setItem("lawyer-jalan.api-base-url", apiBaseUrl);
    void refreshWorkspace(apiBaseUrl);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBaseUrl]);

  const selectedOffence: OffenceOption = useMemo(
    () => getOffenceByValue(selectedOffenceValue),
    [selectedOffenceValue],
  );

  const selectedExtraction = useMemo(
    () => extractions.find((item) => String(item.id) === String(selectedExtractionId)) ?? null,
    [extractions, selectedExtractionId],
  );

  const selectedDocument = useMemo(
    () => documents.find((item) => item.document_name === selectedDocumentName) ?? null,
    [documents, selectedDocumentName],
  );

  const draftModel = useMemo(
    () =>
      buildDraftModel({
        referenceNumber: offenceReference,
        incidentDate,
        incidentLocation,
        mitigatingCircumstances,
        offence: selectedOffence,
        extraction: selectedExtraction,
      }),
    [
      incidentDate,
      incidentLocation,
      mitigatingCircumstances,
      offenceReference,
      selectedExtraction,
      selectedOffence,
    ],
  );

  useEffect(() => {
    const fallback = buildFallbackInsight({
      backendReady: statusState === "ready",
      selectedDocumentName,
      extraction: selectedExtraction,
      mitigatingCircumstances,
      incidentLocation,
      incidentDate,
      offence: selectedOffence,
      sessionId: selectedSessionId,
      apiBaseUrl,
    });

    setStrengthAnalysis(fallback.strengthText);
    setRecommendation(fallback.recommendation);
    setPrecedents(fallback.precedents);

    if (selectedExtraction) {
      const details = Object.entries(selectedExtraction.metadata || {})
        .slice(0, 4)
        .map(([key, value]) => `${humanizeKey(key)}: ${String(value)}`)
        .join(" | ");
      setInsightSummary(
        `${selectedExtraction.document_name}${
          selectedExtraction.page_number === null || selectedExtraction.page_number === undefined
            ? ""
            : `, page ${selectedExtraction.page_number}`
        }${details ? ` | ${details}` : ""}`,
      );
    } else {
      setInsightSummary("No source summary yet. Choose a document extraction to ground the appeal.");
    }
  }, [
    apiBaseUrl,
    incidentDate,
    incidentLocation,
    mitigatingCircumstances,
    selectedDocumentName,
    selectedExtraction,
    selectedOffence,
    selectedSessionId,
    statusState,
  ]);

  async function refreshWorkspace(nextApiBaseUrl: string) {
    setStatusState("loading");
    setStatusMessage("Syncing your workspace...");

    const [healthResult, documentResult, sessionResult] = await Promise.allSettled([
      fetchJson<HealthResponse>(`${nextApiBaseUrl}/health`),
      fetchJson<DocumentSummary[]>(`${nextApiBaseUrl}/documents`),
      fetchJson<SessionResponse[]>(`${nextApiBaseUrl}/sessions`),
    ]);

    if (healthResult.status === "fulfilled") {
      setHealth(healthResult.value);
      setStatusState("ready");
    } else {
      console.error(healthResult.reason);
      setHealth(null);
      setDocuments([]);
      setExtractions([]);
      setSessions([]);
      setChatMessages([]);
      setSelectedDocumentName("");
      setSelectedExtractionId("");
      setSelectedSessionId("");
      setStatusState("error");
      setStatusMessage("Workspace unavailable right now. Please refresh in a moment.");
      return;
    }

    if (documentResult.status === "fulfilled") {
      const nextDocuments = documentResult.value;
      setDocuments(nextDocuments);
      const nextDocumentName =
        nextDocuments.find((item) => item.document_name === selectedDocumentName)?.document_name ??
        nextDocuments[0]?.document_name ??
        "";
      setSelectedDocumentName(nextDocumentName);

      if (nextDocumentName) {
        await loadExtractions(nextApiBaseUrl, nextDocumentName, selectedExtractionId);
      } else {
        setExtractions([]);
        setSelectedExtractionId("");
      }
    } else {
      console.error(documentResult.reason);
      setDocuments([]);
      setExtractions([]);
      setSelectedDocumentName("");
      setSelectedExtractionId("");
    }

    if (sessionResult.status === "fulfilled") {
      const nextSessions = sessionResult.value;
      setSessions(nextSessions);
      const nextSessionId =
        nextSessions.find((item) => item.session_id === selectedSessionId)?.session_id ??
        nextSessions[0]?.session_id ??
        "";
      setSelectedSessionId(nextSessionId);

      if (nextSessionId) {
        await loadChatHistory(nextApiBaseUrl, nextSessionId);
      } else {
        setChatMessages([]);
        setChatStatus("Choose a matter to start a conversation.");
      }
    } else {
      console.error(sessionResult.reason);
      setSessions([]);
      setSelectedSessionId("");
      setChatMessages([]);
      setChatStatus("Matter list unavailable right now.");
    }

    const documentCount = documentResult.status === "fulfilled" ? documentResult.value.length : 0;
    const matterCount = sessionResult.status === "fulfilled" ? sessionResult.value.length : 0;
    setStatusMessage(
      `Workspace ready. ${documentCount} document(s) and ${matterCount} matter(s) available.`,
    );
  }

  async function loadExtractions(
    nextApiBaseUrl: string,
    documentName: string,
    preferredExtractionId = "",
  ) {
    const url = new URL(`${nextApiBaseUrl}/documents/extractions`, window.location.origin);
    url.searchParams.set("document_name", documentName);
    url.searchParams.set("limit", "100");
    url.searchParams.set("offset", "0");

    const response = await fetchJson<ExtractionResponse>(url.toString());
    const nextExtractions = response.items ?? [];
    setExtractions(nextExtractions);
    const nextSelectedExtractionId =
      nextExtractions.find((item) => String(item.id) === String(preferredExtractionId))?.id ??
      nextExtractions[0]?.id ??
      "";
    setSelectedExtractionId(String(nextSelectedExtractionId));
  }

  async function loadChatHistory(nextApiBaseUrl: string, sessionId: string) {
    try {
      const history = await fetchJson<Message[]>(`${nextApiBaseUrl}/sessions/${sessionId}/history`);
      setChatMessages(history);
      setChatStatus(
        history.length
          ? "Conversation history loaded."
          : "This matter has no messages yet. Ask Counsel AI your first question.",
      );
    } catch (error) {
      console.error(error);
      setChatMessages([]);
      setChatStatus("Latest conversation could not be loaded.");
    }
  }

  async function handleRefresh() {
    await refreshWorkspace(apiBaseUrl);
  }

  async function handleDocumentChange(event: ChangeEvent<HTMLSelectElement>) {
    const nextDocumentName = event.target.value;
    setSelectedDocumentName(nextDocumentName);

    if (!nextDocumentName) {
      setExtractions([]);
      setSelectedExtractionId("");
      return;
    }

    try {
      await loadExtractions(apiBaseUrl, nextDocumentName);
    } catch (error) {
      console.error(error);
      setExtractions([]);
      setSelectedExtractionId("");
      setInsightSummary("Source material could not be loaded.");
    }
  }

  async function handleSessionChange(sessionId: string) {
    setSelectedSessionId(sessionId);
    if (!sessionId) {
      setChatMessages([]);
      setChatStatus("Choose a matter to start a conversation.");
      return;
    }
    await loadChatHistory(apiBaseUrl, sessionId);
  }

  async function handleCreateMatter(event?: FormEvent) {
    event?.preventDefault();
    const name = matterNameDraft.trim() || `Matter ${new Date().toLocaleString("en-MY")}`;

    try {
      const session = await fetchJson<SessionResponse>(`${apiBaseUrl}/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name }),
      });
      const nextSessions = [session, ...sessions];
      setSessions(nextSessions);
      setSelectedSessionId(session.session_id);
      setChatMessages([]);
      setChatStatus("New matter created. Ask Counsel AI your first question.");
      setMatterNameDraft("");
    } catch (error) {
      console.error(error);
      setChatStatus("A new matter could not be created right now.");
    }
  }

  async function handleDeleteMatter(sessionId: string) {
    try {
      await fetchNoContent(`${apiBaseUrl}/sessions/${sessionId}`, { method: "DELETE" });
      const nextSessions = sessions.filter((item) => item.session_id !== sessionId);
      setSessions(nextSessions);

      if (selectedSessionId === sessionId) {
        const nextSelectedSessionId = nextSessions[0]?.session_id ?? "";
        setSelectedSessionId(nextSelectedSessionId);
        if (nextSelectedSessionId) {
          await loadChatHistory(apiBaseUrl, nextSelectedSessionId);
        } else {
          setChatMessages([]);
          setChatStatus("Choose a matter to start a conversation.");
        }
      }
    } catch (error) {
      console.error(error);
      setChatStatus("That matter could not be removed.");
    }
  }

  async function handlePdfSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setUploadStatus(`Uploading ${file.name}...`);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const upload = await fetchJson<IngestionUploadResponse>(`${apiBaseUrl}/documents/upload`, {
        method: "POST",
        body: formData,
      });
      setUploadStatus(`Upload accepted for ${upload.filename}. Processing now...`);
      await pollIngestionJob(upload.job_id, upload.filename);
      event.target.value = "";
    } catch (error) {
      console.error(error);
      setUploadStatus("Upload failed. Please try again.");
    }
  }

  async function pollIngestionJob(jobId: string, filename: string) {
    for (let attempt = 0; attempt < 10; attempt += 1) {
      await wait(2500);

      try {
        const job = await fetchJson<IngestionJobResponse>(`${apiBaseUrl}/documents/jobs/${jobId}`);
        setUploadStatus(`${filename}: ${job.status}`);

        if (job.status === "completed" || job.status === "failed") {
          if (job.status === "completed") {
            setUploadStatus(`${filename} is ready and has been added to the archive.`);
          }
          await refreshWorkspace(apiBaseUrl);
          return;
        }
      } catch (error) {
        console.error(error);
        setUploadStatus("Upload accepted, but live progress could not be checked.");
        return;
      }
    }

    setUploadStatus("The upload is still processing. Refresh again in a moment.");
  }

  async function ensureSelectedMatter(): Promise<string> {
    if (selectedSessionId) {
      return selectedSessionId;
    }

    const name = matterNameDraft.trim() || `Matter ${new Date().toLocaleString("en-MY")}`;
    const session = await fetchJson<SessionResponse>(`${apiBaseUrl}/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name }),
    });

    setSessions((current) => [session, ...current]);
    setSelectedSessionId(session.session_id);
    setMatterNameDraft("");
    return session.session_id;
  }

  async function handleSendChat(event: FormEvent) {
    event.preventDefault();
    const messageText = chatInput.trim();
    if (!messageText) {
      return;
    }

    try {
      const sessionId = await ensureSelectedMatter();
      setIsThinking(true);
      setChatStatus("Counsel AI is reviewing the latest question...");

      const userMessage: Message = { role: "user", content: messageText };
      const requestMessages: Message[] = [];

      if (showThinkingSummary) {
        requestMessages.push({
          role: "system",
          content:
            'If useful, respond with two sections titled exactly "Thinking steps" and "Final answer". Keep the thinking steps high-level and concise.',
        });
      }

      requestMessages.push(userMessage);

      const response = await fetchJson<ChatResponse>(`${apiBaseUrl}/sessions/${sessionId}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ messages: requestMessages }),
      });

      const assistantMessages = response.messages.filter((message) => message.role === "assistant");
      setChatMessages((current) => [...current, userMessage, ...assistantMessages]);
      setChatInput("");
      setChatStatus("Latest answer received.");
    } catch (error) {
      console.error(error);
      setChatStatus("The message could not be sent right now.");
    } finally {
      setIsThinking(false);
    }
  }

  async function handleAnalyzeDraft() {
    if (statusState !== "ready") {
      return;
    }

    try {
      const sessionId = await ensureSelectedMatter();
      const response = await fetchJson<ChatResponse>(`${apiBaseUrl}/sessions/${sessionId}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [
            {
              role: "system",
              content:
                "You are a Malaysian road transport law drafting assistant. Return concise litigation-oriented output only.",
            },
            {
              role: "user",
              content: buildAiPrompt({
                model: draftModel,
                offence: selectedOffence,
                incidentDate,
                incidentLocation,
                mitigatingCircumstances,
                selectedDocumentName,
                extraction: selectedExtraction,
              }),
            },
          ],
        }),
      });

      const assistantMessage =
        response.messages.filter((message) => message.role === "assistant").at(-1)?.content ?? "";
      const payload = parseAiInsightPayload(assistantMessage);
      if (payload) {
        applyAiPayload(payload);
      }
    } catch (error) {
      console.error(error);
    }
  }

  function applyAiPayload(payload: AiInsightPayload) {
    const probability = Number(payload.success_probability);
    setStrengthAnalysis(
      Number.isFinite(probability)
        ? `${payload.strength_summary ?? "Analysis complete."} Estimated success probability: ${Math.max(0, Math.min(100, Math.round(probability)))}%.`
        : payload.strength_summary ?? "Analysis returned without a probability score.",
    );
    setRecommendation(payload.recommendation || recommendation);
    setPrecedents(
      Array.isArray(payload.precedents) && payload.precedents.length
        ? payload.precedents.map((item) => ({
            title: item.title || "Untitled authority",
            rationale: item.rationale || "No rationale provided.",
          }))
        : precedents,
    );
    if (payload.notes) {
      setInsightSummary(payload.notes);
    }
  }

  function handleExportDoc() {
    const documentMarkup = document.getElementById("printable-preview")?.outerHTML;
    if (!documentMarkup) {
      return;
    }

    const html = `
      <html xmlns:o="urn:schemas-microsoft-com:office:office"
            xmlns:w="urn:schemas-microsoft-com:office:word"
            xmlns="http://www.w3.org/TR/REC-html40">
        <head><meta charset="utf-8"></head>
        <body>${documentMarkup}</body>
      </html>
    `;

    const blob = new Blob(["\ufeff", html], { type: "application/msword" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${slugify(offenceReference.trim() || "appeal-draft")}.doc`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }

  const currentNav = navItems.find((item) => item.page === activePage) ?? navItems[3];

  return (
    <div className="flex min-h-screen bg-[var(--surface)] text-[var(--text)]">
      <aside className="hidden h-screen w-64 shrink-0 border-r border-[var(--border)] bg-[var(--surface)] xl:fixed xl:inset-y-0 xl:left-0 xl:flex xl:flex-col">
        <div className="px-6 py-6">
          <h1 className="text-2xl font-black tracking-tight text-[var(--primary)]">Lawyer Jalan</h1>
          <p className="mt-2 text-[11px] font-bold uppercase tracking-[0.2em] text-[color:rgba(0,11,29,0.56)]">
            Modern Chambers v2.1
          </p>
        </div>

        <nav className="grid gap-1 px-2">
          {navItems
            .filter((item) => item.page !== "settings")
            .map((item) => (
              <NavButton
                key={item.page}
                item={item}
                active={activePage === item.page}
                onClick={() => {
                  window.location.hash = `#${item.page}`;
                  setActivePage(item.page);
                }}
              />
            ))}
        </nav>

        <div className="mt-auto px-2 pb-6">
          <NavButton
            item={navItems[4]}
            active={activePage === "settings"}
            onClick={() => {
              window.location.hash = "#settings";
              setActivePage("settings");
            }}
          />

          <div className="mx-2 mt-4 flex items-center gap-3 rounded-2xl bg-[var(--primary-container)] p-4 text-[var(--primary-soft)]">
            <div className="grid h-10 w-10 place-items-center rounded-full border border-white/15 bg-white/15 text-xs font-black">
              MZ
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.16em]">M. Zulkafli</p>
              <p className="mt-1 text-[11px] text-white/70">Senior Counsel</p>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex min-h-screen w-full flex-col xl:ml-64">
        <header className="flex flex-col gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-6 py-5 lg:flex-row lg:items-center lg:justify-between lg:px-12">
          <div className="flex items-center gap-4">
            <div className="h-8 w-1 bg-[var(--secondary-container)]" />
            <div>
              <h2 className="text-2xl font-extrabold tracking-tight text-[var(--primary)]">
                {currentNav.title}
              </h2>
              <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--text-muted)]">
                {currentNav.subtitle}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {activePage === "drafting-suite" ? (
              <>
                <div className="flex items-center gap-1 rounded-xl bg-[var(--surface-container)] p-1">
                  <ToolbarButton icon="picture_as_pdf" title="Print / PDF" onClick={() => window.print()} />
                  <ToolbarButton icon="description" title="Export DOC" onClick={handleExportDoc} />
                  <ToolbarButton icon="print" title="Print" onClick={() => window.print()} />
                </div>
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="rounded-xl bg-[var(--secondary-container)] px-5 py-3 text-[11px] font-extrabold uppercase tracking-[0.14em] text-[var(--primary)] shadow-[var(--shadow-sm)] transition hover:scale-[0.99]"
                >
                  Finalize Appeal
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => void handleRefresh()}
                className="rounded-xl bg-[var(--secondary-container)] px-5 py-3 text-[11px] font-extrabold uppercase tracking-[0.14em] text-[var(--primary)] shadow-[var(--shadow-sm)] transition hover:scale-[0.99]"
              >
                Refresh Data
              </button>
            )}
          </div>
        </header>

        {activePage === "counsel-ai" ? (
          <section className="grid min-h-[calc(100vh-88px)] grid-cols-1 gap-6 bg-[var(--surface-container-low)] p-6 xl:h-[calc(100vh-88px)] xl:grid-cols-[minmax(0,1fr)_340px] xl:overflow-hidden xl:p-10">
            <div className="flex min-h-[72vh] min-w-0 flex-col rounded-3xl border border-[var(--border)] bg-white shadow-sm xl:h-full">
              <div className="border-b border-[var(--border)] px-6 py-5">
                <StatusPill statusState={statusState} statusMessage={statusMessage} />
                <h3 className="mt-4 text-xl font-extrabold text-[var(--primary)]">
                  {sessions.find((item) => item.session_id === selectedSessionId)?.name || "Counsel AI"}
                </h3>
                <p className="mt-1 text-sm text-[var(--text-muted)]">{chatStatus}</p>
              </div>

              <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto px-6 py-6">
                <ChatHistoryPanel
                  messages={chatMessages}
                  isThinking={isThinking}
                  showThinkingSummary={showThinkingSummary}
                />
              </div>

              <form onSubmit={(event) => void handleSendChat(event)} className="border-t border-[var(--border)] p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <label className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <input
                      type="checkbox"
                      checked={showThinkingSummary}
                      onChange={(event) => setShowThinkingSummary(event.target.checked)}
                    />
                    <span>Include thinking summary when available</span>
                  </label>
                </div>
                <div className="flex items-end gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-3">
                  <textarea
                    rows={3}
                    value={chatInput}
                    onChange={(event) => setChatInput(event.target.value)}
                    placeholder="Ask Counsel AI anything about the selected matter..."
                    className="min-h-[72px] flex-1 resize-none bg-transparent px-2 py-1 outline-none"
                  />
                  <button
                    type="submit"
                    className="rounded-xl bg-[var(--secondary-container)] px-5 py-3 text-[11px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]"
                  >
                    Send
                  </button>
                </div>
              </form>
            </div>

            <aside className="grid min-h-0 content-start gap-4 xl:h-full xl:grid-rows-[auto_minmax(0,1fr)]">
              <PanelCard title="Matters">
                <form className="grid gap-3" onSubmit={(event) => void handleCreateMatter(event)}>
                  <input
                    value={matterNameDraft}
                    onChange={(event) => setMatterNameDraft(event.target.value)}
                    placeholder="New matter name"
                    className={inputClassName}
                  />
                  <button
                    type="submit"
                    className="rounded-xl bg-[var(--secondary-container)] px-4 py-3 text-[11px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]"
                  >
                    Create Matter
                  </button>
                </form>
              </PanelCard>

              <div className="custom-scrollbar min-h-0 overflow-y-auto rounded-3xl border border-[var(--border)] bg-white p-4">
                <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]">
                  Session List
                </p>
                <div className="mt-4 grid gap-3">
                  {sessions.length ? (
                    sessions.map((session) => (
                      <div
                        key={session.session_id}
                        className={`rounded-2xl border p-4 transition ${
                          selectedSessionId === session.session_id
                            ? "border-[var(--secondary)] bg-amber-50"
                            : "border-[var(--border)] bg-white"
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => void handleSessionChange(session.session_id)}
                          className="w-full text-left"
                        >
                          <strong className="block text-sm text-[var(--primary)]">
                            {session.name || "Untitled matter"}
                          </strong>
                        </button>
                        <div className="mt-3 flex gap-2">
                          <button
                            type="button"
                            onClick={() => void handleSessionChange(session.session_id)}
                            className="rounded-xl bg-[var(--secondary-container)] px-3 py-2 text-[10px] font-extrabold uppercase tracking-[0.14em] text-[var(--primary)]"
                          >
                            Open
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDeleteMatter(session.session_id)}
                            className="rounded-xl border border-rose-200 px-3 py-2 text-[10px] font-extrabold uppercase tracking-[0.14em] text-rose-700"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm leading-7 text-[var(--text-muted)]">
                      No matters yet. Create one to begin.
                    </p>
                  )}
                </div>
              </div>
            </aside>
          </section>
        ) : activePage === "drafting-suite" ? (
          <section className="grid min-h-[calc(100vh-88px)] grid-cols-1 xl:grid-cols-[minmax(360px,42%)_minmax(560px,1fr)_320px]">
            <section className="custom-scrollbar border-r border-[var(--border)] bg-[var(--surface-container-low)]">
              <div className="mx-auto grid max-w-3xl gap-6 p-6 lg:p-10">
                <StatusBanner statusState={statusState} statusMessage={statusMessage} />

                <section className="grid gap-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-[color:rgba(0,11,29,0.42)]">
                        Step 01
                      </span>
                      <h3 className="mt-2 text-2xl font-extrabold text-[var(--primary)]">
                        Citation Details
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => void handleRefresh()}
                      className="rounded-lg px-3 py-2 text-xs font-bold text-[var(--primary)] transition hover:bg-black/5"
                    >
                      Refresh
                    </button>
                  </div>

                  <label className="grid gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--primary)]">
                      Upload supporting PDF
                    </span>
                    <input
                      type="file"
                      accept="application/pdf"
                      onChange={(event) => void handlePdfSelected(event)}
                      className={inputClassName}
                    />
                  </label>

                  <p className="text-[11px] uppercase tracking-[0.12em] text-[color:rgba(26,28,30,0.65)]">
                    {uploadStatus}
                  </p>

                  <label className="grid gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--primary)]">
                      Source document
                    </span>
                    <select
                      value={selectedDocumentName}
                      onChange={(event) => void handleDocumentChange(event)}
                      className={inputClassName}
                    >
                      {!documents.length && <option value="">No source documents available</option>}
                      {documents.map((documentItem) => (
                        <option key={documentItem.document_name} value={documentItem.document_name}>
                          {documentItem.document_name} ({documentItem.total_pages}{" "}
                          {documentItem.total_pages === 1 ? "page" : "pages"})
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="grid gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--primary)]">
                      Source extraction / page
                    </span>
                    <select
                      value={selectedExtractionId}
                      onChange={(event) => setSelectedExtractionId(event.target.value)}
                      className={inputClassName}
                    >
                      {!extractions.length && (
                        <option value="">
                          {selectedDocumentName
                            ? "No extractions available for this document"
                            : "Select a document first"}
                        </option>
                      )}
                      {extractions.map((extraction) => (
                        <option key={extraction.id} value={String(extraction.id)}>
                          {extraction.page_number === null || extraction.page_number === undefined
                            ? "Unpaged extraction"
                            : `Page ${extraction.page_number}`}{" "}
                          - Extraction #{extraction.id}
                        </option>
                      ))}
                    </select>
                  </label>

                  <PanelCard title="Selected source summary">
                    {selectedExtraction ? (
                      <>
                        <strong className="text-[var(--primary)]">{selectedExtraction.document_name}</strong>
                        <br />
                        {selectedExtraction.page_number === null ||
                        selectedExtraction.page_number === undefined
                          ? "Unpaged extraction"
                          : `Page ${selectedExtraction.page_number}`}
                        <br />
                        {Object.entries(selectedExtraction.metadata || {}).length
                          ? Object.entries(selectedExtraction.metadata || {})
                              .slice(0, 4)
                              .map(([key, value]) => `${humanizeKey(key)}: ${String(value)}`)
                              .join(" | ")
                          : "No structured metadata available."}
                        <br />
                        <br />
                        {buildSnippet(selectedExtraction.raw_text, 220)}
                      </>
                    ) : (
                      <>Choose a source document to ground the appeal in real materials.</>
                    )}
                  </PanelCard>
                </section>

                <div className="grid gap-4 md:grid-cols-2">
                  <FormField label="Offence reference number" className="md:col-span-2">
                    <input
                      value={offenceReference}
                      onChange={(event) => setOffenceReference(event.target.value)}
                      className={inputClassName}
                    />
                  </FormField>

                  <FormField label="Date of incident">
                    <input
                      type="date"
                      value={incidentDate}
                      onChange={(event) => setIncidentDate(event.target.value)}
                      className={inputClassName}
                    />
                  </FormField>

                  <FormField label="Location (nearest town)">
                    <input
                      value={incidentLocation}
                      onChange={(event) => setIncidentLocation(event.target.value)}
                      className={inputClassName}
                    />
                  </FormField>
                </div>

                <section className="grid gap-3">
                  <label className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--primary)]">
                    Offence category
                  </label>
                  {offenceCatalog.map((option) => (
                    <label
                      key={option.value}
                      className="flex cursor-pointer items-start gap-3 rounded-2xl border border-[var(--border)] bg-white p-4 transition hover:border-[color:rgba(115,92,0,0.35)]"
                    >
                      <input
                        type="radio"
                        name="offenceCategory"
                        value={option.value}
                        checked={selectedOffenceValue === option.value}
                        onChange={(event) => setSelectedOffenceValue(event.target.value)}
                        className="mt-1"
                      />
                      <div>
                        <strong className="block text-[var(--primary)]">{option.title}</strong>
                        <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                          {option.subtitle}
                        </p>
                      </div>
                    </label>
                  ))}
                </section>

                <FormField label="Mitigating circumstances">
                  <textarea
                    rows={6}
                    value={mitigatingCircumstances}
                    onChange={(event) => setMitigatingCircumstances(event.target.value)}
                    placeholder="Describe environmental conditions, technical faults, or humanitarian grounds..."
                    className={`${inputClassName} min-h-36`}
                  />
                </FormField>

                <div className="border-t border-black/8 pt-6">
                  <button
                    type="button"
                    onClick={() => void handleAnalyzeDraft()}
                    className="flex w-full items-center justify-center gap-3 rounded-xl bg-[var(--secondary-container)] px-5 py-4 text-[11px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)] transition hover:scale-[0.99]"
                  >
                    Generate Document Preview
                    <span className="material-symbols-outlined">auto_awesome</span>
                  </button>
                  <p className="mt-4 text-center text-[11px] uppercase tracking-[0.16em] text-[color:rgba(26,28,30,0.64)]">
                    Ground your draft in source materials and concise AI suggestions.
                  </p>
                </div>
              </div>
            </section>

            <section className="custom-scrollbar flex justify-center overflow-y-auto bg-[var(--surface-container-highest)] p-6 lg:p-10">
              <DraftPreview draftModel={draftModel} />
            </section>

            <aside className="custom-scrollbar border-l border-[var(--border)] bg-white/80 p-6 backdrop-blur xl:overflow-y-auto">
              <DraftInsights
                strengthAnalysis={strengthAnalysis}
                recommendation={recommendation}
                precedents={precedents}
                insightSummary={insightSummary}
                selectedDocument={selectedDocument}
              />
            </aside>
          </section>
        ) : activePage === "archive" ? (
          <section className="grid min-h-[calc(100vh-88px)] grid-cols-1 gap-6 bg-[var(--surface-container-low)] p-6 xl:grid-cols-[360px_minmax(0,1fr)] xl:p-10">
            <div className="grid content-start gap-4">
              <StatusBanner statusState={statusState} statusMessage={statusMessage} />
              <PanelCard title="Documents">
                {documents.length ? (
                  <div className="grid gap-3">
                    {documents.map((documentItem) => (
                      <button
                        key={documentItem.document_name}
                        type="button"
                        onClick={() =>
                          void handleDocumentChange({
                            target: { value: documentItem.document_name },
                          } as ChangeEvent<HTMLSelectElement>)
                        }
                        className={`rounded-xl border p-4 text-left transition ${
                          selectedDocumentName === documentItem.document_name
                            ? "border-[var(--secondary)] bg-amber-50"
                            : "border-[var(--border)] bg-white hover:border-[color:rgba(115,92,0,0.35)]"
                        }`}
                      >
                        <strong className="block text-sm text-[var(--primary)]">
                          {documentItem.document_name}
                        </strong>
                        <span className="mt-1 block text-xs leading-6 text-[var(--text-muted)]">
                          {documentItem.total_pages} page(s) | {documentItem.total_rows} row(s)
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <>No source materials are available yet.</>
                )}
              </PanelCard>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,300px)_minmax(0,1fr)]">
              <PanelCard title="Extractions">
                {extractions.length ? (
                  <div className="grid gap-3">
                    {extractions.map((extraction) => (
                      <button
                        key={extraction.id}
                        type="button"
                        onClick={() => setSelectedExtractionId(String(extraction.id))}
                        className={`rounded-xl border p-4 text-left transition ${
                          String(extraction.id) === String(selectedExtractionId)
                            ? "border-[var(--secondary)] bg-amber-50"
                            : "border-[var(--border)] bg-white hover:border-[color:rgba(115,92,0,0.35)]"
                        }`}
                      >
                        <strong className="block text-sm text-[var(--primary)]">
                          {extraction.page_number === null || extraction.page_number === undefined
                            ? "Unpaged extraction"
                            : `Page ${extraction.page_number}`}
                        </strong>
                      </button>
                    ))}
                  </div>
                ) : (
                  <>No extractions are available for the selected document.</>
                )}
              </PanelCard>

              <PanelCard title="Extraction Content">
                {selectedExtraction ? (
                  <div className="grid gap-4 text-sm leading-7 text-[var(--text-muted)]">
                    <div>
                      <strong className="text-[var(--primary)]">{selectedExtraction.document_name}</strong>
                      <div>
                        {selectedExtraction.page_number === null ||
                        selectedExtraction.page_number === undefined
                          ? "Unpaged extraction"
                          : `Page ${selectedExtraction.page_number}`}
                      </div>
                    </div>
                    <div>
                      <p className="mb-2 text-[10px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]">
                        Metadata
                      </p>
                      <pre className="whitespace-pre-wrap break-words rounded-xl bg-[var(--surface)] p-4 text-xs leading-6">
                        {JSON.stringify(selectedExtraction.metadata || {}, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <p className="mb-2 text-[10px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]">
                        Raw text
                      </p>
                      <div className="whitespace-pre-wrap break-words rounded-xl bg-[var(--surface)] p-4">
                        {selectedExtraction.raw_text || "No raw text available for this extraction."}
                      </div>
                    </div>
                  </div>
                ) : (
                  <>Choose an extraction to inspect its content.</>
                )}
              </PanelCard>
            </div>
          </section>
        ) : activePage === "docket" ? (
          <section className="grid min-h-[calc(100vh-88px)] grid-cols-1 gap-6 bg-[var(--surface-container-low)] p-6 xl:grid-cols-[360px_minmax(0,1fr)] xl:p-10">
            <div className="grid content-start gap-4">
              <StatusBanner statusState={statusState} statusMessage={statusMessage} />
              <PanelCard title="Create Matter">
                <form className="grid gap-3" onSubmit={(event) => void handleCreateMatter(event)}>
                  <input
                    value={matterNameDraft}
                    onChange={(event) => setMatterNameDraft(event.target.value)}
                    placeholder="Matter / appeal title"
                    className={inputClassName}
                  />
                  <button
                    type="submit"
                    className="rounded-xl bg-[var(--secondary-container)] px-4 py-3 text-[11px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]"
                  >
                    Add Matter
                  </button>
                </form>
              </PanelCard>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {sessions.length ? (
                sessions.map((session) => (
                  <div
                    key={session.session_id}
                    className={`rounded-3xl border p-5 ${
                      session.session_id === selectedSessionId
                        ? "border-[var(--secondary)] bg-amber-50"
                        : "border-[var(--border)] bg-white"
                    }`}
                  >
                    <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[var(--text-muted)]">
                      Matter
                    </p>
                    <h3 className="mt-2 text-lg font-extrabold text-[var(--primary)]">
                      {session.name || "Untitled matter"}
                    </h3>
                    <div className="mt-4 flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          void handleSessionChange(session.session_id);
                          window.location.hash = "#counsel-ai";
                          setActivePage("counsel-ai");
                        }}
                        className="rounded-xl bg-[var(--secondary-container)] px-4 py-3 text-[11px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]"
                      >
                        Open
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDeleteMatter(session.session_id)}
                        className="rounded-xl border border-rose-200 px-4 py-3 text-[11px] font-extrabold uppercase tracking-[0.16em] text-rose-700"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <PanelCard title="Docket">
                  No matters yet. Create one to start tracking legal work in Lawyer Jalan.
                </PanelCard>
              )}
            </div>
          </section>
        ) : (
          <section className="grid min-h-[calc(100vh-88px)] grid-cols-1 gap-6 bg-[var(--surface-container-low)] p-6 xl:grid-cols-[minmax(0,380px)_minmax(0,1fr)] xl:p-10">
            <div className="grid content-start gap-4">
              <StatusBanner statusState={statusState} statusMessage={statusMessage} />
              <PanelCard title="Workspace">
                <div className="grid gap-2 text-sm leading-7 text-[var(--text-muted)]">
                  <div>Brand: Lawyer Jalan</div>
                  <div>Documents: {documents.length}</div>
                  <div>Matters: {sessions.length}</div>
                  <div>Storage: {health?.status === "healthy" ? "Ready" : "Unavailable"}</div>
                </div>
              </PanelCard>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <PanelCard title="Interface Preferences">
                The Counsel AI workspace now keeps the chat in the center, the matter list on the right, the composer inside the chat window, and the display focused on the latest exchange.
              </PanelCard>
              <PanelCard title="Reasoning Summaries">
                Turn on “Include thinking summary when available” to ask for a concise reasoning summary above the final answer. While a response is being generated, Lawyer Jalan now shows a live thinking animation.
              </PanelCard>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function NavButton(props: { item: NavItem; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      className={`flex items-center gap-4 rounded-xl px-4 py-3 text-left text-[11px] font-bold uppercase tracking-[0.18em] transition ${
        props.active
          ? "bg-[var(--secondary-container)] text-[var(--primary)]"
          : "text-[var(--text-muted)] hover:bg-black/5 hover:text-[var(--primary)]"
      }`}
    >
      <span className={`material-symbols-outlined ${props.active ? "filled" : ""}`}>
        {props.item.icon}
      </span>
      <span>{props.item.label}</span>
    </button>
  );
}

function ToolbarButton(props: { icon: string; title: string; onClick: () => void }) {
  return (
    <button
      type="button"
      title={props.title}
      onClick={props.onClick}
      className="grid h-10 w-10 place-items-center rounded-lg text-[var(--primary)] transition hover:bg-black/5"
    >
      <span className="material-symbols-outlined">{props.icon}</span>
    </button>
  );
}

function StatusBanner(props: { statusState: StatusState; statusMessage: string }) {
  return (
    <div
      className={`rounded-2xl border px-4 py-3 text-sm ${
        props.statusState === "ready"
          ? "border-emerald-200 bg-emerald-50 text-emerald-900"
          : props.statusState === "error"
            ? "border-rose-200 bg-rose-50 text-rose-900"
            : "border-transparent bg-[var(--surface-container)] text-[var(--text-muted)]"
      }`}
    >
      {props.statusMessage}
    </div>
  );
}

function StatusPill(props: { statusState: StatusState; statusMessage: string }) {
  return (
    <div
      className={`inline-flex rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] ${
        props.statusState === "ready"
          ? "bg-emerald-100 text-emerald-800"
          : props.statusState === "error"
            ? "bg-rose-100 text-rose-800"
            : "bg-slate-100 text-slate-700"
      }`}
    >
      {props.statusMessage}
    </div>
  );
}

function PanelCard(props: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-[var(--border)] bg-white p-5">
      <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]">
        {props.title}
      </p>
      <div className="mt-3 text-sm leading-7 text-[var(--text-muted)]">{props.children}</div>
    </div>
  );
}

function FormField(props: { label: string; children: ReactNode; className?: string }) {
  return (
    <label className={`grid gap-2 ${props.className ?? ""}`}>
      <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--primary)]">
        {props.label}
      </span>
      {props.children}
    </label>
  );
}

function ChatHistoryPanel(props: {
  messages: Message[];
  isThinking: boolean;
  showThinkingSummary: boolean;
}) {
  const visibleMessages = props.messages.filter((message) => message.role !== "system");

  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col justify-start gap-4">
      {visibleMessages.length ? (
        visibleMessages.map((message, index) => {
          if (message.role === "user") {
            return (
              <div
                key={`user-${index}`}
                className="ml-auto max-w-3xl rounded-2xl bg-[var(--secondary-container)] px-4 py-3 text-sm leading-7 text-[var(--primary)]"
              >
                {message.content}
              </div>
            );
          }

          if (message.role === "tool") {
            const toolName =
              typeof message.metadata?.tool_name === "string"
                ? message.metadata.tool_name
                : message.title || "Tool activity";
            const eventLabel =
              typeof message.metadata?.event === "string"
                ? message.metadata.event
                : "activity";

            return (
              <div
                key={`tool-${index}`}
                className="max-w-3xl rounded-2xl border border-sky-100 bg-sky-50 px-4 py-4 text-sm leading-7 text-sky-950"
              >
                <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-sky-700">
                  {eventLabel === "invocation" ? "Tool Invoked" : "Tool Result"}
                </p>
                <p className="mt-1 font-bold">{toolName}</p>
                <div className="mt-2 whitespace-pre-wrap break-words text-sm leading-7">
                  {message.content}
                </div>
              </div>
            );
          }

          const parsed = parseAssistantDisplay(message.content);
          return (
            <div
              key={`assistant-${index}`}
              className="max-w-3xl rounded-2xl bg-[var(--surface-container-low)] px-4 py-4 text-sm leading-7 text-[var(--text)]"
            >
              {props.showThinkingSummary && parsed.thinking ? (
                <div className="mb-4 rounded-2xl border border-[var(--border)] bg-white px-4 py-3">
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]">
                    Thinking Summary
                  </p>
                  <div className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-[var(--text-muted)]">
                    {parsed.thinking}
                  </div>
                </div>
              ) : null}
              <div className="whitespace-pre-wrap break-words">
                {parsed.final || message.content}
              </div>
            </div>
          );
        })
      ) : (
        <div className="rounded-2xl bg-[var(--surface-container-low)] px-4 py-3 text-sm leading-7 text-[var(--text-muted)]">
          Start a new matter or open an existing one, then ask Counsel AI a question.
        </div>
      )}

      {props.isThinking && (
        <div className="max-w-3xl rounded-2xl bg-[var(--surface-container-low)] px-4 py-4 text-sm text-[var(--text-muted)]">
          <div className="mb-2 font-bold text-[var(--primary)]">Lawyer Jalan is thinking</div>
          <div className="flex items-center gap-2">
            <span className="thinking-dot"></span>
            <span className="thinking-dot"></span>
            <span className="thinking-dot"></span>
          </div>
        </div>
      )}
    </div>
  );
}

function DraftPreview(props: {
  draftModel: ReturnType<typeof buildDraftModel>;
}) {
  return (
    <div id="printable-preview" className="legal-bond text-[#1a1a1a]">
      <div className="watermark">Malaysian Law</div>

      <div className="mb-12 flex items-start justify-between gap-6">
        <div className="text-[10px] leading-7 font-black uppercase tracking-[0.12em]">
          PRIVATE &amp; CONFIDENTIAL
          <br />
          Ref: {props.draftModel.internalReference}
        </div>

        <div className="text-right">
          <h4 className="mb-2 text-lg font-bold">Lawyer Jalan</h4>
          <p className="text-[12px] leading-6">
            Level 42, Vista Tower, The Intermark
            <br />
            182, Jalan Tun Razak, 50400
            <br />
            Kuala Lumpur, Malaysia
          </p>
        </div>
      </div>

      <div className="mb-10 text-[13px] leading-7">
        <p className="mb-6">Date: {props.draftModel.letterDate}</p>
        <p className="font-bold">The Director General</p>
        <p>Road Transport Department Malaysia (JPJ)</p>
        <p>Block D4, Complex D, Federal Government Administrative Centre</p>
        <p>62620 Putrajaya, Malaysia</p>
      </div>

      <div className="mb-8 border-y-2 border-black/20 py-3">
        <h5 className="text-center text-[14px] font-bold uppercase underline">
          Formal Appeal Against Compound/Notice: {props.draftModel.referenceNumber}
        </h5>
      </div>

      <div className="space-y-6 text-[13px] leading-8 text-justify">
        <p>Dear Sir / Madam,</p>
        <p>{props.draftModel.openingParagraph}</p>
        <p>{props.draftModel.contextParagraph}</p>
        <p>
          Pursuant to the provisions of the <strong>Road Transport Act 1987</strong>, we seek a
          review of the penalty based on the following legal and factual considerations:
        </p>
        <ol className="list-decimal space-y-4 pl-5">
          {props.draftModel.arguments.map((argument) => (
            <li key={argument.title}>
              <strong>{argument.title}:</strong> {argument.body}
            </li>
          ))}
        </ol>
        <p>{props.draftModel.closingParagraph}</p>
        <p>We remain available for any clarification or hearing the Department may require.</p>
      </div>

      <div className="mt-16 text-[12px]">
        <p>Yours faithfully,</p>
        <div className="signature-mark">M. Zulkafli</div>
        <p className="font-bold">Lawyer Jalan Road Transport Division</p>
        <p>Lawyer Jalan (Legal Practitioners)</p>
      </div>

      <div className="mt-12 flex justify-between gap-4 border-t border-black/10 pt-4 text-[8px] text-black/60">
        <span>DOCUMENT ID: {props.draftModel.documentId}</span>
        <span>CONFIDENTIAL LEGAL WORK PRODUCT</span>
        <span>PAGE 01 OF 01</span>
      </div>
    </div>
  );
}

function DraftInsights(props: {
  strengthAnalysis: string;
  recommendation: string;
  precedents: PrecedentSuggestion[];
  insightSummary: string;
  selectedDocument: DocumentSummary | null;
}) {
  return (
    <>
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined filled text-[var(--secondary)]">
          auto_fix_high
        </span>
        <h4 className="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--primary)]">
          Counsel AI Insights
        </h4>
      </div>

      <div className="mt-6 rounded-r-2xl border-l-4 border-emerald-500 bg-emerald-50 p-4">
        <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-emerald-800">
          Strength Analysis
        </p>
        <p className="mt-2 text-sm leading-7 text-emerald-950">{props.strengthAnalysis}</p>
      </div>

      <div className="mt-6">
        <h5 className="border-b border-black/5 pb-2 text-[10px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]">
          Precedent Suggestions
        </h5>
        <div className="mt-3 grid gap-3">
          {props.precedents.map((precedent) => (
            <button
              key={`${precedent.title}-${precedent.rationale}`}
              type="button"
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 text-left transition hover:border-[color:rgba(115,92,0,0.35)]"
            >
              <strong className="block text-sm text-[var(--primary)]">{precedent.title}</strong>
              <span className="mt-1 block text-xs leading-6 text-[var(--text-muted)]">
                {precedent.rationale}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 rounded-2xl bg-[var(--primary-container)] p-4 text-[var(--primary-soft)]">
        <p className="text-[10px] font-extrabold uppercase tracking-[0.16em]">
          Next Step Recommendation
        </p>
        <p className="mt-2 text-sm leading-7 text-white/80">{props.recommendation}</p>
      </div>

      <div className="mt-6 rounded-2xl border border-[var(--border)] bg-white p-4">
        <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-[var(--primary)]">
          Source Snapshot
        </p>
        <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-[var(--text-muted)]">
          {props.insightSummary}
        </p>
        {props.selectedDocument ? (
          <div className="mt-4 rounded-xl bg-[var(--surface)] p-3 text-xs leading-6 text-[var(--text-muted)]">
            <strong className="block text-[var(--primary)]">{props.selectedDocument.document_name}</strong>
            Pages: {props.selectedDocument.total_pages} | Rows: {props.selectedDocument.total_rows}
            <br />
            Report date: {props.selectedDocument.report_date || "Not provided"}
          </div>
        ) : null}
      </div>
    </>
  );
}

function parseAssistantDisplay(content: string): { thinking: string; final: string } {
  if (!content.trim()) {
    return { thinking: "", final: "" };
  }

  const thinkTagMatch = content.match(/<think>([\s\S]*?)<\/think>/i);
  if (thinkTagMatch) {
    return {
      thinking: thinkTagMatch[1].trim(),
      final: content.replace(thinkTagMatch[0], "").trim(),
    };
  }

  const sectionMatch = content.match(
    /thinking steps\s*:?\s*([\s\S]*?)final answer\s*:?\s*([\s\S]*)/i,
  );
  if (sectionMatch) {
    return {
      thinking: sectionMatch[1].trim(),
      final: sectionMatch[2].trim(),
    };
  }

  return { thinking: "", final: content.trim() };
}

const inputClassName =
  "rounded-xl border border-[var(--border)] bg-white px-4 py-3 outline-none transition focus:border-[var(--secondary)] focus:ring-3 focus:ring-amber-200";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}${text ? ` - ${text}` : ""}`);
  }
  return (await response.json()) as T;
}

async function fetchNoContent(url: string, options?: RequestInit): Promise<void> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}${text ? ` - ${text}` : ""}`);
  }
}

export default App;
