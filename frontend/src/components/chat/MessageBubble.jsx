import React from "react";

/**
 * role: 'user' | 'assistant' | 'system'
 * content: string
 */
export default function MessageBubble({ role = "user", content = "" }) {
  const isUser = role === "user";
  const isAssistant = role === "assistant";

  // system 메시지는 필요 없으면 숨길 수도 있습니다.
  if (role === "system") return null;

  return (
    <div className={`w-full flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={[
          "max-w-[80%] rounded-2xl px-4 py-2 shadow-sm whitespace-pre-wrap break-words",
          isUser ? "bg-blue-600 text-white" : "bg-white text-gray-900 border",
        ].join(" ")}
      >
        {content}
      </div>
    </div>
  );
}
