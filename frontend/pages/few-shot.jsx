"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import useSWR from "swr";
import ImgInteraction from "../UI/ImgInteraction";
import CharacterBtn from "../UI/trans";
// import SvgPathClickModal from '../UI/SVG';

// ✅ FastAPI 서버 베이스 URL (환경변수로 관리)
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";


async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}
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
// async function apiPatch(path) {
//   const res = await fetch(`${API_BASE}${path}`, { method: "PATCH" });
//   if (!res.ok) throw new Error(`PATCH ${path} failed: ${res.status}`);
//   return res.json();
// }
// async function apiDelete(path) {
//   const res = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
//   if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
// }

export default function Home() {
  // ✅ FastAPI의 /api/todos로 직접
  const [title, setTitle] = useState("");
  const wsRef = useRef(null);
  const [msgs, setMsgs] = useState([]);

  // 🔹 프롬프트 관련 상태 추가
  const [prompt, setPrompt] = useState("");
  const [genResult, setGenResult] = useState("");

  // 디자인

  const [activeBtn, setActiveBtn] = useState(null);

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

      <section style={{ marginTop: 24 }}>
        <h2>장곡사 미륵불 괘불탱 안내문</h2>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="프롬프트를 입력하세요..."
          rows={4}
          style={{ width: "100%", padding: 8 }}
        />
        <ImgInteraction />
        <CharacterBtn sendPrompt={sendPrompt} />
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          {/* 버튼 클릭시 sendPrompt 함수 호출 */}
          <div>
          <button
            onClick = {() => {
              setActiveBtn("expert");
              sendPrompt("예시1, 예시2, 예시3에서는 문체를 반영하고 예시4, 예시5, 예시6, 예시7의 내용을 토대로 장곡사 미륵불 괘불탱에 대한 국가유산 안내문을 내국인 아동을 대상으로 생성해 줘.");
            }}
            className={activeBtn === "expert" ? "btn active" : "btn"}
          >
            내국인 아동
          </button>
          <button
            onClick={() => {
              setActiveBtn("normal");
              sendPrompt("예시1, 예시2, 예시3에서는 문체를 반영하고 예시4, 예시5, 예시6, 예시7의 내용을 토대로 장곡사 미륵불 괘불탱에 대한 국가유산 영어 안내문을 외국인 아동을 대상으로 생성해 줘.");
            }}
            className={activeBtn === "normal" ? "btn active" : "btn"}
          >
            외국인 아동
          </button>
          </div>
          <hr></hr>
          <button
            onClick={() => {
              setActiveBtn("easy");
              sendPrompt("예시4, 예시5, 예시6, 예시7의 내용과 문체를 토대로 장곡사 미륵불 괘불탱에 대한 국가유산 안내문을 내국인 일반을 대상으로 생성해 줘.");
            }}
            className={activeBtn === "easy" ? "btn active" : "btn"}
          >
            내국인 일반
          </button>
          <button
            onClick={() => {
              setActiveBtn("easy");
              sendPrompt("예시4, 예시5, 예시6의 내용을 토대로 예시 7의 스타일로 장곡사 미륵불 괘불탱에 대한 국가유산 영어 안내문을 외국인 일반을 대상으로 생성해 줘.");
            }}
            className={activeBtn === "easy" ? "btn active" : "btn"}
          >
            외국인 일반
          </button>
          <hr></hr>
          <div>
          <button
            onClick={() => {
              setActiveBtn("easy");
              sendPrompt("예시4, 예시5, 예시6, 예시7의 내용과 문체를 토대로 장곡사 미륵불 괘불탱에 대한 국가유산 안내문을 내국인 시니어를 대상으로 생성해 줘.");
            }}
            className={activeBtn === "easy" ? "btn active" : "btn"}
          >
            내국인 시니어
          </button>
          <button
            onClick={() => {
              setActiveBtn("easy");
              sendPrompt("예시4, 예시5, 예시6의 내용을 토대로 예시7의 스타일로 장곡사 미륵불 괘불탱에 대한 국가유산 영어 안내문을 외국인 시니어를 대상으로 생성해 줘.");
            }}
            className={activeBtn === "easy" ? "btn active" : "btn"}
          >
            외국인 시니어
          </button>
          </div>
          <hr></hr>
          <div>
          <button
            onClick={() => {
              setActiveBtn("easy");
              sendPrompt("예시5, 예시6의 내용과 문체를 토대로 장곡사 미륵불 괘불탱에 대한 국가유산 안내문을 내국인 전문가를 대상으로 생성해 줘. ");
            }}
            className={activeBtn === "easy" ? "btn active" : "btn"}
          >
            내국인 전문가
          </button>
            <button
            onClick={() => {
              setActiveBtn("easy");
              sendPrompt("예시5, 예시6의 내용과 문체를 토대로 예시7의 스타일로 장곡사 미륵불 괘불탱에 대한 국가유산 영어 안내문을 외국인 전문가를 대상으로 생성해 줘.");
            }}
            className={activeBtn === "easy" ? "btn active" : "btn"}
          >
            외국인 전문가
          </button>
         </div>
          <style jsx>{`
            .btn {
              padding: 8px 12px;
              border: none;
              border-radius: 6px;
              cursor: pointer;
              transition: all 0.2s ease;
            }
            .btn:active {
              transform: scale(0.95); /* 클릭 시 살짝 줄어듦 */
              opacity: 0.8;
            }
            .btn.active {
              box-shadow: 0 0 10px rgba(0, 0, 0, 0.3); /* 눌린 버튼 강조 */
            }
            .btn:nth-child(1) {
              background: #222;
              color: #fff;
            }
            .btn:nth-child(2) {
              background: #0066cc;
              color: #fff;
            }
          `}</style>
        </div>

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
