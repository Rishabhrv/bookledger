import React, { useState, useEffect } from "react";
import Slidebar from "../components/Slidebar";
import HomePageUsers from "../components/HomePageUsers";
import HomePageMsg from "../components/HomePageMsg";
import '../css/SlideBar.css'
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRightFromBracket } from "@fortawesome/free-solid-svg-icons";

const FLASK_AUTH_URL = process.env.REACT_APP_FLASK_AUTH_URL;
const FLASK_LOGIN_URL = process.env.REACT_APP_FLASK_LOGIN_URL;

// ✅ Allowed roles and apps
const VALID_ROLES = ["admin", "user"];
const VALID_APPS = {
  Main: "main",
  Operations: "operations",
  IJISEM: "ijisem",
  Tasks: "tasks",
  Sales: "sales",
  Clone: "clone",
};

const VALID_ACCESS = {
  // Loop buttons (table)
  "ISBN": "manage_isbn_dialog",
  "Payment": "manage_price_dialog",
  "Authors": "edit_author_dialog",
  "Operations": "edit_operation_dialog",
  "Printing & Delivery": "edit_inventory_delivery_dialog",
  "DatadashBoard": "datadashoard",
  "Advance Search": "advance_search",
  "Team Dashboard": "team_dashboard",
  "Print Management": "print_management",
  "Inventory": "inventory",
  "Open Author Positions": "open_author_positions",
  "Pending Work": "pending_books",
  "IJISEM": "ijisem",
  "Tasks": "tasks",
  "Details": "details",
  "Message": "messages",
  // Non-loop buttons
  "Add Book": "add_book_dialog",
  "Authors Edit": "edit_author_detail"
};




const HomePage = () => {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [selectedConv, setSelectedConv] = useState(null);
  const [lastMessageUpdate, setLastMessageUpdate] = useState(null);
  const [isValidating, setIsValidating] = useState(true);
  const [popupMsg, setPopupMsg] = useState(""); // ✅ popup message state

  // ✅ Custom popup function
  const showPopup = (message) => {
  setPopupMsg(message);
};

// ✅ Helper to redirect to login
const redirectToLogin = (message) => {
  console.warn("Redirecting:", message);
  localStorage.removeItem("token");
  showPopup(message || "Authentication failed. Please log in again.");
};



// ✅ Decode JWT (client-side)
const decodeJWT = (token) => {
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error("JWT decode error:", e);
    return null;
  }
};

// ✅ Token expiry check — uses JWT exp (UTC-based)
const checkTokenExpiry = (token) => {
  const payload = decodeJWT(token);
  if (!payload || !payload.exp) {
    redirectToLogin("Invalid token structure.");
    return true;
  }

  // ✅ Compare UTC times directly (both in milliseconds)
  const nowUTC = Date.now();
  const expUTC = payload.exp * 1000;

  if (nowUTC > expUTC) {
    const expTime = new Date(expUTC).toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
    });
    console.log(`Token expired at ${expTime} IST`);
    redirectToLogin("Token expired. Please log in again.");
    return true;
  }

  return false;
};

  // ✅ Main token + user validation logic
  const validateToken = async (activeToken) => {
    try {
      const res = await fetch(FLASK_AUTH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: activeToken }),
      });

      if (!res.ok) {
        redirectToLogin("Authentication server not reachable.");
        return;
      }

      const data = await res.json();
      if (!data.valid) {
        redirectToLogin(`Invalid token: ${data.error || "Unknown error"}`);
        return;
      }

      // ✅ Extract user details
      const userDetails = data.user_details || {};
      const role = (userDetails.role || "").toLowerCase();
      const app = (userDetails.app || "").toLowerCase();
      let access = userDetails.access || [];
      if (typeof access === "string") access = access ? [access] : [];

      // ✅ Role validation
      if (!VALID_ROLES.includes(role)) {
        redirectToLogin(`Access denied: Invalid role '${role}'.`);
        return;
      }

      // ✅ App validation (non-admin only)
      if (role !== "admin") {
        const validApps = Object.values(VALID_APPS);
        if (!validApps.includes(app)) {
          redirectToLogin(`Access denied: Invalid app '${app}'.`);
          return;
        }

        // ✅ App-specific access validation
        if (app === "main") {
          if (!access.every((a) => Object.keys(VALID_ACCESS).includes(a))) {
            redirectToLogin(`Invalid access for main app: ${access.join(", ")}`);
            return;
          }
        } else if (app === "operations") {
          const VALID_OPERATIONS_ACCESS = [
            "writer",
            "proofreader",
            "formatter",
            "cover_designer",
          ];
          if (!(access.length === 1 && VALID_OPERATIONS_ACCESS.includes(access[0]))) {
            redirectToLogin(`Invalid access for operations app: ${access.join(", ")}`);
            return;
          }
        } else if (app === "ijisem") {
          if (!(access.length === 1 && access[0] === "Full Access")) {
            redirectToLogin(`Invalid access for IJISEM app: ${access.join(", ")}`);
            return;
          }
        }
      }

      // ✅ Token is valid → set user
      setUser({
        id: data.user_id,
        ...userDetails,
      });
      setIsValidating(false);

    } catch (err) {
      console.error("Token validation failed:", err);
      redirectToLogin("Access denied: Token validation failed.");
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("token");
    const storedToken = localStorage.getItem("token");
    const activeToken = urlToken || storedToken;

    // ✅ No token found
    if (!activeToken) {
      redirectToLogin("Access denied: No token provided.");
      return;
    }

    // ✅ Update token in state and localStorage if from URL
    if (urlToken) {
      localStorage.setItem("token", urlToken);
      setToken(urlToken);
      
      // Clean URL by removing token parameter
      const newUrl = window.location.pathname;
      window.history.replaceState({}, document.title, newUrl);
    } else {
      setToken(storedToken);
    }

    // ✅ Check token expiry first
    if (checkTokenExpiry(activeToken)) {
      return;
    }

    // ✅ Validate the token
    validateToken(activeToken);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ✅ Loading state
  if (isValidating) {
  return (
    <div className="flex items-center justify-center h-screen relative">
      {popupMsg && (
        <div className="fixed inset-0 bg-[#515151] bg-opacity-0 z-40 transition-opacity"></div>
      )}

      {popupMsg && (
        <div className="fixed top-36 left-1/2 transform -translate-x-1/2 -translate-y-1/2 
                        bg-white p-6 rounded-xl z-50 flex flex-col space-y-4 min-w-120">
          <h2 className="text-gray-800 text-2xl font-semibold">Authentication Failed</h2>
          <h2 className="text-red-600 bg-red-50 px-10 pl-4 py-3 rounded-lg text-[16px] my-3 text-left">
            {popupMsg}
          </h2>
          <button
            onClick={() => (window.location.href = FLASK_LOGIN_URL)}
            className="text-left text-gray-700 mt-4 rounded-md transition"
          >
            Login <FontAwesomeIcon icon={faArrowRightFromBracket} />
          </button>
        </div>
      )}

      <h2 className="text-gray-600 text-xl font-semibold">
        Validating your session...
      </h2>
    </div>
  );
}

  return (
    <div className="flex">
      <Slidebar user={user} />
      <HomePageUsers
        token={token}
        onSelectConversation={(conv) => setSelectedConv(conv)}
        user={user}
        lastMessageUpdate={lastMessageUpdate}
      />
      <HomePageMsg 
        token={token} 
        conversation={selectedConv} 
        user={user} 
        onNewMessage={(data) => setLastMessageUpdate(data)}
      />
    </div>
  );
};

export default HomePage;