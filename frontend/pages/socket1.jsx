"use client";

export default function Home() {
  async function handleTranslate() {
    const response = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "테스트 문장" }),
    });

    const data = await response.json();
    console.log("서버 응답:", data);
  }

  return (
    <main>
      <button onClick={handleTranslate}>번역 요청</button>
    </main>
  );
}
