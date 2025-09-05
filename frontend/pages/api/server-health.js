export default async function handler(req, res) {
  try {
    const r = await fetch("http://localhost:8000/api/health");
    const data = await r.json();
    res.status(200).json(data);
  } catch (e) {
    res.status(500).json({ error: "health check failed", detail: String(e) });
  }
}
