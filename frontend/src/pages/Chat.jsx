import { useState, useRef, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { Send, Bot, User, Sparkles, Search, Database, Brain, MessageSquare, FileUp, Loader2 } from "lucide-react";
import Markdown from "react-markdown";
import { API_URL, getAuthToken } from "../api/client";
import styles from "./Chat.module.css";

const PHASE_META = {
  searching: { icon: Search, label: "Searching knowledge base" },
  retrieving: { icon: Database, label: "Retrieving context" },
  thinking: { icon: Brain, label: "Analyzing documents" },
  answering: { icon: MessageSquare, label: "Generating answer" },
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

export default function Chat() {
  const { 
    messages, isStreaming, phase, 
    sendMessage 
  } = useOutletContext();
  
  const [input, setInput] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const endRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, phase]);

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

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("strategy", "recursive");

    try {
      const res = await fetch(`${API_URL}/docs/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      setUploadStatus("success");
      setTimeout(() => setUploadStatus(null), 3000);
    } catch (err) {
      console.error(err);
      setUploadStatus("error");
      setTimeout(() => setUploadStatus(null), 3000);
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  };

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
              ref={fileInputRef}
              className={styles.uploadInput}
              onChange={handleFileUpload}
            />
            <button 
              className={styles.uploadBtn}
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              {isUploading ? <Loader2 size={16} className="animate-spin" /> : <FileUp size={16} />}
              {isUploading ? "Uploading..." : uploadStatus === "success" ? "Success!" : uploadStatus === "error" ? "Failed" : "Upload Document"}
            </button>
          </div>
        </div>

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
          <div
            key={i}
            className={`${styles.message} ${styles[msg.role]}`}
          >
            <div className={`${styles.avatar} ${styles[msg.role]}`}>
              {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={`${styles.bubble} ${styles[msg.role]}`}>
              {msg.role === "user" ? (
                msg.content
              ) : msg.content ? (
                <Markdown>{msg.content}</Markdown>
              ) : phase && phase !== "answering" ? (
                <StatusPipeline phase={phase} />
              ) : (
                <TypingDots />
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
    </div>
  );
}
