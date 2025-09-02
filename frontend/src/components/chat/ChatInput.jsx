import React, { useState, useRef } from "react";

export default function ChatInput({ onSend, loading = false }) {
  const [text, setText] = useState("");
  const [composing, setComposing] = useState(false); // 한글 조합중 여부
  const taRef = useRef(null);

  const canSend = !loading && text.trim().length > 0;

  const handleChange = (e) => setText(e.target.value);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSend) return;
    onSend(text.trim());
    setText("");
    // 필요하면 포커스 유지
    requestAnimationFrame(() => taRef.current?.focus());
  };

  const handleKeyDown = (e) => {
    // Shift+Enter는 줄바꿈, Enter 단독은 전송 (단, 조합중이면 무시)
    if (e.key === "Enter" && !e.shiftKey && !composing) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3">
      <textarea
        ref={taRef}
        value={text}                // ✅ 제어 컴포넌트
        onChange={handleChange}     // ✅ state 업데이트
        onKeyDown={handleKeyDown}
        onCompositionStart={() => setComposing(true)}
        onCompositionEnd={() => setComposing(false)}
        placeholder="메시지를 입력하세요..."
        rows={1}
        className="flex-1 resize-none rounded border px-3 py-3 outline-none focus:ring-2 focus:ring-blue-400"
      />
      <button
        type="submit"
        disabled={!canSend} // ✅ loading 또는 공백일 때 비활성화
        className={`px-4 py-2 rounded font-semibold transition
          ${canSend ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-200 text-gray-500 cursor-not-allowed"}`}
        aria-disabled={!canSend}
      >
        보내기
      </button>
    </form>
  );
}
