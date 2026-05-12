import { useState, useEffect } from "react";
import { API_URL, getAuthToken, fetchApi } from "../api/client";

const PHASES = ["searching", "retrieving", "thinking", "answering"];

export const useStreamingChat = () => {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [phase, setPhase] = useState(null);

  useEffect(() => {
    async function loadHistory() {
      try {
        const history = await fetchApi("/chat/history");
        
        const grouped = {};
        for (const item of history) {
          const sid = item.session_id || "old-chats";
          if (!grouped[sid]) {
            grouped[sid] = {
              id: sid,
              createdAt: item.created_at,
              title: item.query_text.substring(0, 30) + (item.query_text.length > 30 ? "..." : ""),
              messages: []
            };
          }
          grouped[sid].messages.push({ role: "user", content: item.query_text });
          if (item.answer_text) {
            grouped[sid].messages.push({ role: "assistant", content: item.answer_text });
          }
        }
        
        const sessionList = Object.values(grouped).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        setSessions(sessionList);
        
      } catch (e) {
        console.error("Failed to load history", e);
      }
    }
    loadHistory();
  }, []);

  const currentMessages = currentSessionId 
    ? (sessions.find(s => s.id === currentSessionId)?.messages || [])
    : [];

  const startNewSession = () => {
    setCurrentSessionId(null);
  };

  const switchSession = (id) => {
    setCurrentSessionId(id);
  };

  const sendMessage = async (query) => {
    let activeSessionId = currentSessionId;
    let isNewSession = false;

    if (!activeSessionId) {
      activeSessionId = crypto.randomUUID();
      isNewSession = true;
      setCurrentSessionId(activeSessionId);
    }

    const userMsg = { role: "user", content: query };
    
    setSessions(prev => {
      if (isNewSession) {
        return [{
          id: activeSessionId,
          createdAt: new Date().toISOString(),
          title: query.substring(0, 30) + (query.length > 30 ? "..." : ""),
          messages: [userMsg, { role: "assistant", content: "" }]
        }, ...prev];
      } else {
        return prev.map(s => {
          if (s.id === activeSessionId) {
            return { ...s, messages: [...s.messages, userMsg, { role: "assistant", content: "" }] };
          }
          return s;
        });
      }
    });

    setIsStreaming(true);
    setPhase("searching");

    try {
      const phaseTimer1 = setTimeout(() => setPhase("retrieving"), 600);
      const phaseTimer2 = setTimeout(() => setPhase("thinking"), 1400);

      const response = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ query, session_id: activeSessionId }),
      });

      clearTimeout(phaseTimer1);
      clearTimeout(phaseTimer2);

      if (!response.ok) throw new Error("Stream failed");

      setPhase("answering");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          for (const line of part.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const dataStr = line.slice(6).trim();
            if (dataStr === "[DONE]") break;
            try {
              const data = JSON.parse(dataStr);
              if (data.token) {
                setSessions((prev) => {
                  return prev.map(s => {
                    if (s.id === activeSessionId) {
                      const newMsgs = [...s.messages];
                      newMsgs[newMsgs.length - 1] = {
                        ...newMsgs[newMsgs.length - 1],
                        content: newMsgs[newMsgs.length - 1].content + data.token,
                      };
                      return { ...s, messages: newMsgs };
                    }
                    return s;
                  });
                });
              }
            } catch {
              // ignore malformed JSON
            }
          }
        }
      }
    } catch (e) {
      console.error(e);
      setSessions((prev) => {
        return prev.map(s => {
          if (s.id === activeSessionId) {
            const newMsgs = [...s.messages];
            newMsgs[newMsgs.length - 1] = {
              ...newMsgs[newMsgs.length - 1],
              content: "Something went wrong. Please check your connection and try again.",
            };
            return { ...s, messages: newMsgs };
          }
          return s;
        });
      });
    } finally {
      setIsStreaming(false);
      setPhase(null);
    }
  };

  return { 
    sessions, 
    currentSessionId, 
    messages: currentMessages, 
    isStreaming, 
    phase, 
    sendMessage, 
    startNewSession, 
    switchSession, 
    PHASES 
  };
};
