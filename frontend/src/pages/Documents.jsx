import { useState } from "react";
import { useDocuments } from "../hooks/useDocuments";
import { Upload, Trash2, FileText, RefreshCw, FileType } from "lucide-react";
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
  const [file, setFile] = useState(null);
  const [strategy, setStrategy] = useState("recursive");
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file, strategy);
      setFile(null);
      document.getElementById("file-upload").value = "";
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Knowledge Base</h2>
        <button onClick={loadDocuments} className={styles.refreshBtn}>
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      <div className={styles.uploadCard}>
        <h3 className={styles.uploadTitle}>Upload Document</h3>
        <form onSubmit={handleUpload} className={styles.uploadForm}>
          <div className={styles.fieldGroup}>
            <label className={styles.fieldLabel}>File (PDF or DOCX)</label>
            <input
              id="file-upload"
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setFile(e.target.files[0])}
              className={styles.fileInput}
            />
          </div>
          <div className={styles.fieldGroup} style={{ maxWidth: 200 }}>
            <label className={styles.fieldLabel}>Chunking</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className={styles.select}
            >
              <option value="recursive">Recursive</option>
              <option value="fixed">Fixed Size</option>
              <option value="semantic">Semantic</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={!file || uploading}
            className={styles.uploadBtn}
          >
            {uploading ? (
              <RefreshCw size={16} className={styles.spinner} />
            ) : (
              <Upload size={16} />
            )}
            <span>{uploading ? "Uploading…" : "Upload"}</span>
          </button>
        </form>
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
                    onClick={async () => {
                      if (!window.confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
                      try {
                        await deleteDocument(doc.id);
                      } catch (err) {
                        alert("Delete failed: " + err.message);
                      }
                    }}
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
    </div>
  );
}
