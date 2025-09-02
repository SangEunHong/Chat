import React, { useEffect, useState, useCallback } from "react";

const API = "http://localhost:8000/admin/users";
const SIZE = 20;

export default function AdminUsersPage() {
  const [q, setQ] = useState("");

  // 활성 회원
  const [rowsActive, setRowsActive] = useState([]);
  const [totalActive, setTotalActive] = useState(0);
  const [pageActive, setPageActive] = useState(1);
  const [loadingActive, setLoadingActive] = useState(false);

  // 탈퇴 회원
  const [rowsDeleted, setRowsDeleted] = useState([]);
  const [totalDeleted, setTotalDeleted] = useState(0);
  const [pageDeleted, setPageDeleted] = useState(1);
  const [loadingDeleted, setLoadingDeleted] = useState(false);

  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const fetchList = useCallback(
    async (status) => {
      const isDeleted = status === "deleted";

      // 섹션별 로딩 시작
      if (isDeleted) setLoadingDeleted(true);
      else setLoadingActive(true);

      try {
        // 토큰 없으면 섹션별 초기화
        if (!token) {
          if (isDeleted) {
            setRowsDeleted([]);
            setTotalDeleted(0);
          } else {
            setRowsActive([]);
            setTotalActive(0);
          }
          return;
        }

        const url = new URL(API);
        url.searchParams.set("status", status);
        if (q) url.searchParams.set("q", q);
        url.searchParams.set("page", isDeleted ? pageDeleted : pageActive);
        url.searchParams.set("size", SIZE);

        const res = await fetch(url.toString(), {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `API 요청 실패 (${res.status})`);
        }

        const data = await res.json();

        if (isDeleted) {
          setRowsDeleted(data.items || []);
          setTotalDeleted(data.total || 0);
        } else {
          setRowsActive(data.items || []);
          setTotalActive(data.total || 0);
        }
      } catch (e) {
        console.error(`GET /admin/users?status=${status} failed:`, e.message);
        // 에러 시 섹션별 초기화
        if (isDeleted) {
          setRowsDeleted([]);
          setTotalDeleted(0);
        } else {
          setRowsActive([]);
          setTotalActive(0);
        }
      } finally {
        // 섹션별 로딩 종료
        if (isDeleted) setLoadingDeleted(false);
        else setLoadingActive(false);
      }
    },
    [token, q, pageActive, pageDeleted]
  );

  // 활성/탈퇴 섹션 각각 로드
  useEffect(() => { fetchList("active"); }, [fetchList]);
  useEffect(() => { fetchList("deleted"); }, [fetchList]);

  // 로그인 직후 토큰 들어오면 재요청
  useEffect(() => {
    const onStorage = () => {
      const t = localStorage.getItem("token");
      if (t) {
        fetchList("active");
        fetchList("deleted");
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [fetchList]);

  const totalPagesActive = Math.max(1, Math.ceil(totalActive / SIZE));
  const totalPagesDeleted = Math.max(1, Math.ceil(totalDeleted / SIZE));

  async function softDelete(userID) {
    if (!window.confirm("정말 탈퇴 처리하시겠어요? (복구 가능)")) return;
    await fetch(`${API}/${userID}/soft-delete`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchList("active");
    setPageDeleted(1);
    fetchList("deleted");
  }

  async function restore(userID) {
    if (!window.confirm("이 회원을 복구하시겠어요?")) return;
    await fetch(`${API}/${userID}/restore`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchList("deleted");
    fetchList("active");
  }

  async function hardDelete(userID) {
    if (!window.confirm("영구 삭제됩니다. 계속하시겠어요?")) return;
    await fetch(`${API}/${userID}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchList("active");
    fetchList("deleted");
  }

  async function purgeExpired() {
    if (!window.confirm("1년 경과 탈퇴 회원을 일괄 영구삭제합니다. 계속하시겠어요?")) return;
    await fetch(`${API}/purge-expired`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchList("deleted");
  }

  const Table = ({ title, rows, loading, onDelete, onRestore, showRestore }) => (
    <div className="bg-white border rounded shadow-sm overflow-hidden mb-10">
      <div className="flex items-center justify-between p-4">
        <h2 className="text-lg font-bold">{title}</h2>
        {title === "탈퇴 회원" && (
          <button onClick={purgeExpired} className="px-3 py-2 rounded bg-red-100 text-red-700">
            1년 경과 탈퇴회원 일괄삭제
          </button>
        )}
      </div>
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left">userID</th>
            <th className="px-3 py-2 text-left">아이디</th>
            <th className="px-3 py-2 text-left">이름</th>
            <th className="px-3 py-2 text-left">권한</th>
            <th className="px-3 py-2 text-left">상태</th>
            <th className="px-3 py-2 text-left">가입일</th>
            <th className="px-3 py-2 text-left">탈퇴일</th>
            <th className="px-3 py-2">액션</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan="8" className="p-6 text-center text-gray-500">불러오는 중…</td></tr>
          ) : rows.length === 0 ? (
            <tr><td colSpan="8" className="p-6 text-center text-gray-500">데이터가 없습니다.</td></tr>
          ) : rows.map(u => (
            <tr key={u.userID} className="border-t">
              <td className="px-3 py-2">{u.userID}</td>
              <td className="px-3 py-2">{u.ID}</td>
              <td className="px-3 py-2">{u.name}</td>
              <td className="px-3 py-2">{u.role}</td>
              <td className="px-3 py-2">{u.is_deleted ? "탈퇴" : "활동중"}</td>
              <td className="px-3 py-2">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}</td>
              <td className="px-3 py-2">{u.deleted_at ? new Date(u.deleted_at).toLocaleDateString() : "-"}</td>
              <td className="px-3 py-2 text-right">
                {!u.is_deleted ? (
                  <button
                    onClick={() => onDelete(u.userID)}
                    className="px-2 py-1 rounded bg-yellow-100 text-yellow-800 mr-2">
                    탈퇴 처리
                  </button>
                ) : showRestore ? (
                  <button
                    onClick={() => onRestore(u.userID)}
                    className="px-2 py-1 rounded bg-green-100 text-green-800 mr-2">
                    복구
                  </button>
                ) : null}
                <button
                  onClick={() => hardDelete(u.userID)}
                  className="px-2 py-1 rounded bg-red-100 text-red-700">
                  영구 삭제
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">회원 관리</h1>

      {/* 검색어 (두 표 공통) */}
      <div className="flex items-center gap-3 mb-6">
        <input
          value={q}
          onChange={(e) => { setPageActive(1); setPageDeleted(1); setQ(e.target.value); }}
          placeholder="아이디/이름 검색"
          className="border rounded px-3 py-2 flex-1"
        />
      </div>

      <Table
        title="활동중인 회원"
        rows={rowsActive}
        loading={loadingActive}
        onDelete={softDelete}
        showRestore={false}
      />
      <div className="flex items-center justify-between mt-[-8px] mb-10 text-sm">
        <div>총 {totalActive}명</div>
        <div className="space-x-2">
          <button disabled={pageActive <= 1} onClick={() => setPageActive(p => p - 1)} className="px-3 py-1 rounded border disabled:opacity-50">이전</button>
          <span>{pageActive} / {totalPagesActive}</span>
          <button disabled={pageActive >= totalPagesActive} onClick={() => setPageActive(p => p + 1)} className="px-3 py-1 rounded border disabled:opacity-50">다음</button>
        </div>
      </div>

      <Table
        title="탈퇴 회원"
        rows={rowsDeleted}
        loading={loadingDeleted}
        onDelete={() => {}}
        onRestore={restore}
        showRestore={true}
      />
      <div className="flex items-center justify-between mt-[-8px] text-sm">
        <div>총 {totalDeleted}명</div>
        <div className="space-x-2">
          <button disabled={pageDeleted <= 1} onClick={() => setPageDeleted(p => p - 1)} className="px-3 py-1 rounded border disabled:opacity-50">이전</button>
          <span>{pageDeleted} / {totalPagesDeleted}</span>
          <button disabled={pageDeleted >= totalPagesDeleted} onClick={() => setPageDeleted(p => p + 1)} className="px-3 py-1 rounded border disabled:opacity-50">다음</button>
        </div>
      </div>
    </div>
  );
}