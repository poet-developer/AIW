'use client';

import { useEffect, useRef, useState } from 'react';
import TransfromBtn from "./TransformerBtn"

export default function ImgInteraction() {
  const containerRef = useRef(null);
  const [hoverId, setHoverId] = useState(null);
  const [selected, setSelected] = useState(null); // { id, label }
  const [tooltip, setTooltip] = useState(null);   // { x, y, text }

  // 🔳 데모용 사각형 핫스팟들 (비율 단위: 0~100, 이미지 크기와 무관하게 반응형)
  const hotspots = [
    { id: 'hs-1', x: 38, y: 5, w: 25, h: 16, label: '머리 광배 영역' },
    { id: 'hs-2', x: 45, y: 30, w: 20, h: 18, label: '연꽃 가지' },
  ];

  const imgSrc ="https://bkksg-images.s3.ap-northeast-2.amazonaws.com/raw/%E1%84%80%E1%85%AE%E1%86%A8%E1%84%87%E1%85%A9+%E1%84%8C%E1%85%A1%E1%86%BC%E1%84%80%E1%85%A9%E1%86%A8%E1%84%89%E1%85%A1+%E1%84%86%E1%85%B5%E1%84%85%E1%85%B3%E1%86%A8%E1%84%87%E1%85%AE%E1%86%AF+%E1%84%80%E1%85%AB%E1%84%87%E1%85%AE%E1%86%AF%E1%84%90%E1%85%A2%E1%86%BC(2014%E1%84%82%E1%85%A7%E1%86%AB+%E1%84%80%E1%85%AE%E1%86%A8%E1%84%87%E1%85%A9+%E1%84%83%E1%85%A9%E1%86%BC%E1%84%89%E1%85%A1%E1%86%AB+%E1%84%8B%E1%85%A2%E1%86%B8%E1%84%89%E1%85%A1%E1%84%8C%E1%85%B5%E1%86%AB).jpg"

  // ⚙️ 툴팁 위치를 클릭 지점 기준으로 설정
  const handleRectClick = (e, hs) => {
    const rect = containerRef.current?.getBoundingClientRect();
    const clickX = e.clientX - (rect?.left || 0);
    const clickY = e.clientY - (rect?.top || 0);
    setSelected(hs);
    setTooltip({ x: clickX, y: clickY, text: hs.label });
  };

  // ESC로 선택 해제
  useEffect(() => {
    const onKey = (ev) => {
      if (ev.key === 'Escape') {
        setSelected(null);
        setTooltip(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <figure className="img_box" ref={containerRef} style={styles.figure}>
      {/* 이미지 */}
      <img
        src={imgSrc}
        alt="장곡사 미륵불 괘불탱"
        loading="lazy"
        decoding="async"
        style={{width: "50vw"}}
      />

      {/* ✅ 오버레이 SVG (이미지와 동일 컨테이너 내 절대 배치) */}
      <svg
        role="presentation"
        aria-hidden="true"
        style={styles.overlay}
//           decoding="async"
//           style={{width: "50vw"}}
//         />
      />

      {/* ✅ 오버레이 SVG (이미지와 동일 컨테이너 내 절대 배치) */}
      <svg
        role="presentation"
        aria-hidden="true"
        style={styles.overlay}
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        {hotspots.map((hs) => {
          const isHover = hoverId === hs.id;
          const isActive = selected?.id === hs.id;
          return (
            <g key={hs.id}>
              {/* 클릭 영역 */}
              <rect
                x={hs.x}
                y={hs.y}
                width={hs.w}
                height={hs.h}
                rx="1.5"
                ry="1.5"
                tabIndex={0}
                aria-label={hs.label}
                onMouseEnter={() => setHoverId(hs.id)}
                onMouseLeave={() => setHoverId(null)}
                onFocus={() => setHoverId(hs.id)}
                onBlur={() => setHoverId(null)}
                onClick={(e) => handleRectClick(e, hs)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleRectClick(e, hs);
                  }
                }}
                style={{
                  cursor: 'pointer',
                  fill: isActive ? 'rgba(0,0,0,0.18)' : isHover ? 'rgba(0,0,0,0.10)' : 'transparent',
                  stroke: isActive ? '#111' : isHover ? '#333' : 'rgba(0,0,0,0.35)',
                  strokeWidth: 0.6,
                  outline: 'none',
                }}
              />
              {/* 라벨(미세하게 위쪽에 표시) */}
              <text
                x={hs.x + 1.2}
                y={hs.y - 0.8}
                style={{
                  fontSize: 2.8,
                  fill: '#111',
                  paintOrder: 'stroke',
                  stroke: 'white',
                  strokeWidth: 0.5,
                }}
              >
                {hs.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* 선택 시 툴팁 */}
      {tooltip && (
        <div
          role="status"
          aria-live="polite"
          style={{
            ...styles.tooltip,
            left: tooltip.x + 8,
            top: tooltip.y + 8,
            width : "max-content"
          }}
          onClick={() => {
            // 필요 시 상세 모달/패널 열기 로직 연결
          }}
        >
          <strong>{selected?.label}</strong>
          <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>
            클릭 위치: ({Math.round(tooltip.x)}, {Math.round(tooltip.y)})
          </div>
          <TransfromBtn sourceText={selected?.label} />
          <button
            style={styles.tooltipBtn}
            onClick={(e) => {
              e.stopPropagation();
              setSelected(null);
              setTooltip(null);
            }}
          >
            닫기
          </button>
        </div>
      )}

      <figcaption style={styles.caption}>
        장곡사 미륵불 괘불탱 (이미지 위 네모를 클릭해보세요)
      </figcaption>
    </figure>
  );
}

// 🎨 간단 스타일
const styles = {
  figure: {
    position: 'relative',
    width: 'min(900px, 50vw)',
    margin: '24px auto',
    borderRadius: 12,
    overflow: 'hidden',
    boxShadow: '0 6px 18px rgba(0,0,0,0.12)',
    background: '#fff',
  },
  image: {
    display: 'block',
    width: '100%',
    height: 'auto',
    userSelect: 'none',
  },
  overlay: {
    position: 'absolute',
    inset: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'auto',
  },
  caption: {
    padding: '10px 12px',
    fontSize: 14,
    color: '#444',
    background: '#fafafa',
    borderTop: '1px solid #eee',
  },
  tooltip: {
    position: 'absolute',
    transform: 'translate(0, 0)',
    background: 'white',
    border: '1px solid rgba(0,0,0,0.1)',
    boxShadow: '0 6px 16px rgba(0,0,0,0.16)',
    padding: '10px 12px',
    borderRadius: 10,
    zIndex: 10,
    maxWidth: 220,
  },
  tooltipBtn: {
    marginTop: 8,
    border: 'none',
    padding: '6px 10px',
    borderRadius: 8,
    background: '#111',
    color: 'white',
    cursor: 'pointer',
  },
};
