import React from "react";

export default function AppointmentConfirmation({ text }) {
  return (
    <div style={{ marginTop: 16, padding: 12, border: "1px solid #cfc", background: "#f7fff6" }}>
      <h3>Booking Confirmation</h3>
      <p>{text}</p>
    </div>
  );
}
