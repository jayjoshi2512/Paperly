import { useState } from "react";
import { API_URL, getAuthToken } from "../api/client";

export const useStreamingChat = () => {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = async (query) => {
    const userMsg = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "" }]);
    setIsStreaming(true);

    try {
      const response = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) throw new Error("Stream failed");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      // SSE buffer: accumulate bytes until we have complete lines
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        // Append new bytes to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process all complete SSE messages (separated by \n\n)
        const parts = buffer.split("\n\n");
        // The last part may be incomplete — keep it in the buffer
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
          content: "Error: Failed to fetch response. Please try again.",
        };
        return newMsgs;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return { messages, isStreaming, sendMessage };
};
