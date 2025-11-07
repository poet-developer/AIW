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
    
@app.post("/api/generate_raw")
async def generate_raw(payload: GenerateIn):
    model = payload.model or "gemma3:12b"  # 기본 모델
    llm = Ollama(
        base_url="http://localhost:11434",  # SSH 터널 → 항상 localhost
        model=model,
        temperature=0.2,
        repeat_penalty=1.2,
    )

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

@app.post("/api/generate_super")
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
    ### 시스템: 다국어/다층적 문화유산 해설 생성 엔진

    당신은 [TASK_CONFIG]에 정의된 지침에 따라, 첨부된 {context_text}을 기반으로 문화유산 안내문을 생성하는 AI입니다.

    작업 원칙:
    1.  사실 기반 (Grounding): 안내문의 모든 정보는 반드시 첨부된 {context_text} 파일의 내용에 근거해야 합니다. [DATASET]에 없는 내용은 생성하지 않습니다.
    2.  스타일 준수 (Style): 해설문의 문체, 어조, 구조는 반드시 [STYLE_GUIDE] 파일의 지침을 따라야 합니다.
    3.  지침 수행 (Execution): [TASK_CONFIG]에 명시된 모든 `languages`와 `layers`에 대해 빠짐없이 해설문을 생성해야 합니다.

    작업 순서:
    1.  [TASK_CONFIG]를 분석하여 생성해야 할 총 안내문의 조합(언어 x 레이어)을 파악합니다.
    2.  {context_text}에서 안내문 생성에 필요한 핵심 사실 정보를 추출합니다.
    3.  [STYLE_GUIDE]에서 모방해야 할 문체 지침을 숙지합니다.
    4.  [TASK_CONFIG]의 `layers` 목록을 순회하며, 각 `audience`의 수준과 `keywords`에 맞춰 해설문을 작성합니다.
    5.  각 해설문을 [TASK_CONFIG]의 `languages` 목록에 맞게 정확히 번역 또는 재작성합니다.
    6.  [TASK_CONFIG]의 `output_format`에 맞춰 전체 결과를 구조화하여 출력합니다.

    ### TASK_CONFIG

    # 1. 기본 정보 (안내 대상)
    heritage_asset: "장곡사 미륵불 괘불탱"

    # 2. 다국어 설정 (Multilingual)
    # (확장: 여기에 "fr-FR"을 추가하면 엔진 수정 없이 프랑스어 생성)
    languages:
    - "Korean (ko-KR)"
    #- "English (en-US)"
    #- "Japanese (ja-JP)"

    # 3. 다층적 설정 (Multi-layered)
    layers:
    - audience: "어린이 (Children)"
        description: "초등학교 저학년 대상. 쉽고 재미있는 어휘 사용."
        keywords: ["보물 그림", "미륵 부처님", "소원 빌기", "함께"]
        length: "2문단"
    - audience: "일반 성인 (General Audience)"
        description: "일반 관람객 대상. 핵심 가치와 역사적 배경 설명."
        keywords: ["국보", "조선 후기", "야단법석", "미륵 신앙", "위로"]
        length: "3문단"
    - audience: "연구자 (Academic Experts)"
        description: "미술사/불교 전공자 대상. 학술 용어 사용."
        keywords: ["1673년", "화기(畫記)", "방제(旁題)", "도상학적 특징", "영산회", "과도기적 양상"]
        length: "4문단"
        
    # 4. STYLE_GUIDE
    1. 핵심 목적: 단순 사실 나열이 아닌 '심층 해설'을 목표로 합니다. 문화유산의 학술적, 역사적 맥락을 깊이 있게 설명하고, 현시대의 상황과 연결하여 독자의 '공감'을 이끌어내야 합니다.
    2. 글의 구조: '주제 중심의 기승전결' 구조를 따릅니다. 
    (예: 기원 → 특징 분석 → 역사적 배경 → 현시대적 의미)
    3. 어조 및 문체: '학술적-감성적 서술체'를 사용합니다.
    단정적인 어조보다는 연구자의 해석이 담긴 부드러운 문체(예: "~(으)로 보인다", "~(ㄹ) 것으로 생각된다")를 활용합니다.
    4. 시점 사용: 글쓴이의 '나'나 '우리'는 드러내지 않는 '철저한 3인칭 시점'을 유지합니다. 정보의 출처나 근거를 명확히 밝혀(예: "학계에서는...", "기록에 따르면...") 객관성을 확보합니다.
    5. 용어 사용: '화기(畫記)', '방제(旁題)'와 같은 전문 용어를 정확히 사용하되, '야단법석'처럼 독자의 흥미를 유발할 수 있는 대중적 키워드를 적절히 함께 사용하여 가독성을 높입니다.    

    # 5. 출력 요구사항
    output_specs: 
    text_type: {payload.prompt}
    length: "약 3~4 문단"
    format: "Markdown"
    key_rules:
    - "[STYLE_GUIDE]의 5가지 항목을 반드시 준수할 것." 
    - "[STYLE_GUIDE] 2번 항목의 '기승전결' 구조를 따를 것."
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



class TranslateRequest(BaseModel):
    text: str
    target_lang: str  # "영어", "일본어", "중국어" 등

@app.post("/api/translate")
async def translate(req: TranslateRequest):
    """
    Ollama 모델을 이용한 실제 번역 엔드포인트
    """
    model = "gemma3:12b"  # 필요 시 다른 모델 이름으로 변경 가능
    llm = Ollama(
        base_url="http://localhost:11434",  # Ollama 서버 주소
        model=model,
        temperature=0.3,
        repeat_penalty=1.1,
    )

    # ✅ 프롬프트 엔지니어링
    # 한국어 입력을 target_lang으로 자연스럽게 번역하되, 문화유산 관련 텍스트로서의 품격 유지
    engineered_prompt = f"""
    ### 시스템 지시:
    다음 문장을 {req.target_lang}으로 번역하세요.

    ### 번역 대상 텍스트:
    {req.text}

    ### 출력:
    - 번역 결과만 출력하세요. 추가 설명이나 주석은 포함하지 마세요.
    """
    print("번역 프롬프트:", engineered_prompt)
    try:
        response = llm.invoke(engineered_prompt)
        return {
            "model": model,
            "target_lang": req.target_lang,
            "translation": response.strip(),
            "prompt_used": engineered_prompt[:500]  # 디버그용 (프롬프트 일부만 표시)
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama translation failed: {str(e)}")