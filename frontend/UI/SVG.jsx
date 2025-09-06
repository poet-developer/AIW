'use client';
import { useCallback } from 'react';

export default function SvgPathClickModal({ onPathClick }) {
  const handlePathClick = useCallback(() => {
    if (onPathClick) onPathClick();
  }, [onPathClick]);

  return (
    <>
      {/* SVG 하나만 예시로 두고, 필요하면 여러 개 복제하세요 */}
      <svg viewBox="0 0 277.41 283.46" xmlns="http://www.w3.org/2000/svg" className="svg">
        <path
          className="clickablePath"
          onClick={handlePathClick}
          d="M0,11.36S.96,2.89,8.77,2.89c0,0,35.81-6.51,37.76,0,16.92,7.81,20.18,15.62,20.18,15.62,0,0,22.13-5.21,20.18,24.74,0,0,5.86,21.48,5.21,33.2,0,0,1.4,8.46.05,16.27,0,0,3.85,7.16,3.2,9.76,0,0,3.25,10.42-8.46,5.86,0,0-7.16,18.27-7.81,19.87,0,0-7.16,25.69-9.76,21.79,0,0-11.07,32.55,13.67,52.08l54.03,31.25s8.46-10.42,22.13-8.46h18.23s16.92-33.63,26.04-31.46c0,0,23.43-14.11,33.2-13.46l20.83-1.95s2.6,5.21-9.11,7.81c0,0,26.04-5.21,27.34,1.3,0,0,3.91,19.53,0,16.27,0,0-9.11-14.32-32.55-5.21,0,0-22.13,6.51-22.13,8.46,0,0-8.46,5.5-8.46,12.51,0,0-8.46,12.88-8.46,23.29,0,0,11.07,13.02-9.11,14.32,0,0-11.07,13.02-11.07,23.43l-8.46,3.25h-8.46S97.96,178,23.74,207.3l-23.74,6.51V11.35h0Z"
        />
      </svg>

      <style jsx>{`
        .svg {
          width: 300px;
          height: auto;
          display: block;
          margin: 30px auto;
        }
        .clickablePath {
          fill: black;
          cursor: pointer;
          transition: fill 0.15s ease-in-out;
        }
        .clickablePath:hover {
          fill: darkred;
        }
      `}</style>
    </>
  );
}
