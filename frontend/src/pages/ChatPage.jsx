import React, { useEffect, useRef, useState } from "react";
import ChatMessageList from "../components/chat/ChatMessageList";
import ChatInput from "../components/chat/ChatInput";

/*
  변경 사항 요약
  - elapsed(경과 시간), eta(예상 총 소요 시간) 상태 추가
  - 최근 응답 시간(초)들을 durations에 저장하고 이동 평균으로 ETA 추정
  - 전송 시작 시 타이머 시작, 응답/에러 시 타이머 정지
  - ChatMessageList로 elapsed/eta 내려서 "생성 중…" 말풍선에 1s/~12s 형태로 표기
*/

export default function ChatPage() {
  const [threadId, setThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // ⏱ 경과 시간 & ETA 추정 관련 상태
  const [elapsed, setElapsed] = useState(0);           // 현재 요청의 경과 시간(초)
  const [eta, setEta] = useState(null);                // 예상 총 소요 시간(초) - null이면 미표시
  const [durations, setDurations] = useState([]);      // 과거 응답 시간(초) 기록 (최근 N개)

  // 타이머/시작시각 ref
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  // 이동 평균으로 ETA 계산 (최근 5개 기준)
  const calcETA = () => {
    const take = 5;
    const last = durations.slice(-take);
    if (last.length === 0) return 12; // 히스토리 없으면 기본 12초 가정
    const avg = last.reduce((a, b) => a + b, 0) / last.length;
    // 소수점은 올림해서 보여주기
    return Math.max(3, Math.ceil(avg)); // 최소 3초 이하로는 너무 들쭉날쭉하니 3초 하한
  };

  const startTimer = () => {
    setElapsed(0);
    startTimeRef.current = Date.now();
    // 첫 ETA 추정값 세팅
    setEta(calcETA());
    // 1초 주기로 경과 시간 증가
    timerRef.current = setInterval(() => {
      setElapsed(prev => prev + 1);
    }, 1000);
  };

  const stopTimerAndRecord = (ok = true) => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (ok && startTimeRef.current) {
      const sec = Math.max(0, (Date.now() - startTimeRef.current) / 1000);
      // 최근 10개만 유지
      setDurations(prev => {
        const next = [...prev, Math.round(sec)];
        return next.length > 10 ? next.slice(-10) : next;
      });
    }
    setEta(null);
    setElapsed(0);
    startTimeRef.current = null;
  };

  const sendMessage = async (text) => {
    // UI에 사용자 메시지 먼저 반영
    setMessages(prev => [...prev, { id: Date.now(), role: "user", content: text }]);
    setLoading(true);
    startTimer();

    try {
      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // 세션/쿠키 사용 시
        body: JSON.stringify({ message: text, thread_id: threadId }),
      });
      if (!res.ok) throw new Error("chat api error");
      const data = await res.json();
      setThreadId(data.thread_id);
      setMessages(prev => [
        ...prev,
        { id: Date.now() + 1, role: "assistant", content: data.reply }
      ]);
      stopTimerAndRecord(true);
    } catch (e) {
      setMessages(prev => [
        ...prev,
        { id: Date.now() + 2, role: "assistant", content: "문제가 발생했어요. 잠시 후 다시 시도해 주세요." }
      ]);
      stopTimerAndRecord(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100vh-64px)]">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">회사 챗봇</h1>
        <p className="text-gray-500">운영시간, 위치, 문의 등 물어보세요.</p>
      </header>

      <div className="flex-1 min-h-0">
        <div
          className="bg-white rounded-xl border shadow-sm p-4 flex flex-col
                     h-[90vh] md:h-[75vh] lg:h-[80vh]
                     max-h-[calc(100vh-180px)]"
        >
          {/* 메시지 리스트 (내부 스크롤) */}
          <div className="flex-1 min-h-0">
            <ChatMessageList
              messages={messages}
              loading={loading}
              elapsed={elapsed}
              eta={eta}
            />
          </div>

          {/* 입력창 */}
          <div className="mt-4 shrink-0">
            <ChatInput onSend={sendMessage} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  );
}
