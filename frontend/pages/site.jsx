import { useEffect, useRef, useState } from "react";
import useSWR from "swr";

async function apiGet(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed`);
  return res.json();
}
async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed`);
  return res.json();
}
async function apiPatch(path) {
  const res = await fetch(path, { method: "PATCH" });
  if (!res.ok) throw new Error(`PATCH ${path} failed`);
  return res.json();
}
async function apiDelete(path) {
  const res = await fetch(path, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE ${path} failed`);
}

export default function Home() {
  const { data, mutate, isLoading, error } = useSWR("/api/todos", apiGet);
  const [title, setTitle] = useState("");
  const wsRef = useRef(null);
  const [msgs, setMsgs] = useState([]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws"); // 개발용
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        setMsgs((prev) => [
          `${msg.type}: ${msg.payload ?? msg.message}`,
          ...prev,
        ]);
      } catch (e) {
        setMsgs((prev) => [evt.data, ...prev]);
      }
    };
    ws.onopen = () => {
      try {
        ws.send("hello from browser");
      } catch (e) {
        // ignore
      }
    };
    return () => {
      try {
        ws.close();
      } catch (e) {
        // ignore
      }
    };
  }, []);

  const addTodo = async () => {
    if (!title.trim()) return;
    await apiPost("/api/todos", { title });
    setTitle("");
    mutate();
  };

  const toggle = async (id) => {
    await apiPatch(`/api/todos/${id}`);
    mutate();
  };

  const remove = async (id) => {
    await apiDelete(`/api/todos/${id}`);
    mutate();
  };

  return (
    <main
      style={{
        maxWidth: 680,
        margin: "40px auto",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <h1>FastAPI × Next.js (JS/Pages)</h1>

      <section style={{ marginTop: 24 }}>
        <h2>Todos</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="새 할 일"
            style={{ flex: 1, padding: 8 }}
          />
          <button onClick={addTodo} style={{ padding: "8px 12px" }}>
            추가
          </button>
        </div>

        {error && (
          <p style={{ marginTop: 12, color: "crimson" }}>
            에러: {String(error.message || error)}
          </p>
        )}
        {isLoading ? (
          <p style={{ marginTop: 12 }}>불러오는 중…</p>
        ) : (
          <ul style={{ marginTop: 12, paddingLeft: 16 }}>
            {(data || []).map((t) => (
              <li
                key={t.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 6,
                }}
              >
                <input
                  type="checkbox"
                  checked={t.done}
                  onChange={() => toggle(t.id)}
                />
                <span
                  style={{ textDecoration: t.done ? "line-through" : "none" }}
                >
                  {t.title}
                </span>
                <button
                  onClick={() => remove(t.id)}
                  style={{ marginLeft: "auto" }}
                >
                  삭제
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>WebSocket Messages</h2>
        <div style={{ border: "1px solid #ddd", padding: 12, minHeight: 120 }}>
          {msgs.length === 0 ? (
            <em>메시지 없음</em>
          ) : (
            msgs.map((m, i) => <div key={i}>{m}</div>)
          )}
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>서버 헬스 (Next API Route → FastAPI)</h2>
        <a href="/api/server-health" target="_blank" rel="noreferrer">
          /api/server-health 열기
        </a>
      </section>
      <div>site</div>
    </main>
  );
}
