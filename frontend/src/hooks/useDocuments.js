import { useState, useEffect, useCallback } from "react";
import { fetchApi, API_URL, getAuthToken } from "../api/client";

export const useDocuments = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchApi("/docs/");
      setDocuments(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  /**
   * Upload a single document. Returns immediately with { document_id, filename, status }.
   * The caller should use pollDocumentStatus() to track progress.
   */
  const uploadDocument = async (file, strategy = "recursive") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("strategy", strategy);

    const response = await fetch(`${API_URL}/docs/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${getAuthToken()}` },
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed");
    }

    // 202 Accepted — returns { document_id, filename, status, message }
    return await response.json();
  };

  /**
   * Upload multiple files at once via POST /docs/upload/batch.
   * Returns { accepted: [...], rejected: [...], total_accepted, total_rejected }.
   */
  const uploadBatch = async (files, strategy = "recursive") => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    formData.append("strategy", strategy);

    const response = await fetch(`${API_URL}/docs/upload/batch`, {
      method: "POST",
      headers: { Authorization: `Bearer ${getAuthToken()}` },
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Batch upload failed");
    }

    return await response.json(); // { accepted, rejected, total_accepted, total_rejected }
  };

  /**
   * Poll GET /docs/{documentId}/status every 2 seconds.
   * Calls onUpdate({ progress_pct, progress_message }) on each tick.
   * Calls onComplete() when status === "ready".
   * Calls onError(message) when status === "failed".
   * Returns a stop() function to cancel polling.
   */
  const pollDocumentStatus = (documentId, { onUpdate, onComplete, onError }) => {
    const intervalId = setInterval(async () => {
      try {
        const status = await fetchApi(`/docs/${documentId}/status`);
        if (onUpdate) onUpdate(status);

        if (status.status === "ready") {
          clearInterval(intervalId);
          if (onComplete) onComplete(status);
          // Refresh document list so the new doc appears
          loadDocuments();
        } else if (status.status === "failed") {
          clearInterval(intervalId);
          if (onError) onError(status.progress_message || "Processing failed");
        }
      } catch (e) {
        clearInterval(intervalId);
        if (onError) onError(e.message);
      }
    }, 2000);

    return () => clearInterval(intervalId);
  };

  const deleteDocument = async (id) => {
    await fetchApi(`/docs/${id}`, { method: "DELETE" });
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  return { documents, loading, loadDocuments, uploadDocument, uploadBatch, pollDocumentStatus, deleteDocument };
};
