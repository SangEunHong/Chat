import React, { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

/**
 * messages: { id: string|number, role: 'user'|'assistant'|'system', content: string }[]
 * loading?: boolean
 * elapsed?: number      // ⏱ 현재 요청의 경과 시간(초)
 * eta?: number | null   // ⏳ 예상 총 소요 시간(초). null이면 미표시
 */
export default function ChatMessageList({
  messages = [],
  loading = false,
  elapsed = 0,
  eta = null,
}) {
  // ✅ 스크롤은 이 엘리먼트 내부에서만 일어나게 한다
  const scrollRef = useRef(null);

  // 새 메시지/로딩/시간 변화 시 내부 스크롤을 맨 아래로
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, loading, elapsed, eta]);

  // 생성 중 문구: "답변을 생성하는 중… 5s / ~12s" (eta 없으면 "5s"만)
  const loadingText = `답변을 생성하는 중… ${elapsed}s${eta ? ` / ~${eta}s` : ""}`;

  return (
    <div
      ref={scrollRef}
      className="h-full overflow-y-auto px-3 py-2 space-y-2"
    >
      {messages.map((m) => (
        <MessageBubble key={m.id} role={m.role} content={m.content} />
      ))}

      {loading && <MessageBubble role="assistant" content={loadingText} />}
    </div>
  );
}