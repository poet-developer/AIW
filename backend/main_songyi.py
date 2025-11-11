from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from dotenv import load_dotenv

import google.generativeai as genai
 

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY_2"))
# gemma3:1b   # FastAPI + Next.js + Ollama 연동 예제


app = FastAPI(title="장곡사 미륵불 괘불탱 안내문")

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

# ✅ 1️⃣ RDF/Turtle 파일 로드
ttl_path = "../data/image_sheet.ttl"  # 실제 TTL 파일 경로

examples = """[예시1 - 입력]
    대상: 국립중앙박물관 소장 국보 반가사유상/ 삼국 / 금동 / 높이 81.5cm, 불신높이 50cm /
    국립중앙박물관 / 국보
    수준: 내국인 아동
    [예시1 - 출력]
    왼 무릎을 세워 그 위에 오른발을 올리고 앉아 있는 보살상이에요. 고개를 숙인 얼굴의 오른쪽 뺨에 오른쪽 손가락을 살짝 대고 있어요. 살며시 내려 뜬 두 눈, 입가에 머금은 작은 미소, 섬세하게 표현된
    손과 발을 보면 마치 살아 있는 것처럼 느껴져요.
    출처: 국립중앙박물관 어린이박물관 전시자료

    [예시2 - 입력]
    대상: 청자 인물 모양 주전자/ 고려 / 도자기 / 높이 28cm, 바닥지름 19.7cm / 국립중앙박물관 / 국보
    수준: 내국인 아동
    [예시2 - 출력]
    머리에 관을 쓰고 손에 복숭아를 가득 든 사람 모양의 고려청자 주전자예요. 주전자 맨 아래의 구불거리는 무늬 때문에 사람이 구름을 타고 있는 것처럼 보여요. 이러한 모습은 도교와 관련이 있는데 이 사람은 서왕모와 관련이 있다고 여겨져요. 서왕모는 전설의 산인 곤륜산에 살면서 늙지 않고 오래 살게 만들어 주는 신비한 복숭아를 준다고 해요.
    출처: 국립중앙박물관 어린이박물관 전시자료

    [예시3 - 입력]
    대상: 연가칠년延嘉七年」이 새겨진 부처/ 고구려 / 도자기 / 높이 28cm, 바닥지름 19.7cm / 국립중앙박물관 / 국보
    수준: 내국인 아동
    [예시3 - 출력]
    광배 뒤에 글자가 새겨져 있는 작은 불상입니다. 539년에 고구려의 ‘동사’라는 절에서 승려들이 천 점의 불상을 만들었는데, 이 불상은 그중 하나입니다. 불상 뒷면에 새겨진 글을 통해 이러한 사실을 알 수 있습니다. 오른손은 위를, 왼손은 아래를 향해 펼치고 서 있습니다. 크기는 작지만 표정과 옷 주름 등이 섬세하게 표현되어 있습니다.
    출처: 국립중앙박물관 어린이박물관 활동지/어린이박물관 '시간 여행 안내소' 감상자료_「연가칠년延嘉七年」이 새겨진 부처 https://www.museum.go.kr/CHILD/contents/C0402000000.do?schM=view&catSlug=activity&arcSlug=20427 

    [예시4 - 입력]
    대상:국보 장곡사 미륵불 괘불탱 (長谷寺 彌勒佛 掛佛幀)
    수준: 내국인 일반
    [예시4 - 출력]
    용화수 가지를 들고 있는 미륵불을 그린 괘불이다. 괘불이란 야외에서 큰 법회나 의식을 진행할 때 법당 앞뜰에 걸어놓고 예배를 드리던 대형 불교그림을 말한다.
    장곡사에 있는 이 그림은 전체 897.6×585.7cm, 화면 805.5×556cm로 미륵불을 화면 중심에 두고 6대 여래, 6대 보살 등 여러 인물들로 화면을 가득 채우고 있다. 인간세계에 내려와 중생을 구제한다는 부처인 미륵불은 사각형의 얼굴에 머리에 4구의 작은 불상이 있는 화려한 보관을 쓰고, 풍만하고 살찐 모습으로 유난히 긴 팔과 커다란 상체를 가지고 있다.
    좌우에 있는 비로자나불과 노사나불은 머리에 둥근 두광이 있고 각각 두 손을 맞잡은 손 모양과 어깨 높이까지 두 손을 들어 올려 설법하는 손모양을 하고 있다. 그 밖의 다른 여래와 보살들은 각기 상징하는 물건들을 들고 있으며 10대 제자는 두손을 모아 합장한 자세로 방향이나 표현을 달리해 변화를 주고 있다. 그림 아래에는 부처를 수호하는 사천왕과 그 권속들이 자리잡고 있다. 전체적인 채색은 붉은 색을 주로 사용하고 녹색, 연록색, 주황 등의 중간 색조를 사용하여 밝은 화면을 보여 준다.
    이 그림은 조선 현종 14년(1673) 철학(哲學)을 비롯한 5명의 승려화가가 왕과 왕비, 세자의 만수무강을 기원하기 위해 그린 것이다. 미래불인 미륵을 본존으로 삼고 있지만 그림의 내용은 현세불인 석가가 영축산에서 설법하는 영산회상도와 비슷한 것으로 등장인물들과 배치구도가 독특한 작품이며 경전의 내용과도 다른 점이 있어 앞으로 연구할 가치가 많은 작품이다.
    출처: 국가유산청 국가유산포털 국가유산 지정 안내문 https://www.heritage.go.kr/heri/cul/culSelectDetail.do;jsessionid=OxaCEyRUu8yO9l1XouDSD6GO1GqglK2aNAZGYSOvU5bgHPNut141nJ8MkHx7A436.cpawas2_servlet_engine1?pageNo=1_1_2_0&ccbaCpno=1113403000000 

    [예시5 - 입력]
    대상: 장곡사 미륵불괘불탱 (長谷寺 彌勒佛掛佛幀)
    수준: 내국인/외국인 전문가
    [예시5 - 출력]

    연꽃을 들고 있는 화려한 보관불(寶冠佛) 중심으로 많은 권속들이 둘러 선 군도식 구도이다. 즉 비로자나불과 노사나불이 독립된 존상으로 비교적 크게 표현되었고, 미륵존불의 협시로 6대보살(六大菩薩), 6대여래(六大如來), 10대제자(十大弟子), 범천과 제석천, 사천왕, 천자(天子)와 천동(天童), 아사세왕(阿闍世王)과 위제희(韋提希) 왕비, 용왕과 용녀 등이 둘러 서 있다. 정면 입상의 보관불을 그린 후, 남은 공간에 많은 권속들을 배치한 군도 형식은 단독 형식보다 선행한다.
    보관에 비로자나불과 석가불 등 4구의 화불(化佛)이 묘사된 보관불은 천개(天蓋), 그리고 원형(圓形) 두광(頭光: 부처나 보살의 정수리에서 나오는 빛)과 신광(身光: 부처나 보살의 몸에서 발하는 빛)을 갖추었다. 비만한 원통형 체구는 오른쪽 어깨가 넓고 왼쪽 어깨가 좁아 어색하지만 얼굴은 온화하다.
    6대여래는 노사나불, 비로자나불, 다보여래, 석가문불(釋迦文佛), 약사여래, 아미타불이고 6대보살은 대묘상보살(大妙相菩薩), 법림보살(法林菩薩), 문수보살, 보현보살, 관음보살, 대세지보살이다. 보통 상단부에 등장하는 가섭존자(迦葉尊者)와 아난존자(阿難尊者), 그리고 범천과 제석천은 이 괘불탱에서는 사천왕과 함께 하단부에 배열되었다. 범천은 원유관(遠遊冠)을 쓰고 홀(笏)을 든 왕의 모습이다.
    이 괘불탱의 주조색은 홍색과 녹색이며 그밖에 가볍고 부드러운 파스텔 톤의 하늘색과 금니(金泥)를 대신한 황색(黃色) 등을 사용하였다. 신광의 모란 덩굴무늬 및 화면 테두리의 연속 꽃 문양이 화려하다.
    출처: 한국민족문화대백과사전 장곡사 미륵불괘불탱 https://encykorea.aks.ac.kr/Article/E0048283

    [예시6 - 입력]
    대상: 장곡사 미륵불괘불탱 (長谷寺 彌勒佛掛佛幀)
    수준: 내국인 일반
    [예시6 - 출력]

    괘불은 야외에서 법회(法會)를 할 때 본존불상(本尊佛像) 대신 법당(法堂) 앞에 높이 거는 불화(佛畵)이다. 미륵불은 석가가 열반에 든 후 56억 7천만 년 뒤에 인간 세상에 내려와 중생(衆生)을 구제한다(彌勒下生成佛經)는 미래불이다. 괘불에는 미륵존불(彌勒尊佛)을 중심으로 육대여래(六大如來)와 육대보살(六大菩薩), 제석(帝釋)과 범천(梵天) 등을 좌우대칭으로 배치하였고, 십대제자(十大弟子)와 용왕과 용녀 등은 좌우대칭 구도를 벗어나 배치한 점이 돋보인다. 미륵불은 머리에 둥근 모양의 머리 광배(頭光)가 있고, 몸 전체를 둘러싸고 있는 광배(擧身光背)가 있으며, 큰 상체에 용화수 가지를 손에 들고 서 있는 형상이다. 사각형으로 묘사된 얼굴과 마름모꼴의 화관(化冠)에는 4구의 화불(化佛)이 있으며, 그 주변에는 구슬을 꿰어 만든 장신구와 꽃이 화려하게 장식되어 있다. 이 그림은 길이 8.97m, 폭 5.85m 크기의 삼베(麻)에 그린 것으로, 1673년(현종 14년) 승옥 스님의 가르침 아래 철학(哲學)을 비롯한 5인의 승려 화가가 채색하였다. 괘불은 미륵불이 인간 세상에 내려와 중생을 구제한다는 미륵하생성불경(彌勒下生成佛經)의 내용을 따른 것이지만, 미륵불이면서 석가모니불로 변하여 세상에 나타나는 용화회상이 아니라 영축산에서 법화경을 설명하는 영산대법회괘불탱화로 그린 것이 특이한 점이다.
    출처: 한국학중앙연구원 디지털인문학연구소 https://dh.aks.ac.kr/~heritage/wiki/index.php/장곡사_미륵불_괘불탱

    [예시7 - 입력]
    대상: Hanging Painting of Janggoksa Temple (Maitreya Buddha)
    수준: 외국인 일반
    [예시7 - 출력]

    A hanging banner painting is displayed outdoors at a Buddhist temple on special occasions such as the Buddha’s birthday, outdoor rites, and the funerals of eminent monks.

    The hanging painting of Janggoksa Temple was made in 1673 by five monk artisans including Cheolhak. The painting, made on a hemp canvas measuring 8.97 m in height and 5.85 m in width, depicts Maitreya Buddha surrounded by the six buddhas, the six bodhisattvas, Indra and Brahma, the Buddha’s ten principal disciples, the Dragon King, the Dragon Queen, and the Four Guardian Kings. The halos around Maitreya’s body and head symbolize the auspicious light radiating from his body. The Buddha has a large torso and a square face. In his hands, Maitreya holds a branch of a dragon flower tree, under which he is prophesied to attain enlightenment. His elegant rhombic headdress is decorated with beads and flowers and features images of four Buddhas.
    It is believed that Maitreya, the Future Buddha, will descend into the human world 5.67 billion years after the death of Sakyamuni Buddha and rescue all beings from suffering. While the image depicted in this painting represents Maitreya, it is based on the scene of Sakyamuni Buddha’s lecture at Vulture Peak.
    출처: 한국학중앙연구원 디지털인문학연구소 https://dh.aks.ac.kr/~heritage/wiki/index.php/장곡사_미륵불_괘불탱"""
    
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
    prompt: str | dict
    model: str | None = None  # 없으면 .env의 OLLAMA_MODEL 사용
    
@app.post("/api/generate_raw")
async def generate_raw(payload: GenerateIn):
    model_name = "gemini-2.5-pro"
    gemini = genai.GenerativeModel(model_name)
    
    engineered_prompt = f"장곡사 미륵불 괘불탱에 대하여 {payload.prompt}용으로 설명해줘."
    
    try:
        response = gemini.generate_content(engineered_prompt)
        return {
            "model": model_name,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response.text,
            #temperature": 0
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API call failed: {str(e)}")
    
    
@app.post("/api/generate_ttl")
async def generate_raw(payload: GenerateIn):
    model_name = "gemini-2.5-pro"
    gemini = genai.GenerativeModel(model_name)

    try:
        with open(ttl_path, "r", encoding="utf-8") as f:
            ttl_context = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="TTL file not found")

    # ✅ 2️⃣ 프롬프트 엔지니어링 (RAG context 포함)
    engineered_prompt = f"""
    당신은 문화유산 데이터 해석 전문가입니다.
    아래에 주어진 RDF/Turtle 데이터를 참고하여, 장곡사 미륵불 괘불탱에 대해
    '{payload.prompt}' 용으로 설명문을 작성하세요.

    --- RDF 데이터 (참고용 Context) ---
    {ttl_context}
    -----------------------------------

    출력 형식:
    - 자연스러운 한국어 설명문
    - RDF 데이터의 사실을 바탕으로만 작성
    - 허구적 정보 추가 금지
    """

    try:
        response = gemini.generate_content(engineered_prompt)
        return {
            "model": model_name,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response.text,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API call failed: {str(e)}")

@app.post("/api/generate_super")
async def generate_raw(payload: GenerateIn):
    model_name = "gemini-2.5-pro"
    gemini = genai.GenerativeModel(model_name)
    
    try:
        with open(ttl_path, "r", encoding="utf-8") as f:
            ttl_context = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="TTL file not found")
    
# ✅ 프롬프트 엔지니어링 (RAG context 포함)
    engineered_prompt = f"""
    ### 시스템: 다국어/다층적 문화유산 해설 생성 엔진

    당신은 [TASK_CONFIG]에 정의된 지침에 따라, 첨부된 {ttl_context}을 기반으로 문화유산 안내문을 생성하는 AI입니다.

    작업 원칙:
    1.  사실 기반 (Grounding): 안내문의 모든 정보는 반드시 첨부된 {ttl_context} 파일의 내용에 근거해야 합니다. [DATASET]에 없는 내용은 생성하지 않습니다.
    2.  스타일 준수 (Style): 해설문의 문체, 어조, 구조는 반드시 [STYLE_GUIDE] 파일의 지침을 따라야 합니다.
    3.  지침 수행 (Execution): [TASK_CONFIG]에 명시된 모든 `languages`와 `layers`에 대해 빠짐없이 해설문을 생성해야 합니다.

    작업 순서:
    1.  [TASK_CONFIG]를 분석하여 생성해야 할 총 안내문의 조합(언어 x 레이어)을 파악합니다.
    2.  {ttl_context}에서 안내문 생성에 필요한 핵심 사실 정보를 추출합니다.
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
        response = gemini.generate_content(engineered_prompt)
        return {
            "model": model_name,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response.text,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {str(e)}")


@app.post("/api/generate_zero")
async def generate_raw(payload: GenerateIn):
    model_name = "gemini-2.5-pro"
    gemini = genai.GenerativeModel(model_name)
    
    engineered_prompt = payload.prompt
    
    try:
        response = gemini.generate_content(engineered_prompt)
        return {
            "model": model_name,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response.text,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API call failed: {str(e)}")
    
@app.post("/api/generate_few")
async def generate_raw(payload: GenerateIn):
    model_name = "gemini-2.5-pro"
    gemini = genai.GenerativeModel(model_name)
    
# ✅ 프롬프트 엔지니어링 (RAG context 포함)
    engineered_prompt = f"""
    {examples}
    
    {payload.prompt}
    """
    print("전송된 프롬프트",payload.prompt)
    try:
        response = gemini.generate_content(engineered_prompt)
        return {
            "model": model_name,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response.text,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {str(e)}")
    
    
@app.post("/api/generate_few_guide")
async def generate_raw(payload: GenerateIn):
    model_name = "gemini-2.5-pro"
    gemini = genai.GenerativeModel(model_name)
    
# ✅ 프롬프트 엔지니어링 (RAG context 포함)
    engineered_prompt = f"""
    역할: 너는 2024년 국가유산 안내판 지침을 다음의 [안내문 생성 지침 사항]으로 숙지하고, 이 지침을 기반으로 한국 국가유산의 안내문을 전문으로 다루는 다국어/다층적 안내문 생성 시스템이다.

    요청: 아래 [대상 국가유산 정보] 섹션에 입력된 모든 정보를 활용하여, 예시 없이 안내문 생성 지침 사항대로 사용자가 선택한 국가유산을 사용자 선택에 맞는 언어와 수준으로 설명한다.
    안내문 생성 지침 사항:
    시스템 정의 및 범위
    A.1. 이 안내문 시스템이 다루는 대상인 국가유산은 인위적이거나 자연적으로 형성된 국가적·민족적 또는 세계적 유산으로서 역사적·예술적·학술적 또는 경관적 가치가 큰 문화유산·무형유산·자연유산이다.
    A.2. 이 국가유산 안내문 시스템의 목적은 관람객에게 공공언어로 국가유산의 정보와 가치를 알리기 위한 것이다.
    A.3. 본래 국가유산 안내문은 해설 안내판과 기능성 안내판이 있는데, 이 국가유산 안내문 시스템은 해설 안내판의 기능을 하는 국가유산 안내문을 생성한다.
    A.4. 이 국가유산 안내문 시스템이 처리할 핵심 변수는 언어와 수준이다.
    A.5. 언어는 사용자의 국적에 따라 구분된다. (예: 한국어, 영어 등)
    사용자 수준 정의
    B.1. 수준은 사용자의 연령과 이해도를 포괄하며 다음과 같이 7단계로 정의한다. 
    B.1.1. 수준1(내국인 아동)
    정의: 내국인 유아 및 초등학생.
    이해도: 국가유산에 대한 사전 지식이 없거나 형성되는 입문 단계.
    B.1..2.  수준2(내국인 일반)
    정의: 내국인 청소년(중/고등학생) 및 65세 미만 성인.
    이해도: 보편적인 교양 지식을 갖춘 일반 단계.
    B.1..3. 수준3(내국인 시니어)
    정의: 내국인 65세 이상 성인.
    이해도: 일반 단계의 지식을 갖추었으나, 정보 습득 시 가독성이 중요한 단계. 
    B.1.4. 수준4(내국인 전문가)
    정의: 연령대 관계없이 관련 전공자, 연구자 및 심화 학습자.
    이해도: 국가유산에 대한 학술적/심화 이해 단계
    B.1.5. 수준5(외국인 아동)
    정의: 외국인 유아 및 초등학생.
    이해도: 한국 국가유산에 대한 사전 지식이 없는 입문 단계.
    B.1..6.  수준6(외국인 일반 및 시니어)
    정의: 외국인 청소년(중/고등학생) 및 성인.
    이해도: 한국 국가유산에 대한 사전 지식은 없으나, 성인으로서 기초적인 맥락과 핵심 가치의 이해를 필요로 하는 맥락적 일반 단계.
    B.1.7. 수준7(외국인 전문가)
    정의: 연령대 관계없이 관련 전공자, 연구자 및 심화 학습자.
    이해도: 한국 국가유산에 대한 인문학적 지식을 갖춘 단계.

    생성 스타일 정의
    C.1. (아동스타일)
    (어휘) 초등학생 수준의 매우 평이한 어휘를 사용한다.
    (문장) 짧은 단문 위주로 구성하며, 복잡한 문장 구조(예: '...것이며, ...하였고')를 피한다.
    (내용) 역사적 배경이나 인물보다는 '무엇을 하는 물건인지', '어떻게 생겼는지' 등 직관적인 특징에 집중한다.
    (비유) 이해를 돕기 위해 친근한 비유를 적극적으로 사용한다.
    (한자/용어) 한자 병기 및 전문 용어를 사용하지 않는다.
    C.2. (일반 스타일)
    (기본값) 별도 변형 없이 [B. 내용], [C. 스타일], [D. 형식]의 모든 기본 지침을 준수한다.
    C.3. (시니어 스타일)
    (어휘) '일반 스타일'을 따르되, 외래어 표기보다는 순화어를 우선한다.
    (내용) 역사적 배경, 인물, 유래를 충실히 설명하여 풍부한 맥락을 제공한다.
    (문장) 명확한 서술형으로 종결한다.
    C.4. (전문가 스타일)
    (어휘) 학술적 가치를 중심으로 하는 '양식(Style)', '기법(Technique)' 등 학술 용어 사용을 허용한다.
    (한자) [입력 정보]에 포함된 한자를 적극적으로 병기한다.
    (정보) [입력 정보]의 '지정 이유', '학술적 의의' 등 핵심 가치 정보를 빠짐없이 상세하게 인용한다.
    (예외) '전문 용어 사용 최소화' 지침의 예외를 적용한다.
    C.5. (외국인 스타일) 
    한국의 역사와 문화에 대한 배경지식이 제공되어야 하기에 안내판에서 설명하는 국가유산이 언제, 누가, 어떤 목적으로 만든 것인지를 가장 먼저 명확하고 간략하게 설명한다.
    문화유산 명칭에 사용된 국문 용어에 대한 정의를 적절히 보완하여 제공한다.
    어려운 용어나 긴 문장 대신, 누구나 쉽게 이해할 수 있는 평이하고 명쾌한 문장으로 작성한다.
    불가피하게 전문 용어를 사용해야 하는 경우라면, 해당 용어의 의미를 괄호 안에 덧붙이거나 별도의 문장으로 설명한다.  
    [출처: 국가유산 안내판 정비 통합 가이드라인(2024), 53쪽 ]
    C.6. 사용자 수준 정의와 생성 스타일 간의 연동 규칙을 다음과 같다.
    C.6.1. 수준1 (내국인 아동)은 C.1.(아동 스타일)을 따른다.
    C.6.2. 수준5 (외국인 아동)은 C.1.(아동 스타일)과 C.5(외국인 스타일)을 따른다.
    C.6.2. 수준2 (내국인 일반)는 C.2.(일반 스타일)를 따른다.
    C.6.2. 수준6 (외국인 일반)은 C.5.(외국인 스타일)를 따른다.
    C.6.3. 수준3 (내국인 시니어)는 C.3.(시니어 스타일)을 따른다.
    C.6.4. 수준4와 수준7 (내/외국인 전문가)는 C.4.(전문가 스타일)을 따른다.
    내용 및 서사 구조 원칙
    D.1. 해설안내판은 각각의 성격에 따라 국가유산 전체 영역을 종합하여 설명하는 종합안내판, 국가유산 전체 영역 중 권역을 설명하는 권역안내판, 개별 국가유산 한 건을 중심으로 설명하는 개별안내판으로 구분된다. 
    D.2. 본 국가유산 안내문은 안내문 생성의 대상이 되는 국가유산의 명시된 “안내문 유형”을 확인하고 이에 맞는 안내문을 생성한다.  
    D.2.a. 종합안내판: 국가유산 전체 영역을 종합하여 설명한다.
    D.2.b. 권역안내판: 국가유산 전체 영역 중 역사적, 학술적, 경관적 가치가 있는 유산과 그 주변 환경을 포괄하는 지리적 범위인 권역을 설명한다.
    D.2.c. 개별안내판: 국가유산 한 건을 중심으로 설명한다.
    D.3. 안내문안은 객관적 사실을 핵심 정보 위주로 전달하는 것을 목적으로 가장 우선시 한다.
    D.4. 국가유산 명칭은 각가유산청 국가유산포털(누리집)에 게재된 것을 활용한다.
    D.5. 안내문안은 사용자가 본인의 이해도에 맞춰 해당 국가유산을 쉽게 인지할 수 있도록 평이한 언어와 내용으로 작성한다.
    D.6. 안내문의 첫 문장은 해당 국가유산을 사용자가 쉽게 인지할 수 있는 내용을 작성한다.
    D.7. 해당 국가유산의 기능, 유래 특징 및 역사 및 문화적 가치를 우선적으로 설명한다.
    D.8. 해당 국가유산의 역사적, 문화적 가치는 다음과 같이 설명한다.
    D.8.1. 해당 국가유산이 만들어진 배경과 기능이나 용도를 설명한다.
    D.8.2. 관련 인물과 명칭의 유래를 설명한다.
    D.8.3. D.8.2.와 10.3.b.의 내용을 기반으로 해당 국가유산의 역사적, 문화적 가치를 설명하면서 해당 유산이 국가유산으로 지정된 이유를 간락하고 쉽게 적는다.
    D.8.4 객관적 사실을 핵심정보 위주로 전달하지만, 다수가 공감하는 내용이고 관람객이 해당 국가유산에 보다 흥미를 느낄 수 있는 이야기는, 인간 작업자가 판단하여 첨부한 정보도 안내문안에 첨가한다.
    D.8.5. D.8.4의 흥미를 느낄 수 있는 이야기는 객관적 사실이 아니고 이해와 흥미를 돕기 위해 첨가된 것임을 안내문안에 명시한다.
    D.8.6. 안내문안은 해당 국가유산의 형태나 크기, 규모 등에 대한 설명은 최소화한다.

    E. 스타일 및 용어 원칙
    E.1. 안내문안은 전문 용어나 난해한 용어는 되도록 사용하지 않되 꼭 필요한 경우에는 각주를 활용한다.
    E.2. 안내문안은 높임법을 사용하지 않는 것을 원칙으로 하되, 문장 내에 상하관계가 분명한 경우, 즉 군신관계, 사제, 부제지간 등에는 높임의 표현을 사용할 수 있다.
    E.3. 한국어 안내문에서 연도, 연대, 물량을 나타내는 숫자는 아라비아 숫자로 적고, 국가유산 명칭과 고유명사에 포함된 숫자는 한글로 적는다.
    F. 형식 및 표기법 원칙
    F.1. 한국어 안내문안에서 해당 국가유산을 이해하는 데 반드시 필요한 일부 내용 및 용어에 한해 한자를 함께 병기한다. 
    F.2. 해당 한자는 첨부된 정보에서 활용한다.
    F.3. 해당 국가유산 명칭에 전문 용어나 난해한 용어가 있는 경우 안내문안 첫 머리에 이를 풀이하여 설명한다.

    요청: 아래 [입력 정보]를 활용하여 {payload.prompt["target_audience"]}를 대상으로 {payload.prompt["language"]} 안내문을 작성한다 .
    
    입력 정보 (Input Data)
    [국가유산 안내문 작성 대상]
    안내문 유형: 개별안내판
    지정 번호: 국보
    명칭_한글: 장곡사 미륵불 괘불탱 (長谷寺 彌勒佛 挂佛幀)
    명칭_한문: 長谷寺 彌勒佛 挂佛幀
    명칭_영문: Hanging Painting of Janggoksa Temple (Maitreya Buddha)
    시대_한글: 조선 (1673년, 현종 14)
    재료/크기: 삼베에 채색, 세로 약 10.7m, 가로 약 6.3m
    기능: 괘불은 야외에서 법회(法會)를 할 때 본존불상(本尊佛像) 대신 법당(法堂) 앞에 높이 거는 불화(佛畵)이다. [디지털인문학연구소 안내문] 이 그림은 조선 현종 14년(1673) 철학(哲學)을 비롯한 5명의 승려화가가 왕과 왕비, 세자의 만수무강을 기원하기 위해 그린 것이다. [국가유산청 국가유산포털]
    시대적 배경: 1673년(현종 14년) 승옥 스님의 가르침 아래 철학(哲學)을 비롯한 5인의 승려 화가가 채색하였다. [디지털인문학연구소 안내문]
    핵심 내용: 괘불은 미륵불이 인간 세상에 내려와 중생을 구제한다는 미륵하생성불경(彌勒下生成佛經)의 내용을 따른 것이지만, 미륵불이면서 석가모니불로 변하여 세상에 나타나는 용화회상이 아니라 영축산에서 법화경을 설명하는 영산대법회괘불탱화로 그린 것이 특이한 점이다. [디지털인문학연구소 안내문]
    학술: 미래불인 미륵을 본존으로 삼고 있지만 그림의 내용은 현세불인 석가가 영축산에서 설법하는 영산회상도와 비슷한 것으로 등장인물들과 배치구도가 독특한 작품이며 경전의 내용과도 다른 점이 있어 앞으로 연구할 가치가 많은 작품이다. [국가유산청 국가유산포털]

    
    """
    print("전송된 프롬프트",payload.prompt)
    try:
        response = gemini.generate_content(engineered_prompt)
        return {
            "model": model_name,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response.text,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {str(e)}")
    
@app.post("/api/generate_songyi")
async def generate_raw(payload: GenerateIn):
    model_name = "gemini-2.5-pro"
    gemini = genai.GenerativeModel(model_name)
    
# ✅ 프롬프트 엔지니어링 (RAG context 포함)
    engineered_prompt = payload.prompt
    print("전송된 프롬프트", engineered_prompt)
    try:
        response = gemini.generate_content(engineered_prompt)
        return {
            "model": model_name,
            "input": payload.prompt,
            "final_prompt": engineered_prompt,
            "text": response.text,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Songyi call failed: {str(e)}")
    

class TranslateRequest(BaseModel):
    text: str
    target_lang: str  # "영어", "일본어", "중국어" 등

@app.post("/api/translate")
async def translate(req: TranslateRequest):
    model_name = "gemini-2.5-pro"
    gemini = genai.GenerativeModel(model_name)

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
        response = gemini.generate_content(engineered_prompt)
        return {
            "model": model_name,
            "target_lang": req.target_lang,
            "translation": response.text,
            "prompt_used": engineered_prompt[:500]  # 디버그용 (프롬프트 일부만 표시)
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama translation failed: {str(e)}")