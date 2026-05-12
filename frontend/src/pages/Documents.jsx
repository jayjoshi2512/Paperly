import { useState } from "react";
import { useDocuments } from "../hooks/useDocuments";
import { Trash2, FileText, RefreshCw, FileType, AlertTriangle, X } from "lucide-react";
import styles from "./Documents.module.css";

function getFileExt(filename) {
  return (filename || "").split(".").pop().toLowerCase();
}

function DocIcon({ filename }) {
  const ext = getFileExt(filename);
  let cls = styles.default;
  if (ext === "pdf") cls = styles.pdf;
  else if (ext === "docx" || ext === "doc") cls = styles.docx;

  return (
    <div className={`${styles.docIcon} ${cls}`}>
      {ext === "pdf" ? <FileText size={18} /> : <FileType size={18} />}
    </div>
  );
}

export default function Documents() {
  const { documents, loading, loadDocuments, uploadDocument, deleteDocument } = useDocuments();
  const [docToDelete, setDocToDelete] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const confirmDelete = async () => {
    if (!docToDelete) return;
    try {
      await deleteDocument(docToDelete.id);
      setDocToDelete(null);
      setDeleteError(null);
    } catch (err) {
      setDeleteError(err.message);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Data Sources</h2>
        <button onClick={loadDocuments} className={styles.refreshBtn}>
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      <div className={styles.tableCard}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Document</th>
              <th>Status</th>
              <th>Strategy</th>
              <th>Chunks</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && documents.length === 0 && (
              <tr>
                <td colSpan="5" className={styles.emptyRow}>
                  Loading…
                </td>
              </tr>
            )}
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>
                  <div className={styles.docName}>
                    <DocIcon filename={doc.filename} />
                    <div className={styles.docMeta}>
                      <span className={styles.docFilename}>{doc.filename}</span>
                      <span className={styles.docSize}>
                        {(doc.file_size_bytes / 1024).toFixed(1)} KB · v{doc.version}
                      </span>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`${styles.badge} ${styles[doc.status] || ""}`}>
                    <span className={styles.badgeDot} />
                    {doc.status}
                  </span>
                </td>
                <td style={{ textTransform: "capitalize" }}>{doc.chunking_strategy}</td>
                <td>{doc.chunk_count || "—"}</td>
                <td className={styles.actionsCell}>
                  <button
                    onClick={() => setDocToDelete(doc)}
                    className={styles.deleteBtn}
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {!loading && documents.length === 0 && (
              <tr>
                <td colSpan="5" className={styles.emptyRow}>
                  <div className={styles.emptyContent}>
                    <FileText size={40} className={styles.emptyIcon} />
                    <p className={styles.emptyText}>
                      No documents yet. Upload a PDF or DOCX to get started.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {docToDelete && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                <AlertTriangle size={20} className={styles.modalIcon} />
                Confirm Deletion
              </div>
              <button onClick={() => setDocToDelete(null)} className={styles.closeBtn}>
                <X size={18} />
              </button>
            </div>
            <div className={styles.modalBody}>
              Are you sure you want to delete <strong>{docToDelete.filename}</strong>? This action cannot be undone.
              {deleteError && <div className={styles.modalError}>{deleteError}</div>}
            </div>
            <div className={styles.modalFooter}>
              <button onClick={() => setDocToDelete(null)} className={styles.cancelBtn}>Cancel</button>
              <button onClick={confirmDelete} className={styles.confirmBtn}>Delete Document</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
