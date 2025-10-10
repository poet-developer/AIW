from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import httpx
from dotenv import load_dotenv
from langchain_community.llms import Ollama

from makeContext import load_context

load_dotenv()


# gemma3:1b   # FastAPI + Next.js + Ollama 연동 예제

app = FastAPI(title="장곡사 미륵불 괘불탱 안내문")
# OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
# OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma3:12b"
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
) #여기 뭔지 모름 공부할것.
# curl http://49.247.14.81:11434/api/tags

# make_context.py의 함수 호출
context_text = load_context("data.json")
guide_text = load_context("guide.json")
entities = load_context("entities.json")

# print("=== 불러온 guide ===")
# print(guide_text[:300])  # 일부만 출력  

# print("=== 불러온 context ===")
# print(context_text[:300])  # 일부만 출력


# --- REST API ---
@app.get("/api/health")
def health():
    return {"status": "ok"}


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
    model = payload.model or "gemma3:12b"  # 기본 모델
    llm = Ollama(
        base_url="http://localhost:11434",  # SSH 터널 → 항상 localhost
        model=model,
        temperature=0.2,
        repeat_penalty=1.2,
    )
    
# ✅ 프롬프트 엔지니어링 로직 추가
    engineered_prompt = f"장곡사 미륵불 괘불탱에 대하여 {payload.prompt}용으로 설명해줘."
    # engineered_prompt = f"안녕"
    print("전송모드", payload.prompt)
    try:
        response = llm.invoke(engineered_prompt)
        return {
            "model": model,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,  # 디버깅용으로 반환
            "text": response,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {str(e)}")


@app.post("/api/generate_prompt")
async def generate_raw(payload: GenerateIn):
    model = payload.model or "gemma3:12b"  # 기본 모델
    llm = Ollama(
        base_url="http://localhost:11434",  # SSH 터널 → 항상 localhost
        model=model,
        temperature=0.2,
        repeat_penalty=1.2,
    )
    
# ✅ 프롬프트 엔지니어링 (RAG context 포함)
    engineered_prompt = f"""
    ###시스템
    당신은 문화유산을 안내하는 전문가입니다.
    아래에 제시된 참고 자료를 참고하여 문화유산 안내문을 작성하세요.
    장곡사 미륵불 괘불탱 관련 참고 자료를 토대로 사실에 근거하여 작성하고,
    문화유산 안내문 가이드를 준수하여 작성하세요.

    **장곡사 미륵불 괘불탱 관련 참고 자료**
    {context_text}

    **문화유산 안내문 가이드** 
    {guide_text}

    위 지시 내용을 준수하여 장곡사 미륵불 괘불탱에 대하여 "{payload.prompt}"을/를 대상으로 설명해주세요.
    """
    print("전송된 프롬프트",payload.prompt)
    try:
        response = llm.invoke(engineered_prompt)
        return {
            "model": model,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {str(e)}")

@app.post("/api/generate_entity")
async def generate_raw(payload: GenerateIn):
    model = payload.model or "gemma3:12b"  # 기본 모델
    llm = Ollama(
        base_url="http://localhost:11434",  # SSH 터널 → 항상 localhost
        model=model,
        temperature=0.2,
        repeat_penalty=1.2,
    )
    
# ✅ 프롬프트 엔지니어링 (RAG context 포함)
    engineered_prompt = f"""
    ###시스템
    당신은 문화유산을 안내하는 전문가입니다.
    아래에 제시된 참고 자료를 참고하여 문화유산 안내문을 작성하세요.
    장곡사 미륵불 괘불탱 관련 참고 자료를 토대로 사실에 근거하여 작성하고,
    문화유산 안내문 가이드를 준수하여 작성하세요.

    **장곡사 미륵불 괘불탱 관련 참고 자료**
    불교 작품 정보: {context_text}
    불교 인물 정보: {entities}

    **문화유산 안내문 가이드** 
    {guide_text}

    위 지시 내용을 준수하여 장곡사 미륵불 괘불탱에 대하여 "{payload.prompt}"을/를 대상으로 설명해주세요.
    """
    print("전송된 프롬프트",payload.prompt)
    try:
        response = llm.invoke(engineered_prompt)
        return {
            "model": model,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {str(e)}")


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
