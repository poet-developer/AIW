// Next.js 서버가 KT Cloud Proxy로 직접 요청을 보냄
export default async function handler(req, res) {
  const backendURL =
    "https://proxy3.aitrain.ktcloud.com:10257/proxy/8000/translate";

  try {
    const apiRes = await fetch(backendURL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: req.headers.cookie || "", // 🔑 세션 쿠키 전달
      },
      body: JSON.stringify(req.body),
      credentials: "include",
    });

    if (!apiRes.ok) {
      const text = await apiRes.text();
      console.error("백엔드 오류:", text);
      return res.status(apiRes.status).json({ error: text });
    }

    const data = await apiRes.json();
    return res.status(200).json(data);
  } catch (err) {
    console.error("서버 통신 실패:", err);
    return res.status(500).json({ error: "서버 연결 실패" });
  }
}
