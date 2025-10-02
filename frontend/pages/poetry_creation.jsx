"use client";

import { useState } from "react";

export default function Home() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("idle"); // 타입 지정 제거
  const [output, setOutput] = useState("");

  const handleSubmit = async () => {
    setLoading(true);
    setOutput("");
    setLoadingStep("thinking"); // 1단계

    await new Promise((resolve) => setTimeout(resolve, 2000));
    setLoadingStep("writing"); // 2단계

    await new Promise((resolve) => setTimeout(resolve, 3000));
    setOutput(`✅ 결과: "${input}"에 대한 응답 텍스트`);

    setLoading(false);
    setLoadingStep("idle");
  };

  return (
    <main style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>Next.js Input → Output Demo</h1>

      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="텍스트를 입력하세요"
        style={{
          width: "100%",
          padding: "8px",
          border: "1px solid #ccc",
          borderRadius: "6px",
          marginBottom: "12px",
        }}
      />

      <button
        onClick={handleSubmit}
        disabled={loading || !input.trim()}
        style={{
          background: "#000",
          color: "#fff",
          padding: "10px 16px",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        {loading ? "로딩 중..." : "전송"}
      </button>

      <div style={{ marginTop: "20px", minHeight: "40px" }}>
        {loading && loadingStep === "thinking" && <p>💡 영감을 받는중...</p>}
        {loading && loadingStep === "writing" && <p>✍️ 시를 짓는중...</p>}
        {!loading && output && (
          <p
            style={{
              whiteSpace: "pre-wrap",
              border: "1px solid #eee",
              padding: "8px",
              borderRadius: "6px",
            }}
          >
            {output}
          </p>
        )}
      </div>
    </main>
  );
}
