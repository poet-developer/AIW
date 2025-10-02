'use client'

import { useState } from 'react';

export default function TransfromBtn() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [genResult, setGenResult] = useState('');
  const [selectedLang, setSelectedLang] = useState('');

  const handleLangClick = (lang) => {
    setSelectedLang(lang);
    setIsModalOpen(true);
    setIsGenerating(true);
    setGenResult('');

    // 1초 후 임시 응답 표시
    setTimeout(() => {
      setGenResult(`"${lang}" 번역 테스트 응답입니다.\n여기에 생성된 텍스트가 표시됩니다.`);
      setIsGenerating(false);
    }, 1000);
  };

  const closeModal = () => setIsModalOpen(false);

  return (
    <>
      <button onClick={() => handleLangClick('영어')}>영어</button>
      <button onClick={() => handleLangClick('일본어')}>일본어</button>
      <button onClick={() => handleLangClick('중국어')}>중국어</button>

      {/* 모달 */}
      {isModalOpen && (
        <>
          <div className="overlay" onClick={closeModal} />
          <div className="modal" role="dialog" aria-modal="true" aria-label="응답 모달">
            <div style={{ fontWeight: 600, marginBottom: 8 }}>
              요청 언어: {selectedLang}
            </div>

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
    </>
  );
}
