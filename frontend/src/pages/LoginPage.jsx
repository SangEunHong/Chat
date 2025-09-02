import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiEye, FiEyeOff } from "react-icons/fi";

/**
 * LoginPage.jsx
 * - 로그인 기능
 * - 아이디 찾기 모달(modal)
 * - 비밀번호 재설정(2단계) 모달
 * - 상태 관리 및 서버 통신
 */

export default function LoginPage() {
  const navigate = useNavigate();

  //상태 관리: 로그인 입력
  const [id, setId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  //상태관리: 모달 열람 여부
  const [openFindId, setOpenFindId] = useState(false); //아이디 찾기 모달
  const [openResetPw, setOpenResetPw] = useState(false); //비밀번호 재설정 모달

  //상태관리: 아이디 찾기
  const [findName, setFindName] = useState(''); //이름
  const [findPhone, setFindPhone] = useState(''); //전화번호
  const [foundId, setFoundId] = useState(null);  //조회된 ID
  const [findIdLoading, setFindIdLoading] = useState(false); //조회 로딩 여부
  const [isComposingFindName, setIsComposingFindName] = useState(false); //한글 조합상태

  //상태관리: 비밀번호 재설정(1단계: 본인확인)
  const [resetId, setResetId] = useState('');
  const [resetName, setResetName] = useState('');
  const [resetPhone, setResetPhone] = useState('');
  const [resetStep, setResetStep] = useState(1); // 1=본인확인, 2=새 비번 설정
  const [resetToken, setResetToken] = useState(null); //서버에서 받은 토큰
  const [resetLoading, setResetLoading] = useState(false);
  const [isComposingResetName, setIsComposingResetName] = useState(false);

  //상태관리: 비밀번호 재설정(2단계: 새 비번 입력)
  const [newPw, setNewPw] = useState('');
  const [newPwConfirm, setNewPwConfirm] = useState('');
  const [showNewPw, setShowNewPw] = useState(false);
  const [showNewPwConfirm, setShowNewPwConfirm] = useState(false);

  //유효성 검사
  const pwValid = /^(?=.*[!@#$%^&*(),.?":{}|<>])[A-Za-z\d!@#$%^&*(),.?":{}|<>]{8,}$/.test(newPw); //비밀번호 조건 체크
  const pwMatchError = newPw && newPwConfirm && newPw !== newPwConfirm; //비밀번호 불일치 여부

  //로그인 처리
  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = { ID: id, password };
    try {
      const response = await fetch("http://localhost:8000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        console.log("LOGIN RESPONSE:", data);
        alert("로그인 성공!");
        // 로컬스토리지에 로그인 정보 저장
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("name", data.name); 
        localStorage.setItem("userID", String(data.userID));
        localStorage.setItem("role", data.role);
        console.log("SAVED token:", localStorage.getItem("token"));
        window.dispatchEvent(new Event("storage"));
        navigate("/");
      } else {
        const errorData = await response.json();
        alert("로그인 실패: " + (errorData.detail || "알 수 없는 오류"));
      }
    } catch (error) {
      alert("서버와 연결할 수 없습니다.");
    }
  };

  //전화번호 포맷팅
  const formatPhone = (v) => {
    const raw = v.replace(/\D/g, '');
    if (raw.length <= 3) return raw;
    if (raw.length <= 7) return `${raw.slice(0,3)}-${raw.slice(3)}`;
    return `${raw.slice(0,3)}-${raw.slice(3,7)}-${raw.slice(7,11)}`;
  };

  // 아이디 찾기
  const handleFindId = async (e) => {
    e.preventDefault();
    setFindIdLoading(true);
    setFoundId(null);
    try {
      const res = await fetch("http://localhost:8000/find-id", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: findName, phone: findPhone }),
      });
      const data = await res.json();
      if (res.ok) {
        setFoundId(data.ID); // 서버에서 반환한 ID 표시
      } else {
        alert(data.detail || "일치하는 정보가 없습니다.");
      }
    } catch (err) {
      alert("서버와 연결할 수 없습니다.");
    } finally {
      setFindIdLoading(false);
    }
  };

  // 비밀번호 재설정 (1단계: 본인확인)
  const handleResetStart = async (e) => {
    e.preventDefault();
    setResetLoading(true);
    try {
      const res = await fetch("http://localhost:8000/password/reset-start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ID: resetId, name: resetName, phone: resetPhone }),
      });
      const data = await res.json();
      if (res.ok) {
        setResetToken(data.reset_token); // { reset_token: "..." }
        setResetStep(2); //다음 단계로 이동
      } else {
        alert(data.detail || "입력 정보를 확인해주세요.");
      }
    } catch (err) {
      alert("서버와 연결할 수 없습니다.");
    } finally {
      setResetLoading(false);
    }
  };

  // 비밀번호 재설정 (2단계: 새 비번 입력)
  const handleResetConfirm = async (e) => {
    e.preventDefault();
    if (!pwValid) {
      alert("비밀번호는 특수문자 포함 8자리 이상이어야 합니다.");
      return;
    }
    if (pwMatchError) {
      alert("비밀번호가 일치하지 않습니다.");
      return;
    }
    setResetLoading(true);
    try {
      const res = await fetch("http://localhost:8000/password/reset-confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reset_token: resetToken, new_password: newPw }),
      });
      const data = await res.json();
      if (res.ok) {
        alert("비밀번호가 변경되었습니다. 새 비밀번호로 로그인해주세요.");
        // 상태 초기화
        setOpenResetPw(false);
        setResetStep(1);
        setResetId(''); setResetName(''); setResetPhone('');
        setNewPw(''); setNewPwConfirm(''); setResetToken(null);
      } else {
        alert(data.detail || "비밀번호 변경에 실패했습니다.");
      }
    } catch (err) {
      alert("서버와 연결할 수 없습니다.");
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div className="w-full min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md p-6 bg-white rounded-xl shadow-md">
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="id" className="block font-bold mb-1 text-lg">ID</label>
            <input
              type="text"
              id="id"
              value={id}
              onChange={(e) => setId(e.target.value)}
              placeholder="아이디를 입력하세요"
              className="w-full border border-blue-300 rounded-md px-4 py-2 bg-gray-50 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>

          <div>
            <label htmlFor="password" className="block font-bold mb-1 text-lg">PASSWORD</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호를 입력하세요"
                className="w-full border border-blue-300 rounded-md px-4 py-2 pr-10 bg-gray-50 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                className="absolute right-2 top-2 text-gray-500"
                aria-label={showPassword ? "비밀번호 숨기기" : "비밀번호 보기"}
              >
                {showPassword ? <FiEyeOff size={20} /> : <FiEye size={20} />}
              </button>
            </div>
          </div>

          <button type="submit" className="w-full py-2 bg-blue-500 text-white rounded-md font-bold hover:bg-blue-600">
            로그인
          </button>

          <div className="flex justify-end gap-4 text-sm text-gray-500 mt-2">
            <button type="button" onClick={() => setOpenFindId(true)} className="hover:underline">
              아이디 찾기
            </button>
            <span>|</span>
            <button type="button" onClick={() => setOpenResetPw(true)} className="hover:underline">
              비밀번호 찾기
            </button>
          </div>
        </form>
      </div>

      {/* === 아이디 찾기 모달 === */}
      {openFindId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center">
          <div className="w-full max-w-md bg-white rounded-xl p-6 shadow-lg">
            <h2 className="text-xl font-bold mb-4">아이디 찾기</h2>
            <form className="space-y-4" onSubmit={handleFindId}>
              <div>
                <label className="block font-semibold mb-1">이름</label>
                <input
                  type="text"
                  value={findName}
                  onChange={(e) => {
                    const input = e.target.value;
                    if (!isComposingFindName) {
                      const koreanOnly = input.replace(/[^가-힣]/g, '');
                      setFindName(koreanOnly);
                    } else {
                      setFindName(input);
                    }
                  }}
                  onCompositionStart={() => setIsComposingFindName(true)}
                  onCompositionEnd={(e) => {
                    setIsComposingFindName(false);
                    const koreanOnly = e.target.value.replace(/[^가-힣]/g, '');
                    setFindName(koreanOnly);
                  }}
                  placeholder="등록한 이름"
                  className="w-full border rounded-md px-3 py-2 bg-gray-50"
                />
              </div>
              <div>
                <label className="block font-semibold mb-1">휴대폰번호</label>
                <input
                  type="text"
                  value={findPhone}
                  onChange={(e) => setFindPhone(formatPhone(e.target.value))}
                  placeholder="010-XXXX-XXXX"
                  maxLength={13}
                  className="w-full border rounded-md px-3 py-2 bg-gray-50"
                />
              </div>
              {foundId && (
                <div className="p-3 rounded-md bg-green-50 text-green-700 text-sm">
                  ✅ 등록된 아이디: <b>{foundId}</b>
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setOpenFindId(false); setFoundId(null); setFindName(''); setFindPhone(''); }}
                  className="px-4 py-2 rounded-md bg-gray-200"
                >
                  닫기
                </button>
                <button
                  type="submit"
                  disabled={!findName || !findPhone || findIdLoading}
                  className={`px-4 py-2 rounded-md text-white ${(!findName || !findPhone || findIdLoading) ? 'bg-gray-300' : 'bg-blue-500 hover:bg-blue-600'}`}
                >
                  {findIdLoading ? '조회 중...' : '아이디 조회'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* === 비밀번호 찾기 모달 === */}
      {openResetPw && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center">
          <div className="w-full max-w-md bg-white rounded-xl p-6 shadow-lg">
            <h2 className="text-xl font-bold mb-4">비밀번호 재설정</h2>

            {resetStep === 1 ? (
              <form className="space-y-4" onSubmit={handleResetStart}>
                <div>
                  <label className="block font-semibold mb-1">아이디</label>
                  <input
                    type="text"
                    value={resetId}
                    onChange={(e) => setResetId(e.target.value)}
                    placeholder="등록한 아이디"
                    className="w-full border rounded-md px-3 py-2 bg-gray-50"
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">이름</label>
                  <input
                    type="text"
                    value={resetName}
                    onChange={(e) => setResetName(e.target.value)}
                    placeholder="등록한 이름"
                    className="w-full border rounded-md px-3 py-2 bg-gray-50"
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">휴대폰번호</label>
                  <input
                    type="text"
                    value={resetPhone}
                    onChange={(e) => setResetPhone(formatPhone(e.target.value))}
                    placeholder="010-XXXX-XXXX"
                    maxLength={13}
                    className="w-full border rounded-md px-3 py-2 bg-gray-50"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setOpenResetPw(false);
                      setResetStep(1);
                      setResetId(''); setResetName(''); setResetPhone('');
                      setNewPw(''); setNewPwConfirm(''); setResetToken(null);
                    }}
                    className="px-4 py-2 rounded-md bg-gray-200"
                  >
                    닫기
                  </button>
                  <button
                    type="submit"
                    disabled={!resetId || !resetName || !resetPhone || resetLoading}
                    className={`px-4 py-2 rounded-md text-white ${
                      (!resetId || !resetName || !resetPhone || resetLoading)
                        ? 'bg-gray-300'
                        : 'bg-blue-500 hover:bg-blue-600'
                    }`}
                  >
                    {resetLoading ? '확인 중...' : '본인 확인'}
                  </button>
                </div>
              </form>
            ) : (
              <form className="space-y-4" onSubmit={handleResetConfirm}>
                <div>
                  <label className="block font-semibold mb-1">새 비밀번호</label>
                  <div className="relative">
                    <input
                      type={showNewPw ? "text" : "password"}
                      value={newPw}
                      onInput={(e) => setNewPw(e.currentTarget.value)}
                      placeholder="특수문자 포함 8자리 이상"
                      className="w-full border rounded-md px-3 py-2 pr-10 bg-gray-50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPw(v => !v)}
                      className="absolute right-2 top-2 text-gray-500"
                    >
                      {showNewPw ? <FiEyeOff size={20} /> : <FiEye size={20} />}
                    </button>
                  </div>
                  {newPw.length > 0 && (
                    <p className={`mt-1 text-sm ${pwValid ? 'text-green-600' : 'text-red-500'}`}>
                      {pwValid ? '✅ 사용 가능한 비밀번호입니다.' : '❌ 특수문자 포함 8자리 이상이어야 합니다.'}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block font-semibold mb-1">새 비밀번호 확인</label>
                  <div className="relative">
                    <input
                      type={showNewPwConfirm ? "text" : "password"}
                      value={newPwConfirm}
                      onChange={(e) => setNewPwConfirm(e.target.value)}
                      placeholder="비밀번호 재입력"
                      className="w-full border rounded-md px-3 py-2 pr-10 bg-gray-50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPwConfirm(v => !v)}
                      className="absolute right-2 top-2 text-gray-500"
                    >
                      {showNewPwConfirm ? <FiEyeOff size={20} /> : <FiEye size={20} />}
                    </button>
                  </div>
                  {newPwConfirm.length > 0 && (
                    <p className={`mt-1 text-sm ${!pwMatchError ? 'text-green-600' : 'text-red-500'}`}>
                      {!pwMatchError ? '✅ 비밀번호가 일치합니다.' : '❌ 비밀번호가 일치하지 않습니다.'}
                    </p>
                  )}
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setOpenResetPw(false);
                      setResetStep(1);
                      setResetId(''); setResetName(''); setResetPhone('');
                      setNewPw(''); setNewPwConfirm(''); setResetToken(null);
                    }}
                    className="px-4 py-2 rounded-md bg-gray-200"
                  >
                    닫기
                  </button>
                  <button
                    type="submit"
                    disabled={!pwValid || pwMatchError || resetLoading}
                    className={`px-4 py-2 rounded-md text-white ${(!pwValid || pwMatchError || resetLoading) ? 'bg-gray-300' : 'bg-blue-500 hover:bg-blue-600'}`}
                  >
                    {resetLoading ? '변경 중...' : '비밀번호 변경'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}