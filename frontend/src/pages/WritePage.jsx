import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function WritePage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState(""); //제목
  const [content, setContent] = useState(""); //내용
  const [isSubmitting, setIsSubmitting] = useState(false); //작성 중 여부(중복 클릭 방지)

  const [loggedIn, setLoggedIn] = useState(!!localStorage.getItem("token"));

  // 다른 탭/페이지에서 로그인 상태가 바뀐 것 반영
  useEffect(() => {
    const onStorage = () => setLoggedIn(!!localStorage.getItem("token"));
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  //로그아웃 버튼 (레이아웃에서 처리하더라도 여기 로직은 유지)
  const handleLogout = () => {
    localStorage.removeItem("token"); //사용자 정보 삭제
    localStorage.removeItem("name");
    setLoggedIn(false);        // 사이드바 즉시 갱신
    navigate("/");             // 홈으로 이동
  }; 
  
  //글 작성버튼
  const handleSubmit = async () => {
    // 로그인 확인
    const token = localStorage.getItem("token");
    if (!token) {
      setLoggedIn(false);
      alert("로그인이 필요합니다.");
      return;
    }

    //필수 입력값 확인
    if (!title || !content) {
      alert("제목과 내용을 모두 입력해주세요.");
      return;
    }

    setIsSubmitting(true); //  버튼 중복 클릭 방지
    try {
      const res = await fetch("http://localhost:8000/posts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ title, content })
      });

      if (res.ok) {
        alert("글이 작성되었습니다.");
        navigate("/");
      } else {
        const err = await res.json();
        alert("작성 실패: " + JSON.stringify(err.detail || err));
      }
    } catch (err) {
      console.error(err);
      alert("서버와 연결할 수 없습니다.");
    } finally {
      setIsSubmitting(false); // 다시 활성화
    }
  };

  return (
    // 레이아웃이 사이드바를 공통으로 렌더링하므로 여기서는 본문만 출력
    <div className="flex-1 p-10 flex justify-center items-start bg-gray-50">
      <div className="w-full max-w-2xl bg-white p-8 rounded-xl shadow-md">
        <h1 className="text-2xl font-bold mb-6">글 작성</h1>

        {/* 제목 */}
        <div className="mb-4">
          <label className="block font-semibold mb-1">제목</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full border border-gray-300 rounded px-4 py-2"
            placeholder="제목을 입력해주세요"
          />
        </div>

        {/* 내용 */}
        <div className="mb-6">
          <label className="block font-semibold mb-1">내용</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-64 border border-gray-300 rounded px-4 py-2 resize-none"
            placeholder="내용을 입력해주세요"
          />
        </div>

        {/* 작성 버튼 */}
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className={`px-6 py-2 font-bold rounded-md transition-all duration-200 ${
            isSubmitting
              ? "bg-gray-400 text-white cursor-not-allowed"
              : "bg-blue-500 hover:bg-blue-600 text-white"
          }`}
        >
          {isSubmitting ? "업로드 중..." : "작성 완료"}
        </button>
      </div>
    </div>
  );
}
