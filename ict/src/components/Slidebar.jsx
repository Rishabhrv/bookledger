// src/components/Slidebar.jsx
import React from "react";
import { Link } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHouseChimney } from "@fortawesome/free-solid-svg-icons";

const Slidebar = ({ user }) => {
  const userInitials = user?.username ? user.username.slice(0, 2).toUpperCase() : "JD";

  return (
    <div className="w-25 bgcolor flex flex-col items-center py-4 space-y-3 h-screen rounded-r-2xl shadow-md">
      {/* --- Logo / Top Icon --- */}
      <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center font-bold text-bgcolor text-xl">
        C
      </div>

      {/* --- Main Nav Buttons --- */}
      <div className="flex-1 flex flex-col items-center space-y-4 mt-4">
        <Link
          to={`/chat`}
          className="w-12 h-12 bgcolor-100 rounded-xl flex items-center justify-center hover:bgcolor transition-colors"
        >
          <FontAwesomeIcon icon={faHouseChimney} className="text-white text-lg" />
        </Link>

      </div>

      {/* --- Bottom User Icon --- */}
      <div className="w-12 h-12 rounded-full bgcolor-500 flex items-center justify-center text-white font-semibold">
        {userInitials}
      </div>
    </div>
  );
};

export default Slidebar;
