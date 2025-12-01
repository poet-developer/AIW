'use client';

export default function Loading() {
  return (
    <>
      {/* 로딩 스피너 */}
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
          </>
  )
}