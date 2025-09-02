// src/components/Footer.jsx
import React from "react";
import { Link } from "react-router-dom";

export default function Footer({ peekPx = 48 }) {
  return (
    <footer
      role="contentinfo"
      // ✅ 푸터 전체를 위로 살짝 끌어올려 딱 'peekPx'만큼 화면에 보이게
      style={{ marginTop: `-${peekPx}px` }}
      className="border-t bg-white"
    >
      {/* 항상 보이는 한 줄: 높이를 peekPx와 정확히 맞춤 */}
      <div
        className="max-w-6xl mx-auto px-6 flex items-center text-sm text-gray-600"
        style={{ height: `${peekPx}px` }}
      >
        <span className="font-semibold mr-2">CustomChat</span>
        <span>© {new Date().getFullYear()} All rights reserved.</span>
      </div>

      {/* 상세 섹션(스크롤하면 자연스럽게 등장) */}
      <div className="max-w-6xl mx-auto px-6 pb-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-4 text-sm text-gray-600">
          <section>
            <h4 className="font-semibold mb-2">Company</h4>
            <ul className="space-y-1">
              <li><Link to="/" className="hover:underline">About</Link></li>
              <li><Link to="/" className="hover:underline">Careers</Link></li>
              <li><Link to="/" className="hover:underline">Press</Link></li>
            </ul>
          </section>

          <section>
            <h4 className="font-semibold mb-2">Resources</h4>
            <ul className="space-y-1">
              <li><Link to="/" className="hover:underline">Docs</Link></li>
              <li><Link to="/" className="hover:underline">Blog</Link></li>
              <li><a href="mailto:support@example.com" className="hover:underline">Support</a></li>
            </ul>
          </section>

          <section>
            <h4 className="font-semibold mb-2">Legal</h4>
            <ul className="space-y-1">
              <li><Link to="/" className="hover:underline">Terms</Link></li>
              <li><Link to="/" className="hover:underline">Privacy</Link></li>
              <li><Link to="/" className="hover:underline">Security</Link></li>
            </ul>
          </section>
        </div>
      </div>
    </footer>
  );
}
