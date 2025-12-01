"use client";

import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import TransfromBtn from "../UI/TransformerBtn"
import ImgInteraction from "../UI/ImgInteraction";
import CharacterBtn from "../UI/trans";
import Loading from "../UI/Loading";

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

// ✅ FastAPI 서버 베이스 URL (환경변수로 관리)
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function Home() {
  // ✅ FastAPI의 /api/todos로 직접 (현재 화면에서 사용 안 해도 유지 가능)

  const wsRef = useRef(null);
  const [msgs, setMsgs] = useState([]);

  // 상태
  const [prompt, setPrompt] = useState("");
  const [genResult_all, setGenResult] = useState("");
  const [genResult, setGenResult2] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeBtn, setActiveBtn] = useState(null);

  useEffect(() => {
    // ✅ FastAPI WS 절대주소
    const ws = new WebSocket("ws://localhost:8000/ws");
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        setMsgs((prev) => [`${msg.type}: ${msg.payload ?? msg.message}`, ...prev]);
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
    console.log(e)
    try {
      setIsGenerating(true);     // 시작
      setGenResult("");
      // const res = await apiPost("/api/generate_prompt", { prompt: e });
      const res = await apiPost("/api/generate_few", { prompt: e });
      setGenResult(res.text || "");
    } catch (e) {
      setGenResult("에러: " + e.message);
    } finally {
      setIsGenerating(false);    // 끝
    }
  };


  return (
    <main style={{ maxWidth: 680, margin: "40px auto", fontFamily: "Inter, system-ui, sans-serif" }}>
      <h1>AKS 문화유산 안내문 번역</h1>

      <section style={{ marginTop: 24 }}>
        <h2>WebSocket 메시지</h2>
        <pre style={{ whiteSpace: "pre-wrap", border: "1px solid #eee", padding: 8, maxHeight: 200, overflow: "auto" }}>
          {msgs.join("\n")}
        </pre>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>장곡사 미륵불 괘불탱 안내문</h2>

        {/* 이미지 프리뷰 */}
        <ImgInteraction />

        {/* 버튼 그룹 */}
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          <CharacterBtn sendPrompt={sendPrompt} />
        </div>

        {/* 로딩 스피너 */}
        {isGenerating && (
          <Loading />
        )}

        {/* 응답 */}
        {genResult_all && !isGenerating && (
          <div style={{ marginTop: 12, whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 8, borderRadius: 6 }}>
            <strong>응답:</strong>
            <div>{genResult_all}</div>
            <TransfromBtn sourceText = "안녕하세요."/> 
          </div>
        )}

        {/* 디버그: 현재 테스트 프롬프트 */}
        <div style={{ marginTop: 16, color: "#666", fontSize: 12 }}>
          <strong>현재 프롬프트(테스트):</strong> {prompt}
          <div className=""></div>
          
          </div>
      </section>
    </main>
  );
}
