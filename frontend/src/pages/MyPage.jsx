import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiEye, FiEyeOff } from "react-icons/fi";

export default function MyPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [userInfo, setUserInfo] = useState(null);

  const [formData, setFormData] = useState({
    name: "",
    bdate: "",
    phone: "",
    password: "",
    deletePassword: "",
    confirmDelete: false
  });

  const [passwordError, setPasswordError] = useState("");
  const [showDeleteSection, setShowDeleteSection] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordMatchError, setPasswordMatchError] = useState("");

  // 날짜, 전화번호 등 필드 정규화
  const normalizeUser = (raw) => {
    // 아이디(읽기전용 표시용)
    const id =
      raw?.ID ??
      raw?.id ??
      raw?.userID ??
      raw?.userid ??
      "";

    // 생년월일: bdate/birth/birthdate 등 → YYYY-MM-DD 로 트림
    const bdRaw = raw?.bdate ?? raw?.birth ?? raw?.birthdate ?? raw?.birth_date ?? "";
    const bdate = bdRaw ? String(bdRaw).slice(0, 10) : "";

    // 전화번호: phone/phoneNumber 등
    const phone = raw?.phone ?? raw?.phoneNumber ?? raw?.tel ?? "";

    // 이름
    const name = raw?.name ?? raw?.username ?? "";

    return { id, bdate, phone, name };
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("name");
    localStorage.removeItem("userID");
    navigate("/");
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    fetch("http://localhost:8000/mypage", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => {
        if (res.status === 401) {
          alert("로그인 세션이 만료되었습니다.");
          localStorage.removeItem("token");
          navigate("/login");
          return Promise.reject();
        }
        return res.json();
      })
      .then(data => {
        const norm = normalizeUser(data);
        setUserInfo({ ...data, ID: norm.id }); // 표시는 userInfo.ID로
        setFormData(prev => ({
          ...prev,
          name: norm.name,
          bdate: norm.bdate,
          phone: norm.phone
        }));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [navigate]);

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50 items-center justify-center">
        불러오는 중...
      </div>
    );
  }

  const handleChange = (e) => {
    const { name, value, checked, type } = e.target;

    if (name === "password") {
      if (value && (value.length < 8 || !/[!@#$%^&*(),.?":{}|<>]/.test(value))) {
        setPasswordError("비밀번호는 특수문자 포함 8자리 이상이어야 합니다.");
      } else {
        setPasswordError("");
      }
    }

    setFormData({
      ...formData,
      [name]: type === "checkbox" ? checked : value
    });
  };

  const handleUpdate = async () => {
    const token = localStorage.getItem("token");
    if (formData.password && passwordError) {
      alert("비밀번호를 다시 확인해주세요.");
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/mypage/update", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          name: formData.name,
          bdate: formData.bdate,
          phone: formData.phone,
          password: formData.password || undefined, // 비번 미입력시 전송 생략
        })
      });

      if (res.ok) {
        const updated = await res.json();
        const norm = normalizeUser(updated);
        setUserInfo({ ...updated, ID: norm.id });
        setFormData(prev => ({ ...prev, password: "" }));
        alert("회원정보가 수정되었습니다.");
      } else {
        const err = await res.json();
        alert("수정 실패: " + (err.detail || "알 수 없는 오류"));
      }
    } catch (error) {
      console.error(error);
      alert("서버와 연결할 수 없습니다.");
    }
  };

  const handleDelete = async () => {
    const token = localStorage.getItem("token");

    if (!formData.deletePassword || !formData.confirmDelete) {
      alert("비밀번호와 확인 체크를 완료해주세요.");
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/mypage/delete", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ password: formData.deletePassword })
      });

      if (res.ok) {
        alert("회원 탈퇴가 완료되었습니다.");
        localStorage.removeItem("token");
        localStorage.removeItem("name");
        localStorage.removeItem("userID");
        navigate("/");
      } else {
        const err = await res.json();
        alert("회원 탈퇴 실패: " + (err.detail || "알 수 없는 오류"));
      }
    } catch (error) {
      console.error(error);
      alert("서버와 연결할 수 없습니다.");
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50 justify-center items-center">
      <div className="w-full max-w-md p-6 bg-white rounded-xl shadow-md">
        <h1 className="text-2xl font-bold mb-4">마이페이지</h1>

        {/* ID (읽기전용) */}
        <div className="mb-2">
          <label className="block font-semibold">ID</label>
          <input
            type="text"
            value={userInfo?.ID ?? ""}
            disabled
            className="w-full border border-gray-300 rounded px-3 py-2 bg-gray-100"
          />
        </div>

        {/* 비밀번호 수정 */}
        <div className="mb-2">
          <label className="block font-semibold">비밀번호 수정</label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              name="password"
              value={formData.password || ""}
              onChange={(e) => {
                handleChange(e);
                setPasswordMatchError(
                  confirmPassword && e.target.value !== confirmPassword
                    ? "비밀번호가 일치하지 않습니다."
                    : ""
                );
              }}
              className="w-full border border-gray-300 rounded px-3 py-2 pr-10"
              placeholder="새 비밀번호 (선택사항)"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2 top-2 text-gray-500"
            >
              {showPassword ? <FiEyeOff size={20} /> : <FiEye size={20} />}
            </button>
          </div>
          {passwordError && (
            <p className="text-sm text-red-600 mt-1">{passwordError}</p>
          )}
        </div>

        {/* 비밀번호 확인 */}
        <div className="mb-2">
          <label className="block font-semibold">비밀번호 확인</label>
          <div className="relative">
            <input
              type={showConfirmPassword ? "text" : "password"}
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                setPasswordMatchError(
                  formData.password && e.target.value !== formData.password
                    ? "비밀번호가 일치하지 않습니다."
                    : ""
                );
              }}
              className="w-full border border-gray-300 rounded px-3 py-2 pr-10"
              placeholder="비밀번호를 다시 입력하세요"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-2 top-2 text-gray-500"
            >
              {showConfirmPassword ? <FiEyeOff size={20} /> : <FiEye size={20} />}
            </button>
          </div>
          {passwordMatchError && (
            <p className="text-sm text-red-600 mt-1">{passwordMatchError}</p>
          )}
        </div>

        {/* 이름 */}
        <div className="mb-2">
          <label className="block font-semibold">이름</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded px-3 py-2"
          />
        </div>

        {/* 생년월일 */}
        <div className="mb-2">
          <label className="block font-semibold">생년월일</label>
          <input
            type="text"
            name="bdate"
            value={formData.bdate}
            onChange={handleChange}
            placeholder="YYYY-MM-DD"
            className="w-full border border-gray-300 rounded px-3 py-2"
          />
        </div>

        {/* 전화번호 */}
        <div className="mb-2">
          <label className="block font-semibold">전화번호</label>
          <input
            type="text"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            placeholder="010-XXXX-XXXX"
            className="w-full border border-gray-300 rounded px-3 py-2"
          />
        </div>

        <button
          onClick={handleUpdate}
          className="w-full py-2 bg-blue-500 text-white font-bold rounded hover:bg-blue-600 mt-4"
        >
          수정하기
        </button>

        <button
          onClick={() => setShowDeleteSection(!showDeleteSection)}
          className="w-full py-2 mt-4 bg-red-500 text-white font-bold rounded hover:bg-red-600"
        >
          회원 탈퇴
        </button>

        {showDeleteSection && (
          <>
            <hr className="my-4" />
            <h2 className="text-lg font-semibold mb-2 text-red-600">회원 탈퇴</h2>

            <div className="mb-2">
              <label className="block font-semibold">비밀번호 확인</label>
              <input
                type="password"
                name="deletePassword"
                value={formData.deletePassword}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="비밀번호를 입력하세요"
              />
            </div>

            <div className="mb-4 flex items-center">
              <input
                type="checkbox"
                id="confirmDelete"
                name="confirmDelete"
                checked={formData.confirmDelete}
                onChange={handleChange}
                className="mr-2"
              />
              <label htmlFor="confirmDelete" className="text-sm">
                모든 정보가 삭제됩니다. 이에 동의합니다.
              </label>
            </div>

            <button
              onClick={handleDelete}
              className="w-full py-2 bg-red-500 text-white font-bold rounded hover:bg-red-600"
            >
              회원 탈퇴 확인
            </button>
          </>
        )}
      </div>
    </div>
  );
}