import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

/**
 * 댓글 컴포넌트
 * - 목록/작성/수정/삭제
 * - 로그인 여부 및 본인 댓글 여부에 따라 기능 노출
 * - 본인 여부는 localStorage.userID === c.user_id 로 판단
 */
function Comments({ postId }) {
  const [items, setItems] = useState([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null); 
  const [editingContent, setEditingContent] = useState("");
  const token = localStorage.getItem("token");
  const myUserId = Number(localStorage.getItem("userID") || 0);
  
  const fetchComments = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/posts/${postId}/comments?page=1&size=100`);
      if (!res.ok) throw new Error("failed");
      const data = await res.json();
      setItems(data);
    } catch (e) {
      console.error(e);
      alert("댓글을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComments();
  }, [postId]);

  const handleCreate = async () => {
    if (!token) {
      alert("로그인이 필요합니다.");
      return;
    }
    if (!content.trim()) return;

    try {
      const res = await fetch(`http://localhost:8000/posts/${postId}/comments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "댓글 등록 실패");
      }
      setContent("");
      fetchComments();
    } catch (e) {
      console.error(e);
      alert(e.message);
    }
  };
 
  const startEdit = (c) => {
    setEditingId(c.comment_id);
    setEditingContent(c.content);
  };
  const cancelEdit = () => {
    setEditingId(null);
    setEditingContent("");
  };
  const saveEdit = async () => {
    if (!token) {
      alert("로그인이 필요합니다.");
      return;
    }
    try {
      const res = await fetch(`http://localhost:8000/comments/${editingId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ content: editingContent }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "댓글 수정 실패");
      }
      cancelEdit();
      fetchComments();
    } catch (e) {
      console.error(e);
      alert(e.message);
    }
  };

  const remove = async (commentId) => {
    if (!token) {
      alert("로그인이 필요합니다.");
      return;
    }
    if (!window.confirm("댓글을 삭제할까요?")) return;
    try {
      const res = await fetch(`http://localhost:8000/comments/${commentId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status !== 204) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "댓글 삭제 실패");
      }
      fetchComments();
    } catch (e) {
      console.error(e);
      alert(e.message);
    }
  };

  return (
    <div className="mt-10">
      <h2 className="text-xl font-semibold mb-3">댓글</h2>

      {/* 작성 */}
      <div className="flex gap-2">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="댓글을 입력하세요"
          className="flex-1 border rounded px-3 py-2"
          rows={2}
        />
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          등록
        </button>
      </div>

      {/* 목록 */}
      <div className="mt-4 space-y-3">
        {loading ? (
          <div className="text-gray-500">댓글을 불러오는 중...</div>
        ) : items.length === 0 ? (
          <div className="text-gray-500">첫 댓글을 남겨보세요!</div>
        ) : (
          items.map((c) => {
            const isOwner = myUserId === c.user_id;
            const isEditing = editingId === c.comment_id;

            return (
              <div key={c.comment_id} className="border rounded p-3">
                <div className="text-sm text-gray-600 mb-1">
                  {c.author_name} · {new Date(c.created_at).toLocaleString()}
                </div>

                {!isEditing ? (
                  <p className="whitespace-pre-wrap">{c.content}</p>
                ) : (
                  <textarea
                    value={editingContent}
                    onChange={(e) => setEditingContent(e.target.value)}
                    className="w-full border rounded px-3 py-2"
                    rows={2}
                  />
                )}

                {isOwner && (
                  <div className="mt-2 flex gap-2">
                    {!isEditing ? (
                      <>
                        <button
                          onClick={() => startEdit(c)}
                          className="px-3 py-1 border rounded hover:bg-gray-50"
                        >
                          수정
                        </button>
                        <button
                          onClick={() => remove(c.comment_id)}
                          className="px-3 py-1 border rounded text-red-600 hover:bg-red-50"
                        >
                          삭제
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={saveEdit}
                          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                          저장
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="px-3 py-1 border rounded hover:bg-gray-50"
                        >
                          취소
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

/**
 * 게시글 상세 페이지
 * - 게시글 조회/표시
 * - 로그인 사용자와 글 작성자 비교-> 본인 글일 때만 "수정/삭제" 버튼 노출
 * - 댓글 컴포넌트 포함
 */
export default function PostDetailPage() {
  const { postId } = useParams();
  const navigate = useNavigate();

  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem("token"));
  useEffect(() => {
    const onStorage = () => setIsLoggedIn(!!localStorage.getItem("token"));
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("name");
    localStorage.removeItem("userID");
    setIsLoggedIn(false);
    navigate("/");
  };

  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const myUserId = Number(localStorage.getItem("userID") || "0");

  useEffect(() => {
    fetch(`http://localhost:8000/posts/${postId}`)
      .then((res) => res.json())
      .then((data) => setPost(data))
      .catch(() => alert("글을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [postId]);

  const isOwner = !!post && Number(post.user_id) === myUserId;

  const handleDelete = async () => {
    if (!window.confirm("정말 삭제하시겠습니까?")) return;
    const token = localStorage.getItem("token");
    if (!token) {
      alert("로그인이 필요합니다.");
      return;
    }

    try {
      const res = await fetch(`http://localhost:8000/posts/${postId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        alert("삭제되었습니다.");
        navigate("/");
      } else {
        const err = await res.json();
        alert("삭제 실패: " + (err.detail || "알 수 없는 오류"));
      }
    } catch (e) {
      console.error(e);
      alert("서버와 연결할 수 없습니다.");
    }
  };

  const handleEdit = () => {
    if (!isOwner) return;
    const token = localStorage.getItem("token");
    if (!token) {
      alert("로그인이 필요합니다.");
      return;
    }
    navigate(`/posts/${postId}/edit`);
  };

  if (loading) return <div className="p-10">불러오는 중...</div>;
  if (!post) return <div className="p-10">글이 없습니다.</div>;

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar 제거됨 */}
      <div className="flex-1 p-10 flex justify-center">
        <div className="w-full max-w-3xl bg-white p-8 rounded-xl shadow-md">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-3xl font-bold">{post.title}</h1>
          </div>

          <p className="text-sm text-gray-500 mb-6">
            작성일: {new Date(post.created_at).toLocaleString()}
          </p>

          <div className="whitespace-pre-wrap text-lg leading-7 mb-8">
            {post.content}
          </div>

          {isOwner && (
            <div className="flex justify-end gap-3">
              <button
                onClick={handleEdit}
                className="px-5 py-2 bg-blue-500 text-white rounded-md font-semibold hover:bg-blue-600"
              >
                수정
              </button>
            </div>
          )}

          <Comments postId={Number(postId)} />
        </div>
      </div>
    </div>
  );
}
