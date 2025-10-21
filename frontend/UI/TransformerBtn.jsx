'use client';

import { useState } from 'react';

// ✅ 환경 변수에서 FastAPI 주소 불러오기
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

// ✅ POST 요청 함수
async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export default function TransfromBtn({ sourceText }) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [genResult, setGenResult] = useState('');
  const [selectedLang, setSelectedLang] = useState('');

  // ✅ 버튼 클릭 시 백엔드로 번역 요청
  const handleLangClick = async (lang) => {
    setSelectedLang(lang);
    setIsModalOpen(true);
    setIsGenerating(true);
    setGenResult('');

    try {
      // ✅ FastAPI /api/translate 호출
      const data = await apiPost('/api/translate', {
        // text: sourceText,
        text : sourceText, //이 부분에 번역할 텍스트가 들어감.
        target_lang: lang,
      });

      // ✅ 응답 결과 표시
      setGenResult(data.translation || '번역 결과를 불러오지 못했습니다.');
    } catch (err) {
      console.error(err);
      setGenResult(`⚠️ 오류 발생: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const closeModal = () => setIsModalOpen(false);

  return (
    <>
      <button onClick={() => handleLangClick('영어')}>영어</button>
      <button onClick={() => handleLangClick('일본어')}>일본어</button>
      <button onClick={() => handleLangClick('중국어')}>중국어</button>
      <button onClick={() => handleLangClick('스와힐리어')}>스와힐리어</button>


      {isModalOpen && (
        <>
          <div className="overlay" onClick={closeModal} />
          <div className="modal" role="dialog" aria-modal="true">
            <div style={{ fontWeight: 600, marginBottom: 8 }}>
              요청 언어: {selectedLang}
            </div>

            {isGenerating ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div className="spinner" />
                <span>번역 중...</span>
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

            <button onClick={closeModal} className="closeBtn" style={{ marginTop: 12 }}>
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
    </>
  );
}
