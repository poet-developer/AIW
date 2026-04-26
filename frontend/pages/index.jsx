"use client";

import { useEffect, useRef, useState } from "react";
import ImgInteraction from "../UI/ImgInteraction";
import CharacterBtn from "../UI/trans";

// import SvgPathClickModal from '../UI/SVG';

// ✅ FastAPI 서버 베이스 URL (환경변수로 관리)
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";


async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`POST ${path} failed: ${res.status} ${t}`);
  }
  return res.json();
}

export default function Home() {
  const wsRef = useRef(null);
  const [msgs, setMsgs] = useState([]);

  // 🔹 프롬프트 관련 상태 추가
  const [prompt, setPrompt] = useState("");
  const [genResult, setGenResult] = useState("");

  useEffect(() => {
    // ✅ FastAPI WS 절대주소 : 연결확인용
    const ws = new WebSocket("ws://localhost:8000/ws");
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        setMsgs((prev) => [
          `${msg.type}: ${msg.payload ?? msg.message}`,
          ...prev,
        ]);
      } catch (e) {
        setMsgs((prev) => [evt.data, ...prev]);
      }
    };
    ws.onopen = () => {
      try {
        ws.send("hello from browser");
      } catch {}
    };
    return () => {
      try {
        ws.close();
      } catch {}
    };
  }, []);
 
  // ✅ 프롬프트 전송 (FastAPI의 /api/generate_raw 사용)
  const sendPrompt = async (e) => {
    try {
      setIsGenerating(true);     // 시작
      setGenResult("");
      console.log(e);
      const res = await apiPost("/api/graph-cypher-qa", { prompt: e });
      // const test = await apiPost("/api/test", e );
      // console.log(test);
      setGenResult(res.text || "");
      // setGenResult((test.results || []).join("\n\n"));
    } catch (e) {
      console.error(e);
      setGenResult("에러: " + e.message);
    } finally {
      setIsGenerating(false);    // 끝
    }
  };

  // 🔹 새 상태 추가
  const [isGenerating, setIsGenerating] = useState(false);

  return (
    <main style={{ maxWidth: 680, margin: "40px auto", fontFamily: "Inter, system-ui, sans-serif" }}>
      <h1>AKS 문화유산 안내문 번역</h1>

      <section style={{ marginTop: 24 }}>
        <h2>WebSocket 메시지</h2>
        <pre style={{ whiteSpace: "pre-wrap", border: "1px solid #eee", padding: 8, maxHeight: 200, overflow: "auto" }}>
          {msgs.join("\n")}
        </pre>
      </section>
        <ImgInteraction />
      <section style={{ marginTop: 24 }}>

        {/* 버튼 그룹 */}
                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <CharacterBtn sendPrompt={sendPrompt} />
                </div>
        <h2>장곡사 미륵불 괘불탱 안내문</h2>
        

        {/* 로딩 스피너 */}
        {isGenerating && (
          <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <div className="spinner" />
            <span>응답을 생성 중...</span>
            <style jsx>{`
              .spinner {
                width: 18px;
                height: 18px;
                border: 3px solid #ccc;
                border-top-color: #333;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
              }
              @keyframes spin {
                to {
                  transform: rotate(360deg);
                }
              }
              
            `}</style>
          </div>
        )}

        {/* 응답 */}
        {genResult && !isGenerating && (
          <div style={{ marginTop: 12, whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 8 }}>
            <strong>응답:</strong>
            <div>{genResult}</div>
          </div>
        )}
      </section>
      
    </main>
  );
}
