'use client';

import { useEffect, useRef, useState } from 'react';

export default function CharacterBtn({ sendPrompt }) {

// 디자인
const [activeBtn, setActiveBtn] = useState(null);    

    return (
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
            );
}