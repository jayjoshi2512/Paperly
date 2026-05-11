import { useState, useRef, useEffect } from "react";
import { useStreamingChat } from "../hooks/useStreamingChat";
import { Send, Bot, User } from "lucide-react";
import Markdown from "react-markdown";

export default function Chat() {
  const { messages, isStreaming, sendMessage } = useStreamingChat();
  const [input, setInput] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <div className="flex flex-col h-full bg-white relative">
      <div className="p-4 border-b flex items-center justify-between shadow-sm z-10 bg-white">
        <h2 className="text-lg font-semibold text-gray-800">Chat Assistant</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-4">
            <div className="bg-blue-50 p-4 rounded-full text-blue-500">
              <Bot size={40} />
            </div>
            <h3 className="text-xl font-medium text-gray-700">How can I help you today?</h3>
            <p className="text-center max-w-md">
              Ask me questions about the documents uploaded to your workspace. I will search the knowledge base and provide an answer with citations.
            </p>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`flex space-x-3 max-w-3xl ${msg.role === "user" ? "flex-row-reverse space-x-reverse" : "flex-row"}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${msg.role === "user" ? "bg-blue-100 text-blue-600" : "bg-purple-100 text-purple-600"}`}>
                {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div className={`p-4 rounded-2xl ${msg.role === "user" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-800"}`}>
                {msg.role === "user" ? (
                  msg.content
                ) : (
                  <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-gray-800 prose-pre:text-gray-100">
                    <Markdown>
                      {msg.content}
                    </Markdown>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="p-4 bg-white border-t">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSend} className="relative flex items-center">
            <input
              type="text"
              className="w-full border-2 border-gray-200 p-4 pr-14 rounded-full focus:outline-none focus:border-blue-500 transition-colors shadow-sm"
              placeholder="Ask a question about your documents..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isStreaming}
            />
            <button
              type="submit"
              className="absolute right-2 bg-blue-600 text-white p-2.5 rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isStreaming || !input.trim()}
            >
              <Send size={18} className={isStreaming ? "animate-pulse" : ""} />
            </button>
          </form>
          <div className="text-center mt-2 text-xs text-gray-400">
            Paperly can make mistakes. Consider verifying important information.
          </div>
        </div>
      </div>
    </div>
  );
}
