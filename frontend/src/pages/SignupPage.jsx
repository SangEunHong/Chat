import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiEye, FiEyeOff } from "react-icons/fi";

/**
 * SignupPage.jsx
 * - 회원가입 폼 (ID 중복 확인, 비밀번호 규칙/일치, 이름 한글 입력, 생년월일/휴대폰 포맷)
 * - 성공 시 메인으로 이동
 */

function SignupPage() {
  //폼 상태
  const [ID, setID] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [bdate, setBdate] = useState('');
  const [phone, setPhone] = useState('');

  //UI상태(비밀번호 보이기/숨기기)
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const navigate = useNavigate();

  //유효성/부가 상태
  const [isIDAvailable, setIsIDAvailable] = useState(null); // true / false / null=미확인
  const [passwordValid, setPasswordValid] = useState(null);
  const [passwordMatchError, setPasswordMatchError] = useState("");
  const [isComposing, setIsComposing] = useState(false); //한글 IME 조합 중 여부

  //핸들러: ID 중복 확인
  const handleCheckID = async () => { 
    try {
      const response = await fetch(`http://localhost:8000/check-id?ID=${ID}`);
      const data = await response.json();
      console.log("✅ check-id 응답:", data);
      setIsIDAvailable(data.available); // true/false만 저장
    } catch (error) {
      console.error("ID 중복 확인 중 오류 발생", error);
      setIsIDAvailable(false);
    }
  };

  //비밀번호 규칙 검사(특수문자 포함 8자 이상)
  const validatePassword = (pw) => { 
    const regex = /^(?=.*[!@#$%^&*(),.?":{}|<>])[A-Za-z\d!@#$%^&*(),.?":{}|<>]{8,}$/;
    return regex.test(pw);
  };

  //핸들러: 비밀번호 입력 변경
  const handlePasswordChange = (e) => {
    const pw = e.target.value;
    setPassword(pw);
    setPasswordValid(validatePassword(pw));
    setPasswordMatchError(
      confirmPassword && pw !== confirmPassword ? "비밀번호가 일치하지 않습니다." : ""
    );
  };

  //핸들러: 비밀번호 확인 입력 변경
  const handleConfirmPasswordChange = (e) => {
    const value = e.target.value;
    setConfirmPassword(value);
    setPasswordMatchError(
      password && value !== password ? "비밀번호가 일치하지 않습니다." : ""
    );
  };

  //핸들러: 이름(한글만, IME 조합 고려)
  const handleNameChange = (e) => { // 이름은 한국어만
    const input = e.target.value;
    if (!isComposing) {
      const koreanOnly = input.replace(/[^가-힣]/g, '');
      setName(koreanOnly);
    } else {
      setName(input); // 조합 중엔 그대로 유지
    }
  };
  //핸들러: 생년월일 숫자 입력->YYYY-MM-DD 포맷팅
  const handleBdateChange = (e) => { 
    const raw = e.target.value.replace(/[^0-9]/g, ''); 
    let formatted = raw;

    if (raw.length >= 5 && raw.length <= 6)
      formatted = raw.slice(0, 4) + '-' + raw.slice(4);
    else if (raw.length >= 7)
      formatted = raw.slice(0, 4) + '-' + raw.slice(4, 6) + '-' + raw.slice(6, 8);

    setBdate(formatted);
  };
  //제출: 클라이언트 검증-> /signup POST -> 성공 시 이동
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!passwordValid) {
      alert("비밀번호는 특수문자 포함 8자리 이상이어야 합니다.");
      return;
    }
    if (password !== confirmPassword) {
      alert("비밀번호가 일치하지 않습니다.");
      return;
    }
    if (isIDAvailable !== true) {
      alert("ID 중복 확인이 필요합니다.");
      return;
    }

    const payload = { ID, password, name, bdate, phone };

    try {
      const response = await fetch('http://localhost:8000/signup/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json(); //서버 응답 로그/확인용
        alert('회원가입 성공!');
        console.log(data);
        navigate('/');
      } else {
        //Pydantic 에러 배열 or 단일 detail 문자열 처리
        const errorData = await response.json();
        if (Array.isArray(errorData.detail)) {
          alert("회원가입 실패: " + errorData.detail.map(err => err.msg).join("\n"));
        } else {
          alert("회원가입 실패: " + (errorData.detail || "알 수 없는 오류"));
        }
      }
    } catch (error) {
      alert('서버와 연결되지 않았습니다.');
      console.error(error);
    }
  };

  return (
    <div className="flex h-screen">
      {/* 오른쪽 회원가입 폼 */}
      <div className="flex-1 bg-gray-50 flex justify-center items-center">
        <div className="w-full max-w-md p-6 bg-white rounded-xl shadow-md">
          <form className="space-y-4" onSubmit={handleSubmit}>
            {/* ID */}
            <div>
              <label className="block font-bold mb-1">ID</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="ID입력 후 중복 확인버튼"
                  value={ID}
                  onChange={(e) => {
                    setID(e.target.value);
                    setIsIDAvailable(null); // ID 바뀌면 다시 검사
                  }}
                  className="flex-1 border border-blue-300 rounded-md px-4 py-2 bg-gray-50 placeholder-gray-400"
                />
                <button
                  type="button"
                  onClick={handleCheckID}
                  className="px-4 py-2 bg-blue-500 text-white rounded-md font-semibold hover:bg-blue-600"
                >
                  중복 확인
                </button>
              </div>
              {isIDAvailable === false && (
                <p className="text-red-500 text-sm mt-1">❌ 이미 사용 중인 ID입니다.</p>
              )}
              {isIDAvailable === true && (
                <p className="text-green-600 text-sm mt-1">✅ 사용 가능한 ID입니다.</p>
              )}
            </div>

            {/* PASSWORD */}
            <div>
              <label className="block font-bold mb-1">PASSWORD</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="특수문자 포함 8자리 이상"
                  value={password}
                  onChange={handlePasswordChange}
                  className="w-full border border-blue-300 rounded-md px-4 py-2 pr-10 bg-gray-50 placeholder-gray-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-2 text-gray-500"
                >
                  {showPassword ? <FiEyeOff size={20} /> : <FiEye size={20} />}
                </button>
              </div>
              {password.length > 0 && (
                <p className={`mt-1 text-sm ${passwordValid ? 'text-green-600' : 'text-red-500'}`}>
                  {passwordValid ? '✅ 사용 가능한 비밀번호입니다.' : '❌ 특수문자 포함 8자리 이상이어야 합니다.'}
                </p>
              )}
            </div>

            {/* PASSWORD CONFIRM */}
            <div>
              <label className="block font-bold mb-1">비밀번호 확인</label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="비밀번호 재입력"
                  value={confirmPassword}
                  onChange={handleConfirmPasswordChange}
                  className="w-full border border-blue-300 rounded-md px-4 py-2 pr-10 bg-gray-50 placeholder-gray-400"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-2 top-2 text-gray-500"
                >
                  {showConfirmPassword ? <FiEyeOff size={20} /> : <FiEye size={20} />}
                </button>
              </div>
              {confirmPassword.length > 0 && (
                <p className={`mt-1 text-sm ${!passwordMatchError ? 'text-green-600' : 'text-red-500'}`}>
                  {!passwordMatchError ? '✅ 비밀번호가 일치합니다.' : passwordMatchError}
                </p>
              )}
            </div>

            {/* 이름 */}
            <div>
              <label className="block font-bold mb-1">이름</label>
              <input
                type="text"
                placeholder="OOO"
                value={name}
                onChange={handleNameChange}
                onCompositionStart={() => setIsComposing(true)}
                onCompositionEnd={(e) => {
                  setIsComposing(false);
                  const koreanOnly = e.target.value.replace(/[^가-힣]/g, '');
                  setName(koreanOnly);
                }}
                className="w-full border border-blue-300 rounded-md px-4 py-2 bg-gray-50 placeholder-gray-400"
              />
            </div>

            {/* 생년월일 */}
            <div>
              <label className="block font-bold mb-1">생년월일</label>
              <input
                type="text"
                placeholder="YYYY-MM-DD"
                value={bdate}
                onChange={handleBdateChange}
                className="w-full border border-blue-300 rounded-md px-4 py-2 bg-gray-50 placeholder-gray-400"
              />
            </div>

            {/* 휴대폰번호 */}
            <div>
              <label className="block font-bold mb-1">휴대폰번호</label>
              <input
                type="text"
                placeholder="010-XXXX-XXXX"
                value={phone}
                onChange={(e) => {
                  const raw = e.target.value.replace(/\D/g, ''); // 숫자만
                  let formatted = raw;
                  if (raw.length <= 3) {
                    formatted = raw;
                  } else if (raw.length <= 7) {
                    formatted = raw.slice(0, 3) + '-' + raw.slice(3);
                  } else if (raw.length <= 11) {
                    formatted = raw.slice(0, 3) + '-' + raw.slice(3, 7) + '-' + raw.slice(7, 11);
                  }
                  setPhone(formatted);
                }}
                maxLength={13}
                className="w-full border border-blue-300 rounded-md px-4 py-2 bg-gray-50 placeholder-gray-400"
              />
            </div>

            {/* 회원가입 버튼 */}
            <div className="pt-4">
              <button
                type="submit"
                disabled={!passwordValid || isIDAvailable !== true || passwordMatchError}
                className={`w-full py-2 rounded-md font-bold transition ${
                  passwordValid && isIDAvailable === true && !passwordMatchError
                    ? 'bg-blue-500 hover:bg-blue-600 text-white'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                회원가입
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default SignupPage;
