import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

export default function PostEditPage() {
  const { postId } = useParams();
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 기존 글 불러오기
  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`http://localhost:8000/posts/${postId}`);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        setTitle(data.title || "");
        setContent(data.content || "");
      } catch (e) {
        alert("글을 불러오지 못했습니다.");
        navigate(-1);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [postId, navigate]);

  // 글 수정 요청
  const handleUpdate = async () => {
    if (!title.trim() || !content.trim()) {
      alert("제목과 내용을 모두 입력해주세요.");
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      alert("로그인이 필요합니다.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`http://localhost:8000/posts/${postId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title, content }),
      });

      if (res.ok) {
        alert("수정되었습니다.");
        navigate(`/posts/${postId}`);
      } else {
        const err = await res.json().catch(() => ({}));
        alert("수정 실패: " + (err.detail || "알 수 없는 오류"));
      }
    } catch (e) {
      console.error(e);
      alert("서버와 연결할 수 없습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="p-10">불러오는 중...</div>;

  return (
    <div className="flex-1 p-10 flex justify-center items-start">
      <div className="w-full max-w-2xl bg-white p-8 rounded-xl shadow-md">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">글 수정</h1>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 text-sm"
          >
            취소
          </button>
        </div>

        {/* 제목 */}
        <div className="mb-4">
          <label className="block font-semibold mb-1">제목</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full border border-gray-300 rounded px-4 py-2"
            placeholder="제목을 입력하세요"
            disabled={isSubmitting}
          />
        </div>

        {/* 내용 */}
        <div className="mb-6">
          <label className="block font-semibold mb-1">내용</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-64 border border-gray-300 rounded px-4 py-2 resize-none"
            placeholder="내용을 입력하세요"
            disabled={isSubmitting}
          />
        </div>

        <button
          onClick={handleUpdate}
          disabled={isSubmitting}
          className={`px-6 py-2 font-bold rounded-md ${
            isSubmitting
              ? "bg-gray-400 text-white cursor-not-allowed"
              : "bg-blue-500 hover:bg-blue-600 text-white"
          }`}
        >
          {isSubmitting ? "수정 중..." : "수정 완료"}
        </button>
      </div>
    </div>
  );
}
