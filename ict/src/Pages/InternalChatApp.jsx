import React, { useState } from "react";
import {
  Send,
  Paperclip,
  Search,
  Users,
  Hash,
  MoreVertical,
  Plus,
  Phone,
  Video,
  Smile,
  File,
  Image as ImageIcon,
} from "lucide-react";

export default function InternalChatApp() {
  const [activeChat, setActiveChat] = useState("sarah-chen");
  const [message, setMessage] = useState("");
  const [showFileMenu, setShowFileMenu] = useState(false);

  const chats = [
    {
      id: "sarah-chen",
      name: "Sarah Chen",
      type: "dm",
      avatar: "SC",
      status: "online",
      lastMessage: "Sounds good! Let me know if you need...",
      time: "2m",
      unread: 0,
    },
    {
      id: "design-team",
      name: "Design Team",
      type: "group",
      avatar: "🎨",
      lastMessage: "Alex: Updated the mockups",
      time: "15m",
      unread: 3,
    },
    {
      id: "marcus-lee",
      name: "Marcus Lee",
      type: "dm",
      avatar: "ML",
      status: "away",
      lastMessage: "Can we schedule a call tomorrow?",
      time: "1h",
      unread: 1,
    },
    {
      id: "product-updates",
      name: "Product Updates",
      type: "group",
      avatar: "📢",
      lastMessage: "New feature deployed to staging",
      time: "2h",
      unread: 0,
    },
    {
      id: "engineering",
      name: "Engineering",
      type: "group",
      avatar: "⚡",
      lastMessage: "Maya: Fixed the database issue",
      time: "3h",
      unread: 0,
    },
    {
      id: "emma-wilson",
      name: "Emma Wilson",
      type: "dm",
      avatar: "EW",
      status: "offline",
      lastMessage: "Thanks for the update!",
      time: "Yesterday",
      unread: 0,
    },
  ];

  const messages = [
    {
      id: 1,
      sender: "Sarah Chen",
      avatar: "SC",
      content: "Hey! Did you get a chance to review the latest designs?",
      time: "10:30 AM",
      isMine: false,
    },
    {
      id: 2,
      sender: "You",
      content:
        "Yes, just finished looking through them. Really impressed with the direction!",
      time: "10:32 AM",
      isMine: true,
    },
    {
      id: 3,
      sender: "Sarah Chen",
      avatar: "SC",
      content: "Awesome! Any feedback on the color scheme?",
      time: "10:33 AM",
      isMine: false,
    },
    {
      id: 4,
      sender: "You",
      content:
        "I think the blues work well. Maybe we could test a warmer accent color?",
      time: "10:35 AM",
      isMine: true,
    },
    {
      id: 5,
      sender: "You",
      content: "Something like an orange or coral",
      time: "10:35 AM",
      isMine: true,
    },
    {
      id: 6,
      sender: "Sarah Chen",
      avatar: "SC",
      content: "Great idea! Let me mock up a few variations",
      time: "10:37 AM",
      isMine: false,
      file: { name: "color-variations.fig", type: "figma", size: "2.4 MB" },
    },
    {
      id: 7,
      sender: "You",
      content: "Perfect! Looking forward to seeing them",
      time: "10:38 AM",
      isMine: true,
    },
  ];

  const currentChat = chats.find((c) => c.id === activeChat);

  const handleSend = () => {
    if (message.trim()) {
      setMessage("");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Sidebar */}
      <div className="w-20 bg-indigo-600 flex flex-col items-center py-4 space-y-6">
        <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center font-bold text-indigo-600 text-xl">
          C
        </div>
        <div className="flex-1 flex flex-col items-center space-y-4">
          <button className="w-12 h-12 bg-indigo-500 rounded-xl flex items-center justify-center hover:bg-indigo-400 transition-colors">
            <Hash className="w-6 h-6 text-white" />
          </button>
          <button className="w-12 h-12 rounded-xl flex items-center justify-center hover:bg-indigo-500 transition-colors">
            <Users className="w-6 h-6 text-indigo-200" />
          </button>
        </div>
        <button className="w-12 h-12 rounded-full bg-indigo-800 flex items-center justify-center text-white font-semibold">
          JD
        </button>
      </div>

      {/* Chat List */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Messages</h2>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <Plus className="w-5 h-5 text-gray-600" />
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search messages..."
              className="w-full pl-10 pr-4 py-2 bg-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {chats.map((chat) => (
            <button
              key={chat.id}
              onClick={() => setActiveChat(chat.id)}
              className={`w-full p-4 flex items-start space-x-3 hover:bg-gray-50 transition-colors ${
                activeChat === chat.id ? "bg-indigo-50" : ""
              }`}
            >
              <div className="relative flex-shrink-0">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center text-lg font-semibold ${
                    chat.type === "group"
                      ? "bg-gray-100"
                      : "bg-gradient-to-br from-indigo-400 to-purple-400 text-white"
                  }`}
                >
                  {chat.avatar}
                </div>
                {chat.type === "dm" && chat.status === "online" && (
                  <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                )}
              </div>
              <div className="flex-1 min-w-0 text-left">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-semibold text-gray-900 truncate">
                    {chat.name}
                  </h3>
                  <span className="text-xs text-gray-500 ml-2">
                    {chat.time}
                  </span>
                </div>
                <p className="text-sm text-gray-600 truncate">
                  {chat.lastMessage}
                </p>
              </div>
              {chat.unread > 0 && (
                <div className="flex-shrink-0 w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center text-xs text-white font-semibold">
                  {chat.unread}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-semibold ${
                  currentChat?.type === "group"
                    ? "bg-gray-100"
                    : "bg-gradient-to-br from-indigo-400 to-purple-400 text-white"
                }`}
              >
                {currentChat?.avatar}
              </div>
              {currentChat?.type === "dm" &&
                currentChat?.status === "online" && (
                  <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                )}
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">
                {currentChat?.name}
              </h2>
              <p className="text-sm text-gray-500">
                {currentChat?.type === "dm"
                  ? currentChat?.status
                  : "12 members"}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <Phone className="w-5 h-5 text-gray-600" />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <Video className="w-5 h-5 text-gray-600" />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <MoreVertical className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.isMine ? "justify-end" : "justify-start"}`}
            >
              {!msg.isMine && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-400 to-purple-400 text-white flex items-center justify-center text-xs font-semibold mr-3 flex-shrink-0">
                  {msg.avatar}
                </div>
              )}
              <div
                className={`max-w-md flex flex-col ${
                  msg.isMine ? "items-end" : "items-start"
                }`}
              >
                {!msg.isMine && (
                  <span className="text-xs font-medium text-gray-700 mb-1">
                    {msg.sender}
                  </span>
                )}
                <div
                  className={`px-4 py-2 rounded-2xl ${
                    msg.isMine
                      ? "bg-indigo-600 text-white rounded-br-sm"
                      : "bg-gray-100 text-gray-900 rounded-bl-sm"
                  }`}
                >
                  <p className="text-sm">{msg.content}</p>
                  {msg.file && (
                    <div
                      className={`mt-2 p-3 rounded-lg flex items-center space-x-3 ${
                        msg.isMine ? "bg-indigo-700" : "bg-white"
                      }`}
                    >
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          msg.isMine ? "bg-indigo-800" : "bg-indigo-100"
                        }`}
                      >
                        <File
                          className={`w-5 h-5 ${
                            msg.isMine ? "text-indigo-200" : "text-indigo-600"
                          }`}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p
                          className={`text-sm font-medium truncate ${
                            msg.isMine ? "text-white" : "text-gray-900"
                          }`}
                        >
                          {msg.file.name}
                        </p>
                        <p
                          className={`text-xs ${
                            msg.isMine ? "text-indigo-200" : "text-gray-500"
                          }`}
                        >
                          {msg.file.size}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
                <span className="text-xs text-gray-500 mt-1">{msg.time}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Message Input */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-end space-x-3">
            <div className="flex-1 bg-gray-100 rounded-2xl px-4 py-3 focus-within:ring-2 focus-within:ring-indigo-500">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type a message..."
                rows="1"
                className="w-full bg-transparent resize-none focus:outline-none text-gray-900 placeholder-gray-500"
              />
              <div className="flex items-center space-x-2 mt-2">
                <div className="relative">
                  <button
                    onClick={() => setShowFileMenu(!showFileMenu)}
                    className="p-1 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    <Paperclip className="w-5 h-5 text-gray-600" />
                  </button>
                  {showFileMenu && (
                    <div className="absolute bottom-full left-0 mb-2 bg-white rounded-xl shadow-lg border border-gray-200 py-2 w-48">
                      <button className="w-full px-4 py-2 flex items-center space-x-3 hover:bg-gray-50 transition-colors text-left">
                        <ImageIcon className="w-5 h-5 text-indigo-600" />
                        <span className="text-sm text-gray-700">
                          Upload Image
                        </span>
                      </button>
                      <button className="w-full px-4 py-2 flex items-center space-x-3 hover:bg-gray-50 transition-colors text-left">
                        <File className="w-5 h-5 text-indigo-600" />
                        <span className="text-sm text-gray-700">
                          Upload File
                        </span>
                      </button>
                    </div>
                  )}
                </div>
                <button className="p-1 hover:bg-gray-200 rounded-lg transition-colors">
                  <Smile className="w-5 h-5 text-gray-600" />
                </button>
              </div>
            </div>
            <button
              onClick={handleSend}
              className="w-12 h-12 bg-indigo-600 hover:bg-indigo-700 rounded-xl flex items-center justify-center transition-colors flex-shrink-0"
            >
              <Send className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
