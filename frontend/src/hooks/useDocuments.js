import { useState, useEffect, useCallback } from "react";
import { fetchApi } from "../api/client";

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

  const uploadDocument = async (file, strategy = "recursive") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("strategy", strategy);

    const doc = await fetchApi("/docs/upload", {
      method: "POST",
      body: formData,
    });
    setDocuments((prev) => [doc, ...prev]);
    return doc;
  };

  const deleteDocument = async (id) => {
    await fetchApi(`/docs/${id}`, { method: "DELETE" });
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  return { documents, loading, loadDocuments, uploadDocument, deleteDocument };
};
