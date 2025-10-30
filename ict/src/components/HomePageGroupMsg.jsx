// src/components/HomePageGroupMsg.jsx
import React, { useEffect, useState, useRef } from "react";
import { createSocket } from "../socket";

const HomePageGroupMsg = ({ token, user, group, onNewMessage }) => {
  const [messages, setMessages] = useState([]);
  const socketRef = useRef(null);

  useEffect(() => {
    if (!group) return;

    // Fetch group messages
    fetch(`http://localhost:5001/groupMessages/${group.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setMessages(Array.isArray(data) ? data : []))
      .catch((err) => console.error("Error fetching group messages:", err));
  }, [group, token]);

  useEffect(() => {
    const s = createSocket(token);
    socketRef.current = s;

    s.on("new_group_message", (msg) => {
      if (msg.group_id === group.id) {
        setMessages((prev) => [...prev, msg]);
        if (onNewMessage) onNewMessage(msg);
      }
    });

    return () => s.disconnect();
  }, [token, group, onNewMessage]);

  const handleSend = async (message) => {
    if (!message.trim()) return;

    const payload = {
      sender_id: user.id,
      group_id: group.id,
      message,
      message_type: "text",
    };

    socketRef.current.emit("send_group_message", payload);
    setMessages((prev) => [...prev, payload]);
  };

  return (
    <div className="flex flex-col flex-1 bg-white">
      <div className="p-4 border-b border-gray-300">
        <h2 className="font-semibold text-lg">{group.name}</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((msg, idx) => (
          <div key={idx} className="mb-3">
            <p className="text-sm text-gray-600">
              <strong>{msg.sender_name || "User"}:</strong> {msg.message}
            </p>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-gray-300 flex">
        <input
          type="text"
          placeholder="Type a message..."
          className="flex-1 border rounded-lg p-2 text-sm"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSend(e.target.value);
          }}
        />
      </div>
    </div>
  );
};

export default HomePageGroupMsg;
