import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function MainPage() {
  const navigate = useNavigate();
  const [posts, setPosts] = useState([]);
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem("token"));
  const [role, setRole] = useState(localStorage.getItem("role") || "user"); // ← 추가
  const myUserID = localStorage.getItem("userID");                           // ← 추가
  const myName   = localStorage.getItem("name") || "";                       // ← 추가

  // 로그인 상태 검증
  const verifyLogin = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setIsLoggedIn(false);
      setRole("user");
      return;
    }
    try {
      const res = await fetch("http://localhost:8000/verify-token", {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setIsLoggedIn(true);
        setRole(localStorage.getItem("role") || "user"); // ← 로그인 성공 시 role 동기화
      } else {
        localStorage.removeItem("token");
        setIsLoggedIn(false);
        setRole("user");
      }
    } catch {
      localStorage.removeItem("token");
      setIsLoggedIn(false);
      setRole("user");
    }
  };

  // 게시글 로드
  const loadPosts = () => {
    fetch("http://localhost:8000/posts")
      .then(res => res.json())
      .then(data => Array.isArray(data) ? setPosts(data) : setPosts([]))
      .catch(() => setPosts([]));
  };

  useEffect(() => {
    verifyLogin();
    loadPosts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 스토리지 이벤트로 로그인/역할 동기화
  useEffect(() => {
    const onStorage = () => {
      setRole(localStorage.getItem("role") || "user");
      setIsLoggedIn(!!localStorage.getItem("token"));
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // 내가 이 글을 삭제할 수 있는가?
  const isAdmin = role === "admin";
  const canDelete = (post) => {
    // 백엔드가 author_id를 내려준다면 그것으로 판단
    if (post.author_id != null && myUserID != null) {
      if (String(post.author_id) === String(myUserID)) return true;
    }
    // 백엔드가 author_name만 준다면 이름으로 보조 판단
    if (post.author_name && myName && post.author_name === myName) return true;
    // 관리자면 항상 가능
    return isAdmin;
  };

  // 삭제 핸들러
  const deletePost = async (post_id) => {
    if (!window.confirm("이 글을 삭제하시겠어요?")) return;
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`http://localhost:8000/posts/${post_id}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "삭제에 실패했습니다.");
        return;
      }
      // 목록에서 제거
      setPosts(prev => prev.filter(p => p.post_id !== post_id));
    } catch {
      alert("서버와 연결할 수 없습니다.");
    }
  };

  return (
    <div>
      {/* 제목 */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-4xl font-extrabold">대시보드</h1>
        <button
          onClick={() => navigate("/write")}
          disabled={!isLoggedIn}
          className={`px-6 py-2 rounded-md font-bold 
            ${isLoggedIn
              ? "bg-blue-500 text-white hover:bg-blue-600"
              : "bg-gray-300 text-gray-500 cursor-not-allowed"}`}
        >
          글 작성
        </button>
      </div>

      {/* 게시글 리스트 */}
      <div className="bg-white p-6 rounded-xl shadow-md">
        <ul className="divide-y divide-black text-lg font-semibold">
          {posts.map((post) => (
            <li key={post.post_id} className="py-4">
              <div className="flex justify-between items-center gap-4">
                <button
                  onClick={() => navigate(`/posts/${post.post_id}`)}
                  className="text-left hover:underline flex-1"
                >
                  {post.title}
                </button>
                <span className="text-sm text-gray-500 mr-2 whitespace-nowrap">
                  작성자: {post.author_name}, 작성일: {new Date(post.created_at).toLocaleDateString()}
                </span>
                {/* 관리자이거나 본인 글이면 삭제 버튼 노출 */}
                {isLoggedIn && canDelete(post) && (
                  <button
                    onClick={() => deletePost(post.post_id)}
                    className="px-3 py-1 rounded bg-red-100 text-red-700 text-sm"
                    title={isAdmin ? "관리자 삭제" : "내 글 삭제"}
                  >
                    삭제
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default MainPage;