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
korean_text = """괘불은 야외에서 법회(法會)를 할 때 본존불상(本尊佛像) 대신 법당(法堂) 앞에 높이 거는 불화(佛畵)이다.
미륵불은 석가가 열반에 든 후 56억 7천만 년 뒤에 인간 세상에 내려와 중생(衆生)을 구제한다(彌勒下生成佛經)는 미래불이다.
괘불에는 미륵존불(彌勒尊佛)을 중심으로 육대여래(六大如來)와 육대보살(六大菩薩), 제석(帝釋)과 범천(梵天) 등을 좌우대칭으로 배치하였고, 십대제자(十大弟子)와 용왕과 용녀 등은 좌우대칭 구도를 벗어나 배치한 점이 돋보인다.
미륵불은 머리에 둥근 모양의 머리 광배(頭光)가 있고, 몸 전체를 둘러싸고 있는 광배(擧身光背)가 있으며, 큰 상체에 용화수 가지를 손에 들고 서 있는 형상이다.
사각형으로 묘사된 얼굴과 마름모꼴의 화관(化冠)에는 4구의 화불(化佛)이 있으며, 그 주변에는 구슬을 꿰어 만든 장신구와 꽃이 화려하게 장식되어 있다.
이 그림은 길이 8.97m, 폭 5.85m 크기의 삼베(麻)에 그린 것으로, 1673년(현종 14년) 승옥 스님의 가르침 아래 철학(哲學)을 비롯한 5인의 승려 화가가 채색하였다.
괘불은 미륵불이 인간 세상에 내려와 중생을 구제한다는 미륵하생성불경(彌勒下生成佛經)의 내용을 따른 것이지만, 미륵불이면서 석가모니불로 변하여 세상에 나타나는 용화회상이 아니라 영축산에서 법화경을 설명하는 영산대법회괘불탱화로 그린 것이 특이한 점이다."""

english_text = """A hanging banner painting is displayed outdoors at a Buddhist temple on special occasions such as the Buddha’s birthday, outdoor rites, and the funerals of eminent monks.
The hanging painting of Janggoksa Temple was made in 1673 by five monk artisans including Cheolhak.
The painting, made on a hemp canvas measuring 8.97 m in height and 5.85 m in width, depicts Maitreya Buddha surrounded by the six buddhas, the six bodhisattvas, Indra and Brahma, the Buddha’s ten principal disciples, the Dragon King, the Dragon Queen, and the Four Guardian Kings.
The halos around Maitreya’s body and head symbolize the auspicious light radiating from his body.
The Buddha has a large torso and a square face. In his hands, Maitreya holds a branch of a dragon flower tree, under which he is prophesied to attain enlightenment.
His elegant rhombic headdress is decorated with beads and flowers and features images of four Buddhas.
It is believed that Maitreya, the Future Buddha, will descend into the human world 5.67 billion years after the death of Sakyamuni Buddha and rescue all beings from suffering.
While the image depicted in this painting represents Maitreya, it is based on the scene of Sakyamuni Buddha’s lecture at Vulture Peak."""

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
    

@app.post("/api/generate_all")
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
    문화유산 안내문 가이드와 기존 장곡사 미륵불 괘불탱 안내문을 준수하여 작성하세요.

    **장곡사 미륵불 괘불탱 관련 참고 자료**
    불교 작품 정보: {context_text}
    불교 인물 정보: {entities}

    **문화유산 안내문 가이드** 
    1. 안내문안은 정보전달을 목적으로 하며 간결하고 쉽게 표현하여 초등학교 3학년생 이상이 이해할 수 있도록 작성한다.
    2. 건축구조 및 형식 등 전문적인 용어를 지양하며 학습목적의 전문적 지식은 리플릿 등 타 매체를 통하여 보완한다
    3. 다른 매체와의 역할분담과 연계활용을 고려한 정확하고 기본적인 정보위주로 작성하며, 관람자의 이해와 흥미유발을 위하여 Story-telling기법의 가미도 고려한다.
    4. 국어문안은 국립국어원의 기준으로 작성한다.

    **기존 장곡사 미륵불 괘불탱 안내문**
    한국어 : {korean_text}
    영어 : {english_text}
    
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
