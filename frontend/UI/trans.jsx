'use client';

import { useEffect, useRef, useState } from 'react';

export default function CharacterBtn({ sendPrompt }) {

// 디자인
const [activeBtn, setActiveBtn] = useState(null);    

  // ✅ 모달 제어
  const [langModalOpen, setLangModalOpen] = useState(false);
  const [foreignDepth, setForeignDepth] = useState(null); // "아동" | "일반" | "시니어" | "전문가"

  const openLangModal = (depth) => {
    setForeignDepth(depth);
    setLangModalOpen(true);
  };

  const closeLangModal = () => {
    setLangModalOpen(false);
    setForeignDepth(null);
  };

  const chooseLang = (lang) => {
    sendPrompt({ role: "외국인", depth: foreignDepth, detail: lang });
    closeLangModal();
  };

    return (
    <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            {/* 버튼 클릭시 sendPrompt 함수 호출 */}
            <div>
            <button
                onClick = {() => {
                setActiveBtn(true);
                sendPrompt({role:"내국인", depth:"아동", detail:"한국어"});
                }}
                className={activeBtn === true ? "btn active" : "btn"}
            >
                내국인 아동
            </button>
            <button
          onClick={() => {
            setActiveBtn(true);
            openLangModal("아동");   // ✅ 외국인 버튼은 모달 열기
          }}
          className={activeBtn === true ? "btn active" : "btn"}
        >
          외국인 아동
        </button>
            </div>
            <hr></hr>
            <button
                onClick={() => {
                setActiveBtn(true);
                sendPrompt({role:"내국인", depth:"일반", detail:"한국어"});
                }}
                className={activeBtn === true ? "btn active" : "btn"}
            >
                내국인 일반
            </button>
            <button
          onClick={() => {
            setActiveBtn(true);
            openLangModal("일반");   // ✅ 외국인 버튼은 모달 열기
          }}
          className={activeBtn === true ? "btn active" : "btn"}
        >
                외국인 일반
            </button>
            <hr></hr>
            <div>
            <button
                onClick={() => {
                setActiveBtn(true);
                sendPrompt({role:"내국인", depth:"시니어", detail:"한국어"});
                }}
                className={activeBtn === true ? "btn active" : "btn"}
            >
                내국인 시니어
            </button>
            <button
          onClick={() => {
            setActiveBtn(true);
            openLangModal("시니어");   // ✅ 외국인 버튼은 모달 열기
          }}
          className={activeBtn === true ? "btn active" : "btn"}
        >
                외국인 시니어
            </button>
            </div>
            <hr></hr>
            <div>
            <button
                onClick={() => {
                setActiveBtn(true);
                sendPrompt({role:"내국인", depth:"전문가", detail:"한국어"});
                }}
                className={activeBtn === true ? "btn active" : "btn"}
            >
                내국인 전문가
            </button>
                <button
          onClick={() => {
            setActiveBtn(true);
            openLangModal("전문가");   // ✅ 외국인 버튼은 모달 열기
          }}
          className={activeBtn === true ? "btn active" : "btn"}
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

             {/* ✅ 모달 */}
      {langModalOpen && (
        <div className="modalOverlay" onClick={closeLangModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modalHeader">
              <div className="modalTitle">언어 선택</div>
              <div className="modalSub">외국인 · {foreignDepth}</div>
            </div>

            <div className="langGrid">
              {["중국어", "일본어", "영어", "스와힐리어"].map((lang) => (
                <button key={lang} className="langBtn" onClick={() => chooseLang(lang)}>
                  {lang}
                </button>
              ))}
            </div>

            <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
              <button className="btn" onClick={closeLangModal}>닫기</button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .btn {
          padding: 8px 12px;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
          margin-right: 8px;
          background: #222;
          color: #fff;
        }
        .btn.active {
          box-shadow: 0 0 10px rgba(0,0,0,0.25);
        }
        hr {
          border: none;
          border-top: 1px solid #e5e5e5;
          margin: 6px 0;
        }

        /* ✅ Modal */
        .modalOverlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.45);
          display: flex;
          align-items: flex-end; /* 하단부 모달 느낌 */
          justify-content: center;
          padding: 16px;
          z-index: 9999;
        }
        .modal {
          width: 100%;
          max-width: 520px;
          background: #fff;
          border-radius: 16px;
          padding: 16px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }
        .modalHeader {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 12px;
        }
        .modalTitle {
          font-weight: 800;
          font-size: 16px;
        }
        .modalSub {
          color: #666;
          font-size: 13px;
        }
        .langGrid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
        }
        .langBtn {
          padding: 12px;
          border-radius: 12px;
          border: 1px solid #ddd;
          background: #f7f7f7;
          cursor: pointer;
          font-weight: 700;
        }
        .langBtn:active {
          transform: scale(0.98);
          opacity: 0.9;
        }
      `}</style>
            </div>
            );
}