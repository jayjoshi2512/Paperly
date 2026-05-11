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

      let done = false;
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.slice(6);
              if (dataStr === "[DONE]") {
                done = true;
                break;
              }
              try {
                const data = JSON.parse(dataStr);
                setMessages((prev) => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content += data.token;
                  return newMsgs;
                });
              } catch (e) {
                // ignore JSON parse error
              }
            }
          }
        }
      }
    } catch (e) {
      console.error(e);
      setMessages((prev) => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1].content = "Error: Failed to fetch response.";
        return newMsgs;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return { messages, isStreaming, sendMessage };
};
