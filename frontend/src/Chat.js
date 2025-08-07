import React, { useState, useRef, useEffect } from "react";
import styles from "./Chat.module.css";

const API_BASE_URL = process.env.NODE_ENV === "development" ? "http://localhost:8000" : "";

const AVATARS = {
  user: "/logo192.png",
  bot: "/logo512.png"
};

const NAMES = {
  user: "You",
  bot: "Acme Chatbot"
};

function Loader3D() {
  return (
    <div className={styles.loader3d}>
      <div className={styles.cube3d}>
        <div className={styles.face + ' ' + styles.front}></div>
        <div className={styles.face + ' ' + styles.back}></div>
        <div className={styles.face + ' ' + styles.right}></div>
        <div className={styles.face + ' ' + styles.left}></div>
        <div className={styles.face + ' ' + styles.top}></div>
        <div className={styles.face + ' ' + styles.bottom}></div>
      </div>
    </div>
  );
}

const Chat = () => {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello! How can I help you today?", timestamp: new Date().toISOString() },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedIdx, setCopiedIdx] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    setError(null);
    const userMessage = { sender: "user", text: input, timestamp: new Date().toISOString() };
    setMessages((msgs) => [...msgs, userMessage]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: userMessage.text })
      });
      const data = await res.json();
      if (res.ok) {
        setMessages((msgs) => [
          ...msgs,
          { sender: "bot", text: data.reply || data.message || "(No response)", timestamp: new Date().toISOString() },
        ]);
      } else {
        setMessages((msgs) => [
          ...msgs,
          { sender: "bot", text: data.error || "Error from server.", timestamp: new Date().toISOString() },
        ]);
      }
    } catch (err) {
      setMessages((msgs) => [
        ...msgs,
        { sender: "bot", text: "Network error. Please try again.", timestamp: new Date().toISOString() },
      ]);
    }
    setLoading(false);
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1200);
  };

  return (
    <div className={styles.claudeChatContainer}>
      <div className={styles.messages}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={
              msg.sender === "user"
                ? styles.userMessage
                : styles.botMessage
            }
            onMouseLeave={() => setCopiedIdx(null)}
            tabIndex={0}
            aria-label={`${NAMES[msg.sender]}: ${msg.text}`}
          >
            <div className={styles.messageHeader}>
              <img src={AVATARS[msg.sender]} alt={msg.sender} className={styles.avatar} />
              <span className={styles.senderName}>{NAMES[msg.sender]}</span>
              <span className={styles.timestamp}>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              <button
                className={styles.copyBtn}
                onClick={() => handleCopy(msg.text, idx)}
                title="Copy message"
                type="button"
                aria-label="Copy message"
              >
                {copiedIdx === idx ? "Copied!" : "Copy"}
              </button>
            </div>
            <div className={styles.messageText}>{msg.text}</div>
          </div>
        ))}
        {loading && <Loader3D />}
        <div ref={messagesEndRef} />
      </div>
      <form className={styles.inputForm} onSubmit={handleSend} autoComplete="off">
        <input
          className={styles.inputBox}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={loading ? "Waiting for response..." : "Type your message..."}
          disabled={loading}
          aria-label="Type your message"
        />
        <button className={styles.sendButton} type="submit" disabled={loading || !input.trim()} aria-label="Send message">
          {loading ? "..." : "Send"}
        </button>
      </form>
      {error && <div style={{ color: 'red', textAlign: 'center', marginTop: 8 }}>{error}</div>}
    </div>
  );
};

export default Chat; 