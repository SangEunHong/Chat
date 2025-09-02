// src/Layout.jsx
import React, { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Footer from "./components/Footer";

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();

  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem("token"));
  const [currentUser, setCurrentUser] = useState(null); // ✅ 추가: 현재 사용자 상태

  // 안전한 JWT 디코딩 (base64url → JSON)
  const decodeJwt = (token) => {
    try {
      const [, payloadB64] = token.split(".");
      const b64 = payloadB64.replace(/-/g, "+").replace(/_/g, "/");
      const json = JSON.parse(atob(b64));
      return json;
    } catch {
      return null;
    }
  };

  // 로그인 상태 동기화
  useEffect(() => {
    const onStorage = () => setIsLoggedIn(!!localStorage.getItem("token"));
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // 토큰 → currentUser 채우기
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setCurrentUser(null);
      return;
    }
    const payload = decodeJwt(token);
    if (!payload) {
      setCurrentUser(null);
      return;
    }
    setCurrentUser({
      userID: payload.sub ?? payload.userID ?? null,
      role: payload.role ?? "user",
      name: localStorage.getItem("name") || "",
    });
  }, [isLoggedIn]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("name");
    localStorage.removeItem("userID");
    setIsLoggedIn(false);
    setCurrentUser(null); // ✅ 로그아웃 시 초기화
    navigate("/");
  };

  // 항상 보일 푸터 상단 한 줄 높이(px)
  const FOOTER_PEEK = 48;
  //  어떤 페이지에서 푸터를 숨길지 정의
  const isAuthPage =
    location.pathname.startsWith("/login") ||
    location.pathname.startsWith("/signup");
  //  채팅 페이지면 스페이서(푸터 미리보기용) 줄이기
  const isChat = location.pathname.startsWith("/chat");
  const spacerHeight = isAuthPage ? "0" : (isChat ? "6vh" : "30vh");

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex min-h-screen">
        <Sidebar
          isLoggedIn={isLoggedIn}
          onLogout={handleLogout}
          currentUser={currentUser} //  관리자 메뉴 노출용
        />

        {/*  내부 자식이 자신의 스크롤을 갖게 하려면 min-h-0 이 중요합니다 */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* 메인 컨텐츠 */}
          <main className="flex-1 p-10 min-h-0">
            <Outlet />
          </main>

          {/*  페이지별로 다른 스페이서 (푸터를 아래로 밀어내는 용도) */}
          <div aria-hidden="true" className="shrink-0" style={{ height: spacerHeight }} />

          {!isAuthPage && <Footer peekPx={FOOTER_PEEK} />}
        </div>
      </div>
    </div>
  );
}
