import { useState } from "react";
import { API_URL, getAuthToken } from "../api/client";

const PHASES = ["searching", "retrieving", "thinking", "answering"];

export const useStreamingChat = () => {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [phase, setPhase] = useState(null); // current pipeline phase

  const sendMessage = async (query) => {
    const userMsg = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "" }]);
    setIsStreaming(true);
    setPhase("searching");

    try {
      // Simulate phase progression during network request
      const phaseTimer1 = setTimeout(() => setPhase("retrieving"), 600);
      const phaseTimer2 = setTimeout(() => setPhase("thinking"), 1400);

      const response = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ query }),
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
                setMessages((prev) => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1] = {
                    ...newMsgs[newMsgs.length - 1],
                    content: newMsgs[newMsgs.length - 1].content + data.token,
                  };
                  return newMsgs;
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
      setMessages((prev) => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1] = {
          ...newMsgs[newMsgs.length - 1],
          content: "Something went wrong. Please check your connection and try again.",
        };
        return newMsgs;
      });
    } finally {
      setIsStreaming(false);
      setPhase(null);
    }
  };

  return { messages, isStreaming, phase, sendMessage, PHASES };
};
