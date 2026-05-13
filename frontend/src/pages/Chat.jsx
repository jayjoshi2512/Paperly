import { useState, useRef, useEffect, useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import { Send, Bot, User, Sparkles, Search, Database, Brain, MessageSquare, FileUp, Loader2, CheckCircle2, AlertCircle, ThumbsUp, ThumbsDown, BookOpen } from "lucide-react";
import Markdown from "react-markdown";
import styles from "./Chat.module.css";
import { useDocuments } from "../hooks/useDocuments";
import { API_URL, getAuthToken } from "../api/client";
import CitationsDrawer from "../components/CitationsDrawer";

const PHASE_META = {
  searching:  { icon: Search,        label: "Searching knowledge base" },
  retrieving: { icon: Database,       label: "Retrieving context" },
  thinking:   { icon: Brain,          label: "Analyzing documents" },
  answering:  { icon: MessageSquare,  label: "Generating answer" },
};

const PHASE_ORDER = ["searching", "retrieving", "thinking", "answering"];

function StatusPipeline({ phase }) {
  const activeIdx = PHASE_ORDER.indexOf(phase);
  return (
    <div className={styles.statusPipeline}>
      {PHASE_ORDER.map((step, i) => {
        let state = "";
        if (i < activeIdx) state = "done";
        else if (i === activeIdx) state = "active";
        return (
          <div key={step} style={{ display: "flex", alignItems: "center", gap: "var(--space-sm)" }}>
            {i > 0 && <div className={styles.statusSep} />}
            <div className={`${styles.statusStep} ${state ? styles[state] : ""}`}>
              <div className={styles.statusDot} />
              <span>{PHASE_META[step].label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TypingDots() {
  return (
    <div className={styles.typing}>
      <div className={styles.typingDot} />
      <div className={styles.typingDot} />
      <div className={styles.typingDot} />
    </div>
  );
}

const QUICK_PROMPTS = [
  "Summarize the key findings",
  "What are the main topics?",
  "Compare the documents",
];

/**
 * Thumbs-up / thumbs-down bar shown below each assistant message.
 * Tracks submitted state per-message to prevent double submission.
 */
function FeedbackBar({ queryId }) {
  const [state, setState] = useState("idle"); // idle | positive | negative | submitted
  const [correctAnswer, setCorrectAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!queryId) return null;

  const submit = async (rating, answer) => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await fetch(`${API_URL}/chat/${queryId}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ rating, correct_answer: answer || null }),
      });
      setState("submitted");
    } catch (e) {
      console.error("Feedback failed:", e);
    } finally {
      setSubmitting(false);
    }
  };

  if (state === "submitted") {
    return <p className={styles.feedbackDone}>✓ Thanks for the feedback</p>;
  }

  return (
    <div className={styles.feedbackBar}>
      {state === "idle" && (
        <>
          <button
            className={styles.feedbackBtn}
            onClick={() => submit("positive", null)}
            title="Helpful"
          >
            <ThumbsUp size={13} />
          </button>
          <button
            className={styles.feedbackBtn}
            onClick={() => setState("negative")}
            title="Not helpful"
          >
            <ThumbsDown size={13} />
          </button>
        </>
      )}
      {state === "negative" && (
        <div className={styles.feedbackNeg}>
          <p className={styles.feedbackNegLabel}>What's the correct answer? (optional)</p>
          <textarea
            className={styles.feedbackTextarea}
            rows={2}
            placeholder="Type the correct answer, or leave blank..."
            value={correctAnswer}
            onChange={(e) => setCorrectAnswer(e.target.value)}
          />
          <div className={styles.feedbackNegBtns}>
            <button
              className={styles.feedbackSubmitBtn}
              onClick={() => submit("negative", correctAnswer)}
              disabled={submitting}
            >
              {submitting ? "Submitting..." : "Submit"}
            </button>
            <button
              className={styles.feedbackSkipBtn}
              onClick={() => submit("negative", null)}
              disabled={submitting}
            >
              Skip
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Chat() {
  const { messages, isStreaming, phase, sendMessage } = useOutletContext();
  const { uploadDocument, uploadBatch, pollDocumentStatus } = useDocuments();

  const [input, setInput]                 = useState("");
  // batchUploads: Map<documentId, { phase, pct, message, filename }>
  const [batchUploads, setBatchUploads]   = useState(new Map());

  const endRef       = useRef(null);
  const fileInputRef = useRef(null);
  const stopPollingMap = useRef(new Map()); // documentId -> stop()

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, phase]);

  // Auto-clear completed/failed upload rows after 5 seconds
  useEffect(() => {
    const timeouts = [];
    batchUploads.forEach((state, docId) => {
      if (state.phase === "done" || state.phase === "error") {
        timeouts.push(
          setTimeout(() => {
            setBatchUploads(prev => {
              const next = new Map(prev);
              next.delete(docId);
              return next;
            });
          }, 5000)
        );
      }
    });
    return () => timeouts.forEach(clearTimeout);
  }, [batchUploads]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    sendMessage(input.trim());
    setInput("");
  };

  const handleQuickPrompt = (prompt) => {
    if (isStreaming) return;
    sendMessage(prompt);
  };

  const handleFileChange = useCallback(async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    e.target.value = ""; // reset so same files can be re-selected

    const startPoll = (docId, filename) => {
      const stop = pollDocumentStatus(docId, {
        onUpdate: ({ progress_pct, progress_message }) => {
          setBatchUploads(prev => {
            const next = new Map(prev);
            next.set(docId, { ...next.get(docId), phase: "processing", pct: progress_pct, message: progress_message || "Processing..." });
            return next;
          });
        },
        onComplete: () => {
          stopPollingMap.current.delete(docId);
          setBatchUploads(prev => {
            const next = new Map(prev);
            next.set(docId, { phase: "done", pct: 100, message: "Ready", filename });
            return next;
          });
        },
        onError: (msg) => {
          stopPollingMap.current.delete(docId);
          setBatchUploads(prev => {
            const next = new Map(prev);
            next.set(docId, { phase: "error", pct: 0, message: msg, filename });
            return next;
          });
        },
      });
      stopPollingMap.current.set(docId, stop);
    };

    if (files.length === 1) {
      // Single file — direct upload
      const file = files[0];
      const tempId = `temp-${Date.now()}`;
      setBatchUploads(prev => new Map(prev).set(tempId, { phase: "uploading", pct: 5, message: "Uploading...", filename: file.name }));
      try {
        const { document_id } = await uploadDocument(file, "recursive");
        setBatchUploads(prev => {
          const next = new Map(prev);
          next.delete(tempId);
          next.set(document_id, { phase: "processing", pct: 10, message: "Extracting text...", filename: file.name });
          return next;
        });
        startPoll(document_id, file.name);
      } catch (err) {
        setBatchUploads(prev => {
          const next = new Map(prev);
          next.set(tempId, { phase: "error", pct: 0, message: err.message || "Upload failed", filename: file.name });
          return next;
        });
      }
    } else {
      // Multi-file — batch upload
      const tempId = `batch-${Date.now()}`;
      setBatchUploads(prev => new Map(prev).set(tempId, { phase: "uploading", pct: 5, message: `Uploading ${files.length} files...`, filename: `${files.length} files` }));
      try {
        const result = await uploadBatch(files, "recursive");
        setBatchUploads(prev => {
          const next = new Map(prev);
          next.delete(tempId);
          // Create a row per accepted file
          for (const item of result.accepted) {
            next.set(item.document_id, { phase: "processing", pct: 10, message: "Processing...", filename: item.filename });
            startPoll(item.document_id, item.filename);
          }
          // Immediately mark rejected
          for (const item of result.rejected) {
            const rId = `rejected-${item.filename}`;
            next.set(rId, { phase: "error", pct: 0, message: item.reason, filename: item.filename });
          }
          return next;
        });
      } catch (err) {
        setBatchUploads(prev => {
          const next = new Map(prev);
          next.set(tempId, { phase: "error", pct: 0, message: err.message || "Batch upload failed", filename: `${files.length} files` });
          return next;
        });
      }
    }
  }, [uploadDocument, uploadBatch, pollDocumentStatus]);

  const isUploadBusy = [...batchUploads.values()].some(s => s.phase === "uploading" || s.phase === "processing");

  // Citations drawer state
  const [citationsQueryId, setCitationsQueryId] = useState(null);

  return (
    <div className={styles.page}>
      <div className={styles.chatContent}>
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <Sparkles size={18} style={{ color: "var(--color-accent)" }} />
            <h2 className={styles.headerTitle}>Chat</h2>
            <span className={styles.headerBadge}>AI</span>
          </div>

          <div className={styles.headerActions}>
            <input
              type="file"
              accept=".pdf,.docx,.doc"
              multiple
              ref={fileInputRef}
              className={styles.uploadInput}
              onChange={handleFileChange}
            />
            <button
              className={styles.uploadBtn}
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploadBusy}
              title="Upload PDF or Word documents (select multiple)"
            >
              {isUploadBusy
                ? <Loader2 size={16} className="animate-spin" />
                : <FileUp size={16} />}
              {isUploadBusy ? "Processing..." : "Upload Docs"}
            </button>
          </div>
        </div>

        {/* ── Per-file upload progress rows ── */}
        {batchUploads.size > 0 && (
          <div className={styles.batchUploadPanel}>
            {[...batchUploads.entries()].map(([docId, state]) => (
              <div key={docId} className={styles.uploadRow}>
                <div className={styles.uploadRowHeader}>
                  <span className={styles.uploadRowFilename} title={state.filename}>
                    {state.filename.length > 28 ? state.filename.slice(0, 25) + "..." : state.filename}
                  </span>
                  {(state.phase === "uploading" || state.phase === "processing") && (
                    <span className={styles.uploadProgressPct}>{state.pct}%</span>
                  )}
                  {state.phase === "done" && (
                    <span className={styles.uploadRowDone}><CheckCircle2 size={12} /> Ready</span>
                  )}
                  {state.phase === "error" && (
                    <span className={styles.uploadRowError}><AlertCircle size={12} /> Failed</span>
                  )}
                </div>
                {(state.phase === "uploading" || state.phase === "processing") && (
                  <div className={styles.uploadProgressBar}>
                    <div className={styles.uploadProgressFill} style={{ width: `${state.pct}%` }} />
                  </div>
                )}
                <p className={styles.uploadProgressMsg}>
                  {state.phase === "error" ? state.message : state.message}
                </p>
              </div>
            ))}
          </div>
        )}

        <div className={styles.messages}>
          {messages.length === 0 && (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>
                <Bot size={28} />
              </div>
              <h3 className={styles.emptyTitle}>Ask anything about your documents</h3>
              <p className={styles.emptyDesc}>
                I search your uploaded knowledge base and provide answers with source citations.
              </p>
              <div className={styles.suggestions}>
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    className={styles.suggestion}
                    onClick={() => handleQuickPrompt(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
              <div className={`${styles.avatar} ${styles[msg.role]}`}>
                {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div className={styles.messageColumn}>
                <div className={`${styles.bubble} ${styles[msg.role]}`}>
                  {msg.role === "user" ? (
                    msg.content
                  ) : msg.content ? (
                    <>
                      <Markdown>{msg.content}</Markdown>
                      {msg.cacheHit && (
                        <span className={styles.cacheBadge} title="Served from semantic cache">
                          ⚡ Cached
                        </span>
                      )}
                    </>
                  ) : phase && phase !== "answering" ? (
                    <StatusPipeline phase={phase} />
                  ) : (
                    <TypingDots />
                  )}
                </div>
                {msg.role === "assistant" && msg.content && msg.queryId && (
                  <div className={styles.messageActions}>
                    <FeedbackBar queryId={msg.queryId} />
                    <button
                      className={styles.citationsBtn}
                      onClick={() => setCitationsQueryId(msg.queryId)}
                      title="View source documents"
                    >
                      <BookOpen size={13} /> Sources
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <div className={styles.inputArea}>
          <div className={styles.inputWrapper}>
            <form onSubmit={handleSend} className={styles.inputForm}>
              <input
                type="text"
                className={styles.chatInput}
                placeholder="Ask a question about your documents…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isStreaming}
                autoFocus
              />
              <button
                type="submit"
                className={styles.sendBtn}
                disabled={isStreaming || !input.trim()}
              >
                <Send size={18} />
              </button>
            </form>
            <p className={styles.disclaimer}>
              Paperly may make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>

      {/* Citations drawer */}
      {citationsQueryId && (
        <CitationsDrawer
          queryId={citationsQueryId}
          onClose={() => setCitationsQueryId(null)}
        />
      )}
    </div>
  );
}
