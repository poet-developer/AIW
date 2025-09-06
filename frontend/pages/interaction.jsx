"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import useSWR from "swr";

import SvgPathClickModal from '../UI/SVG';

// ✅ FastAPI 서버 베이스 URL (환경변수로 관리)
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";


const sendPrompt = async () => {
  if (!prompt.trim()) return;
  try {
    setIsGenerating(true);     // 시작
    setGenResult("");
    const res = await apiPost("/api/generate_raw", { prompt });
    setGenResult(res.text || "");
  } catch (e) {
    setGenResult("에러: " + e.message);
  } finally {
    setIsGenerating(false);    // 끝
  }
};


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
  const { data, mutate, isLoading, error } = useSWR("/api/todos", apiGet);
  const [title, setTitle] = useState("");
  const wsRef = useRef(null);
  const [msgs, setMsgs] = useState([]);

  // 🔹 프롬프트 관련 상태 추가
//   const [prompt, setPrompt] = useState("");
//   const [genResult, setGenResult] = useState("");

  useEffect(() => {
    // ✅ FastAPI WS 절대주소
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
 
  // ===== 프롬프트/생성 결과를 모달에서 관리 =====
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [genResult, setGenResult] = useState('');
  const FIXED_PROMPT = '장곡사 미륵불 괘불탱의 연꽃에 대해서 설명해줘';

  // SVG 클릭 시: 모달 열고 → API 호출
  const handleSvgClick = async () => {
    setIsModalOpen(true);
    setIsGenerating(true);
    setGenResult('');
    try {
      const res = await apiPost('/api/generate_raw', { prompt: FIXED_PROMPT });
      setGenResult(res.text || '');
    } catch (e) {
      setGenResult('에러: ' + e.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const closeModal = () => setIsModalOpen(false);

  return (
    <main style={{ maxWidth: 680, margin: '40px auto', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <h1>FastAPI × Next.js (JS/Pages)</h1>

      {/* WebSocket 로그 */}
      <section style={{ marginTop: 24 }}>
        <h2>WebSocket 메시지</h2>
        <pre style={{ whiteSpace: 'pre-wrap', border: '1px solid #eee', padding: 8, maxHeight: 200, overflow: 'auto' }}>
          {msgs.join('\n')}
        </pre>
      </section>

      {/* SVG 클릭 → 모달에서 응답 생성 */}
      <section style={{ marginTop: 24 }}>
        <h2>SVG 클릭으로 프롬프트 전송</h2>
        <p style={{ color: '#555' }}>경로를 클릭하면 고정 프롬프트가 전송되고, 결과가 모달에 표시됩니다.</p>

        <SvgPathClickModal onPathClick={handleSvgClick} />

        {/* 모달 */}
        {isModalOpen && (
          <>
            <div className="overlay" onClick={closeModal} />
            <div className="modal" role="dialog" aria-modal="true" aria-label="응답 모달">
              <div style={{ fontWeight: 600, marginBottom: 8 }}>요청 프롬프트</div>
              <div style={{ fontSize: 14, color: '#555', marginBottom: 12 }}>{FIXED_PROMPT}</div>

              {isGenerating ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="spinner" />
                  <span>응답을 생성 중...</span>
                </div>
              ) : (
                <div
                  style={{
                    whiteSpace: 'pre-wrap',
                    border: '1px solid #ddd',
                    padding: 8,
                    borderRadius: 6,
                    maxHeight: 260,
                    overflow: 'auto',
                  }}
                >
                  {genResult || '응답이 비어 있습니다.'}
                </div>
              )}

              <button className="closeBtn" onClick={closeModal} style={{ marginTop: 12 }}>
                닫기
              </button>
            </div>

            <style jsx>{`
              .overlay {
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.3);
                z-index: 999;
              }
              .modal {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: min(640px, 92vw);
                max-height: 80vh;
                overflow: auto;
                background: #fff;
                border: 2px solid #000;
                padding: 16px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
                z-index: 1000;
                border-radius: 10px;
              }
              .closeBtn {
                cursor: pointer;
                background: #000;
                color: #fff;
                padding: 8px 12px;
                border: none;
                border-radius: 8px;
              }
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
          </>
        )}
      </section>
    </main>
  );
}
