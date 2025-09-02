import React from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { FaRegUserCircle } from "react-icons/fa";
import { LuMessageSquare } from "react-icons/lu";
import { FaUsersCog } from "react-icons/fa";

export default function Sidebar({ isLoggedIn, onLogout, currentUser }) {
  const navigate = useNavigate();
  const userName = localStorage.getItem("name") || "";
  // 변경: currentUser 없을 때 토큰에서 role 읽어오기 (fallback)
 let isAdmin = currentUser?.role === "admin";
 if (!isAdmin) {
  const token = localStorage.getItem("token");
   if (token) {
     try {
       const [, p] = token.split(".");
       const payload = JSON.parse(atob(p));
       isAdmin = payload?.role === "admin";
     } catch {}
   }
  }
  const handleLogoutClick = () => {
    onLogout();
    navigate("/");
  };

  const itemBase =
    "flex items-center gap-3 px-5 py-3 rounded-lg text-gray-700 hover:bg-gray-100 transition";
  const itemActive = "bg-gray-100 font-bold";

  return (
    <div className="w-64 border-r border-gray-300 flex flex-col items-center justify-start bg-white py-10">
      {/* Brand */}
      <Link
        to="/"
        className="text-4xl font-serif italic mb-10 cursor-pointer hover:opacity-80 leading-tight"
      >
        Custom<br />Chat
      </Link>

      {isLoggedIn ? (
        <>
          {/* 유저 아이콘 + 이름 */}
          <FaRegUserCircle className="text-6xl mb-2 text-black" />
          <p className="text-xl font-semibold mb-6">{userName}</p>

          {/* 👉 한 줄 버튼 */}
          <div className="w-full px-4 mb-6 flex gap-2">
            <button
              onClick={handleLogoutClick}
              className="flex-1 h-10 bg-red-500 text-white rounded-md font-bold hover:bg-red-600"
            >
              로그아웃
            </button>
            <Link
              to="/mypage"
              className="flex-1 h-10 bg-blue-500 text-white rounded-md font-bold hover:bg-blue-600 flex items-center justify-center"
            >
              마이페이지
            </Link>
          </div>
        </>
      ) : (
        <>
          {/*  로그인 / 회원가입 버튼을 한 줄에 맞게, 사이드바 밖으로 안 나가게 */}
          <div className="flex w-full px-4 gap-2 mb-6">
            <Link
              to="/login"
              className="flex-1 h-10 bg-blue-500 text-white rounded-md font-semibold text-sm
                        hover:bg-blue-600 flex items-center justify-center whitespace-nowrap"
            >
              로그인
            </Link>
            <Link
              to="/signup"
              className="flex-1 h-10 bg-blue-500 text-white rounded-md font-semibold text-sm
                        hover:bg-blue-600 flex items-center justify-center whitespace-nowrap"
            >
              회원가입
            </Link>
          </div>
        </>
      )}

      {/* Chat 메뉴 (더 크고 진하게 강조) */}
      <div className="w-full px-4 mt-4">
        <NavLink
          to="/chat"
          className={({ isActive }) =>
            `${itemBase} ${isActive ? itemActive : ""} text-lg font-bold`
          }
        >
          <LuMessageSquare className="text-xl" />
          <span>Chat</span>
        </NavLink>
      </div>
      {/* 관리자 전용 메뉴 */}
      {isAdmin && (
        <div className="w-full px-4 mt-2">
          <NavLink
            to="/admin/users"
            className={({ isActive }) =>
              `${itemBase} ${isActive ? itemActive : ""} text-lg font-bold text-red-600`
            }
          >
            <FaUsersCog className="text-xl" />
            <span>회원 관리</span>
          </NavLink>
        </div>
      )}
    </div>
  );
}