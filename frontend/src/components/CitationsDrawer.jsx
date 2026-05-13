import { useState, useEffect } from "react";
import { BookOpen, X, FileText, ChevronRight, Loader2 } from "lucide-react";
import { fetchApi } from "../api/client";
import styles from "./CitationsDrawer.module.css";

/**
 * CitationsDrawer — slides in from the right showing source documents
 * and page excerpts for a given queryId.
 */
export default function CitationsDrawer({ queryId, onClose }) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    if (!queryId) return;
    setLoading(true);
    setError(null);
    fetchApi(`/chat/${queryId}/citations`)
      .then(setData)
      .catch((e) => setError(e.message || "Failed to load citations"))
      .finally(() => setLoading(false));
  }, [queryId]);

  const toggleExpand = (docId) =>
    setExpanded((prev) => ({ ...prev, [docId]: !prev[docId] }));

  return (
    <>
      {/* Backdrop */}
      <div className={styles.backdrop} onClick={onClose} />

      {/* Drawer */}
      <aside className={styles.drawer}>
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <BookOpen size={16} />
            <span>Sources</span>
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        <div className={styles.body}>
          {loading && (
            <div className={styles.center}>
              <Loader2 size={20} className={styles.spin} />
              <span>Loading citations…</span>
            </div>
          )}

          {error && (
            <div className={styles.errorMsg}>{error}</div>
          )}

          {data && !loading && (
            <>
              <p className={styles.queryText}>
                <em>"{data.query_text}"</em>
              </p>

              {data.sources.length === 0 ? (
                <div className={styles.empty}>No source chunks were retrieved for this answer.</div>
              ) : (
                <ul className={styles.sourceList}>
                  {data.sources.map((src, i) => (
                    <li key={src.document_id} className={styles.sourceCard}>
                      <button
                        className={styles.sourceHeader}
                        onClick={() => toggleExpand(src.document_id)}
                        aria-expanded={!!expanded[src.document_id]}
                      >
                        <span className={styles.sourceIndex}>{i + 1}</span>
                        <FileText size={14} className={styles.sourceIcon} />
                        <span className={styles.sourceFilename} title={src.filename}>
                          {src.filename}
                        </span>
                        <span className={styles.pagesBadge}>
                          {src.pages.length > 0
                            ? `p. ${src.pages.join(", ")}`
                            : ""}
                        </span>
                        <ChevronRight
                          size={14}
                          className={`${styles.chevron} ${expanded[src.document_id] ? styles.chevronOpen : ""}`}
                        />
                      </button>

                      {expanded[src.document_id] && src.excerpt && (
                        <div className={styles.excerpt}>
                          <p>{src.excerpt}</p>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
