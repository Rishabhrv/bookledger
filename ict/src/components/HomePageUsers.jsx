import React, { useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faThumbtack, faFile, faImage } from "@fortawesome/free-solid-svg-icons";
import {  Search, MessagesSquare  } from "lucide-react";

const HomePageUsers = ({ token, onSelectConversation, user, lastMessageUpdate }) => {
  const [convos, setConvos] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeChat, setActiveChat] = useState(null);
  const [showAllUsers, setShowAllUsers] = useState(false);


  // 🔹 Fetch existing conversations
  useEffect(() => {
    fetch("https://auth.agkit.in/conversations", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setConvos(data.map((c) => ({ ...c, hasConversation: true })));
        } else {
          setConvos([]);
        }
      })
      .catch((err) => console.error("Error fetching conversations:", err));
  }, [token, lastMessageUpdate]);

  // 🔹 Handle search
  useEffect(() => {
    if (!searchTerm.trim()) {
      setSearchResults([]);
      return;
    }

    setLoading(true);
    const timer = setTimeout(() => {
      fetch(`https://auth.agkit.in/users?search=${encodeURIComponent(searchTerm)}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((data) => {
          const userList = Array.isArray(data) ? data : [];
          const existingUsernames = new Set(convos.map((c) => c.other_username));
          const results = userList.map((u) => ({
            ...u,
            hasConversation: existingUsernames.has(u.username),
          }));
          setSearchResults(results);
        })
        .catch((err) => console.error("Search error:", err))
        .finally(() => setLoading(false));
    }, 400);

    return () => clearTimeout(timer);
  }, [searchTerm, convos, token]);

  const listToShow = showAllUsers
  ? searchResults
  : searchTerm
  ? searchResults
  : convos;

  // 🔹 Create new conversation
  const createConversation = async (otherUserId) => {
    try {
      const res = await fetch("https://auth.agkit.in/createConversation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user1_id: user.id,
          user2_id: otherUserId,
        }),
      });

      const data = await res.json();
      if (data.success) {
        alert("Conversation created!");
        setConvos((prev) => [...prev, { ...data.conversation, hasConversation: true }]);
        setSearchTerm("");
        onSelectConversation(data.conversation);
        window.location.reload();
      } else {
        alert("Failed to create conversation.");
      }
    } catch (err) {
      console.error("Error creating conversation:", err);
    }
  };

const timeAgo = (dateString) => {
  if (!dateString) return "";

  // Get IST current time
  const now = new Date();
  const nowIST = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));

  // Parse message time (already IST in your backend)
  const messageTime = new Date(dateString);

  const diffMs = nowIST - messageTime;
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return "just now";
  if (diffMinutes < 60) return `${diffMinutes} min${diffMinutes > 1 ? "s" : ""}`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""}`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""}`;

  return messageTime.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
};



  return (
    <div className="w-80 min-w-90 bg-white border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 pt-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{user.username}</h2>
          </div>
          <div className="flex">
            {/* <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
            <Plus className="w-5 h-5 text-gray-600" />
          </button> */}
          <button
  onClick={async () => {
    setLoading(true);
    setShowAllUsers(true); // ✅ tell component to show all users
    try {
      const res = await fetch(`https://auth.agkit.in/all_users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      const userList = Array.isArray(data) ? data : [];

      // Tag them as "no conversation"
      const existingUsernames = new Set(convos.map((c) => c.other_username));
      const result = userList.map((u) => ({
        ...u,
        hasConversation: existingUsernames.has(u.username),
      }));

      setSearchResults(result);
      setSearchTerm(""); // clear search bar
    } catch (err) {
      console.error("Error fetching all users:", err);
    } finally {
      setLoading(false);
    }
  }}
  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
  title="Show all users"
>
  <MessagesSquare className="w-5 h-5 text-gray-600" />
</button>

          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search messages..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#f37c7c]"
          />
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {loading && <div className="p-4 text-gray-500">Searching...</div>}

        {Array.isArray(listToShow) && listToShow.length > 0 ? (
          listToShow.map((c) => {
            const name = c.other_username || c.username || "Unknown";
            const avatarLetter = name.charAt(0).toUpperCase();
            const isActive = activeChat === (c.id || c.user_id);

            return (
              <button
                key={c.id || c.user_id}
                onClick={() => {
                                  console.log(c);
                  if (c.hasConversation) {
                    const convo = convos.find(
                      (conv) =>
                        conv.other_username === c.username ||
                        conv.other_user_id === c.id
                    );
                    if (convo) {
                      onSelectConversation(convo);
                      setActiveChat(c.id || c.user_id);
                    } else {
                      onSelectConversation(c);
                      setActiveChat(c.id || c.user_id);
                    }
                  }
                }}
                className={`w-full p-4 flex items-start space-x-3 hover:bg-red-50 transition-colors ${
                  isActive ? "bg-red-50" : ""
                }`}
              >
                {/* Avatar */}
                <div className="relative flex-shrink-0">
                  <div
                    className={`w-12 h-12 rounded-xl flex items-center justify-center text-lg font-semibold ${
                      c.type === "group"
                        ? "bg-gray-100 text-gray-600"
                        : "bg-gradient-to-br from-[#f37c7c] to-[#ef6061] text-white"
                    }`}
                  >
                    {avatarLetter}
                  </div>
                  {c.status === "online" && (
                    <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                  )}
                </div>

                {/* Chat Info */}
                <div className="flex-1 min-w-0 text-left">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-semibold text-gray-900 truncate">{name}</h3>
                    <span className="text-xs text-gray-500 ml-2">{timeAgo(c.last_time)}</span>
                  </div>

                  <p className="text-sm text-gray-600 truncate flex items-center gap-1">
                    {(() => {
                      if (!c.last_message) return c.email || "No messages yet";
                      if (c.last_message_type === "text") return c.last_message;
                      if (c.last_message_type === "file") {
                        const fileName = c.last_message.split("/").pop();
                        return (
                          <>
                            <FontAwesomeIcon icon={faFile} className="text-gray-400" />
                            <span className="truncate max-w-[150px]">{fileName}</span>
                          </>
                        );
                      }
                      if (c.last_message_type === "image") {
                        const fileName = c.last_message.split("/").pop();
                        return (
                          <>
                            <FontAwesomeIcon icon={faImage} className="text-gray-400" />
                            <span className="truncate max-w-[150px]">{fileName}</span>
                          </>
                        );
                      }
                      return c.last_message;
                    })()}
                  </p>
                </div>

                {/* Unread or New chat */}
                {!c.hasConversation ? (
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      createConversation(c.id);
                    }}
                    className="text-yellow-500 hover:text-gray-500"
                    title="Start Conversation"
                  >
                    <FontAwesomeIcon icon={faThumbtack} />
                  </div>
                ) : (
                  c.unread > 0 && (
                    <div className="flex-shrink-0 w-5 h-5 bgcolor-500 rounded-full flex items-center justify-center text-xs text-white font-semibold">
                      {c.unread}
                    </div>
                  )
                )}
              </button>
            );
          })
        ) : (
          !loading && <div className="p-4 text-gray-500 text-sm">No users found</div>
        )}
      </div>
    </div>
  );
};

export default HomePageUsers;
