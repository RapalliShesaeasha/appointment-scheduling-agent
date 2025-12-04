import React, { useState } from "react";
import axios from "axios";
import AppointmentConfirmation from "./AppointmentConfirmation";

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    { from: "bot", text: "Hello — I’m here to help you schedule appointments. How can I help today?" }
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [confirmation, setConfirmation] = useState(null);

  async function sendMessage() {
    if (!input.trim()) return;
    const userText = input.trim();
    setMessages(m => [...m, { from: "user", text: userText }]);
    setInput("");
    try {
      const resp = await axios.post("http://127.0.0.1:8000/api/chat", { message: userText, session_id: sessionId });
      const { session_id, result } = resp.data;
      setSessionId(session_id);
      setMessages(m => [...m, { from: "bot", text: result.response }]);
      if (result.type === "confirmation") {
        setConfirmation(result.response);
      }
    } catch (err) {
      setMessages(m => [...m, { from: "bot", text: "Error contacting server." }]);
    }
  }

  return (
    <div>
      <div style={{ border: "1px solid #ddd", padding: 12, minHeight: 320, background: "#fff" }}>
        {messages.map((m, i) => (
          <div key={i} style={{ margin: "8px 0", textAlign: m.from === "user" ? "right" : "left" }}>
            <div style={{ display: "inline-block", padding: "8px 12px", borderRadius: 12, background: m.from === "user" ? "#DCF8C6" : "#F1F0F0" }}>
              {m.text}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
        <input value={input} onChange={e => setInput(e.target.value)} style={{ flex: 1, padding: 8 }} placeholder="Type message..." />
        <button onClick={sendMessage}>Send</button>
      </div>

      {confirmation && <AppointmentConfirmation text={confirmation} />}
    </div>
  );
}
