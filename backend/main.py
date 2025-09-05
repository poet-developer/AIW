from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import httpx
from dotenv import load_dotenv

load_dotenv()


# gemma3:1b   # FastAPI + Next.js + Ollama 연동 예제

app = FastAPI(title="FastAPI + Next.js Demo")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
# --- CORS: 개발 중 Next.js(3000)에서 바로 호출 가능 ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 모델 & 인메모리 저장소 (데모용) ---
class TodoIn(BaseModel):
    title: str

class Todo(BaseModel):
    id: int
    title: str
    done: bool = False

TODOS: List[Todo] = []
NEXT_ID = 1

# --- REST API ---
@app.get("/api/health")
def health():
    return {"status": "ok"}

# CRUD

# @app.get("/api/todos", response_model=List[Todo])
# def list_todos():
#     return TODOS

# @app.post("/api/todos", response_model=Todo, status_code=201)
# def create_todo(todo: TodoIn):
#     global NEXT_ID
#     new = Todo(id=NEXT_ID, title=todo.title, done=False)
#     NEXT_ID += 1
#     TODOS.append(new)
#     return new

# @app.patch("/api/todos/{todo_id}", response_model=Todo)
# def toggle_done(todo_id: int):
#     for t in TODOS:
#         if t.id == todo_id:
#             t.done = not t.done
#             return t
#     return {"detail": "Not found"}  # 간단 처리(실전에서는 HTTPException)

# @app.delete("/api/todos/{todo_id}", status_code=204)
# def delete_todo(todo_id: int):
#     global TODOS
#     TODOS = [t for t in TODOS if t.id != todo_id]
#     return

# --- WebSocket (브라우저에서 ws://localhost:8000/ws 로 연결) ---
active_connections: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_connections.append(ws)
    try:
        await ws.send_json({"type": "welcome", "message": "connected"})
        while True:
            data = await ws.receive_text()
            # 에코 + 브로드캐스트
            for conn in list(active_connections):
                await conn.send_json({"type": "echo", "payload": data})
    except WebSocketDisconnect:
        active_connections.remove(ws)

# -- Ollama 연동 예제 ---

class GenerateIn(BaseModel):
    prompt: str
    model: str | None = None  # 없으면 .env의 OLLAMA_MODEL 사용

@app.post("/api/generate_raw")
async def generate_raw(payload: GenerateIn):
    model = payload.model or OLLAMA_MODEL
    url = f"{OLLAMA_BASE_URL}/api/generate"

    req_json = {
        "model": model,
        "prompt": payload.prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=req_json)
            # Ollama는 200이지만 내부 에러는 JSON 내 error에 담기는 경우도 있으니 방어
            if r.status_code >= 400:
                raise HTTPException(r.status_code, r.text)
            data = r.json()
            if "error" in data:
                raise HTTPException(500, data["error"])
            # Ollama generate 응답 예: { "model":..., "created_at":..., "response": "...", ... }
            return {"model": data.get("model"), "text": data.get("response", "")}
    except httpx.RequestError as e:
        raise HTTPException(502, f"Ollama connection failed: {e}")

# Chat API 예제

# class ChatMessage(BaseModel):
#     role: str  # "user" | "assistant" | "system"
#     content: str

# class ChatIn(BaseModel):
#     messages: List[ChatMessage]
#     model: str | None = None

# @app.post("/api/chat")
# async def chat(payload: ChatIn):
#     model = payload.model or OLLAMA_MODEL
#     url = f"{OLLAMA_BASE_URL}/api/chat"
#     req_json = {
#         "model": model,
#         "messages": [{"role": m.role, "content": m.content} for m in payload.messages],
#         "stream": False,
#     }
#     try:
#         async with httpx.AsyncClient(timeout=60) as client:
#             r = await client.post(url, json=req_json)
#             if r.status_code >= 400:
#                 raise HTTPException(r.status_code, r.text)
#             data = r.json()
#             # 예: {"message":{"role":"assistant","content":"..."},"done":true,...}
#             msg = (data.get("message") or {}).get("content", "")
#             return {"text": msg, "raw": data}
#     except httpx.RequestError as e:
#         raise HTTPException(502, f"Ollama connection failed: {e}")
