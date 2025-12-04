import React from "react";
import ChatInterface from "./components/ChatInterface";

export default function App() {
  return (
    <div style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "Arial, sans-serif" }}>
      <h1>HealthCare Plus — Appointment Assistant</h1>
      <ChatInterface />
    </div>
  );
}
