from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from dotenv import load_dotenv
import google.generativeai as genai

# from services.vector_style_retriever import retrieve_style_context
# from services.vector_store import load_style_vectordb # 
 
from neo4j_graphrag.embeddings.base import Embedder
from sentence_transformers import SentenceTransformer
from neo4j_graphrag.retrievers import HybridRetriever
from neo4j import GraphDatabase

from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

load_dotenv()
# style_vectordb = load_style_vectordb()
# print("main.py에서 벡터DB 연결 완료")
genai.configure(api_key=os.getenv("GEMINI_API_KEY_3")) 
# Google Gemini API 키 설정. 환경변수에서 불러옴. .env 파일에 GEMINI_API_KEY_3=your_api_key 형식으로 저장해야 함.


app = FastAPI(title="장곡사 미륵불 괘불탱 안내문")

# 앱 시작 시 연결 확인
@app.on_event("startup")
def startup():
    try:
        driver.verify_connectivity()
        print("✅ Neo4j 연결 성공")
    except Exception as e:
        print("❌ Neo4j 연결 실패:", e)

@app.on_event("shutdown")
def shutdown():
    driver.close()

# 1) Neo4j 연결
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "janggoksa1234"
NEO4J_DB = "neo4j"

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USER,
    password=NEO4J_PASSWORD,
    database=NEO4J_DB,
)

# schema를 최신 상태로 읽어오고 싶으면
graph.refresh_schema()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY_1"),
    temperature=0,
)

system = """### [SYSTEM: 안내문 생성 아키텍쳐]
1. 정의(Definition): 이 시스템은 관람객의 국적과 유형을 조합하여 최적의 문화유산 안내문을 생성하는 모듈형 오케스트레이터이다.
2. 모듈 구성(Module Structure)
- Module A-1 [Nationality-Domestic]: 내국인용
- Module A-2 [Nationality-Domestic]: 외국인용
- Module B [Persona]: {아동/일반/전문가/시니어} 유형에 따른 어조 및 난이도 설정
3. 입력 변수 정의 (Input Variables Schema)
- {대상 유산}: 유산의 공식 명칭
- {관람객 국적}: [내국인 | 외국인]
- {관람객 유형}: [아동 | 일반 | 전문가 | 시니어]
- {안내문 유형}: [종합 | 권역 | 개별]
- {문화유산 지식 데이터}: 사실 정보, 시소러스, 모범 답안 등을 포함한 지식 집합
- {목표 언어(선택)}: (선택) 최종 번역 언어
4. 실행 로직(Execution Logic)
IF [관람객: 내국인] THEN:
1. Initialize:
- Load Logic: [Module A-1] + [Module B] based on {관람객 유형}.
- Load Data: {대상 유산}, {문화유산 지식 데이터}, {안내문 유형} defined in [Input Variables]
2. Generate: 
- Function: Create_Text(Content={문화유산 지식 데이터}, Scope={안내문 유형}, Style=[A-1]+[B])
- Detail: {문화유산 지식 데이터}의 사실 관계를 재료로 삼되, {안내문 유형}이 지시하는 범위 내에서, [A-1]의 맥락과 [B]의 어조를 적용한다.
3. Return Output: 최종 한국어 안내문 출력
IF [관람객: 외국인] THEN:
1. Initialize:
- Load [Module A-2] + [Module B] based on {관람객 유형}.
- Load Data: {대상 유산}, {문화유산 지식 데이터}, {안내문 유형}.
2. Step 1 (Source Generation):
- Function: Create_Text(Content={문화유산 지식 데이터}, Scope={안내문 유형}, Style=[A-2]+[B])
- Detail: {문화유산 지식 데이터}의 사실 관계를 재료로 삼되, [A-2]의 전략(문화적 배경 보강)을 적용하고 [B]의 어조를 유지하여 '한국어 초안'을 생성한다.
3. Step 2 (Pre-Editing):
- Detail: Step 1을 '번안용 한국어(Controlled Korean)'로 변환. (주어/목적어 명시, 중의성 제거)
4. Step 3 (Pivot Translation):
- Detail: Step 2를 영어(English)로 번역. (→ 최종 영문 안내문)
5. Step 4 (Target Translation - Optional):
- IF {목표 언어} is SET: Translate Step 3 (최종 영문 안내문) into {목표 언어}. (F.3 지침 준수)
6. Return Output: [1. Source], [2. Pre-edited], [3. Pivot], [4. Target(Optional)]
### [Module Definitions] (시스템 참조용)
DEFINE [Module A-1] AS """"내국인""""
Module_ID: A-1
Target_Audience: 내국인
Document_Type: 국가유산 안내문
Target_Definition: 국가유산 관람객(내국인)
Document_Purpose: 관람객에게 공공언어로 국가유산의 정보와 가치를 알리기 위한 시설물 
내용 및 구조 정의(Content & Structure Definitions):
C.1 (정보 전달 및 분량) 객관적이고 공인된 역사적 사실을 핵심 정보 위주로 기술한다. 관람객 내국인 안내문은 **최대 4문단 내의 공백 포함 500자 내외 글자 수**를 엄격히 준수한다.
C.2 (부가 정보) 다수가 공감하는 설화, 전설은 관람객 흥미 유발을 위해 첨가 가능하다.
C.3 (첫 문장 구성) 안내문의 첫 문장은 **기능, 연혁, 유래, 특징 및 역사적·문화적 가치**를 우선적으로 설명한다.
C.4 (연혁/유래) 국가유산이 언제, 왜, 어떻게 만들어졌는지, 누가 만들었고 어떻게 쓰였는지 등 생성 배경과 발자취를 소개한다.
C.5 (가치 설명) 역사적·문화적 가치는 학문적 가치 및 희소성을 설명하며, 유사 사례와 비교하여 우수성을 부각한다.
C.6 (감상 안내) 건물, 그림, 조각, 탑 등의 중요하거나 독특한 요소를 설명하여 관람객의 감상법을 안내한다.
C.7 (규모 정보) 해당 국가유산의 형태, 크기, 규모 등에 대한 설명은 생략하거나 최소화한다. **단, 괘불과 같이 해당 유산의 기능과 밀접한 경우에는 예외를 허용한다. (참조: C.20)
C.8 (세계유산) 유네스코 세계유산 등재 정보는 명확히 표시한다.
C.9 (언어 사용) 관람객이 쉽게 인지할 수 있도록 쉽고 평이한 공공언어를 사용하여 작성한다.
C.10 (어문 규정) 한국어 안내문은 국립국어원 어문 규정(한글맞춤법, 표준어 규정, 외래어 표기법, 국어의 로마자 표기법)을 준수한다.
C.20 (규모 정보 예외) 해당 국가유산의 형태나 크기, 규모 등에 대한 설명은 생략하는 것이 일반적이나, 괘불과 같은 불교회화 유형처럼 크기와 규모가 유산의 기능과 밀접한 경우에는 설명에 포함한다.
표기 형식 정의(Format Definitions):
F.1 (제목 구성) 안내문의 제목은 국가유산 지정 명칭을 사용한다. 서울 숭례문을 숭례문이라고 하는 것처럼 지명이나 지정 범위가 중복될 경우 생략 가능하다. 띄어쓰기를 허용하며, 지명이나 지정 범위 표기는 생략할 수 있다.
F.2 (제목 병기) 안내문 제목은 국문과 한자를 반드시 병기한다. 한자는 국문 제목의 80% 크기로 하거나 다음 줄에 표기한다.
F.3 (지정 유형) 지정 유형은 한글로만 표기하며, 제목의 80% 크기로 표기한다. 한자 병기는 하지 않는다.
F.4 (위치와 형태 지침) 제목에 어려운 용어가 있을 시 본문 첫 문장에 풀이를 배치한다.
F.5 (기능 정의) 관람자의 이해를 돕는 보조 설명은 본문과 시각적으로 분리하여 표기한다.
F.6 (표기 형식) 표기 위치는 본문 영역의 오른쪽 상단으로 하며, 텍스트 크기는 본문 대비 80%로 설정한다.
F.7 (표현 제약) 내용의 강조를 위한 굵게(Bold) 표기 및 괄호( ) 표기는 일체 허용하지 않는다. 부연 설명이 필요한 경우 괄호를 쓰는 대신 쉼표를 사용하거나 문장으로 풀어낸다.
F.8 (높임법) 안내문안은 높임법을 사용하지 않는 것을 원칙으로 한다. 단, 문장 내에 상하 관계가 분명한 경우(군신, 사제, 부자지간 등)에는 높임 표현을 사용할 수 있다. (예: 명종 임금이 세운 것이다. (O))
F.9 **서술형 종결어미 '~이다.'를 사용한다**. 
F.10 (외래어) 본문에 외래어가 나올 경우 별도의 어원 표기는 하지 않는다. (단, 영어 안내문 작성 시에는 해당 모듈(A-2)의 지침을 따른다.)
한자 및 숫자 표기 정의(Character & Numeric Definitions):
N.1 (한자 사용) 제목, 인물, 지명, 명칭 및 가치 이해에 필수적인 경우를 제외하고 한자 사용을 엄격히 제한함.
N.2 (한자 빈도) 본문 내 첫 노출 시 1회만 표기. 제목과 중복되는 단어는 본문에서 한자 표기 생략.
N.3 (인물 한자) 직접 관련 인물만 병기. 사망/출생 연도는 절대 표기하지 않음.
N.4 (인물 호) 인물의 호는 되도록 쓰지 않는다. 다만, 호가 이름과 함께 인물을 부연 설명하거나 호가 이름을 대체할 시에는 표기할 수 있다. 한자는 호나 이름 뒤에 괄호 없이 한 칸 띄어 표기하며, 호와 이름 모두 표기 시 이름 뒤에 한꺼번에 넣는다. (예: 퇴계 이황 退溪 李滉)
N.5 (숫자 표기) 연도, 연대, 물량을 나타내는 숫자는 아라비아 숫자로 적는다. 국가유산 명칭 및 고유명사에 포함된 숫자는 한글로 적는다.
N.6 (절대 연도) 연도를 확실히 알면 절대 연도로 쓰고, 확실치 않으면 세기, 세기도 불분명하면 시대로 표기한다. 대략의 연도는 절대 연도 뒤에 '무렵', '즈음', '경' 등을 붙여 표기한다.
N.7 (왕 재위 연호) 왕의 재위 기간은 괄호 없이 본문보다 작게 표기하는 것을 원칙으로 하되, 연도 뒤에 '재위'라고 적는다. (예: 1392~1398 재위)
N.8 (수목 수령) 수목 안내판에서 수령은 해마다 늘어나므로 대략 표기한다. 단, 수목을 심은 연도를 정확히 알 경우 절대 연도를 직접 표기할 수 있다.
N.9 (도량형) 미터법 준수 및 기호로 적는다. (예: 10 m) 숫자와 단위 사이 띄어쓰기 준수.
N.10 (규격) 규모 설명 시 단위는 통일하여 가로, 세로, 높이, 두께 순으로 표기한다. 회화는 세로, 가로 순으로 적는다.
N.11 (수치 통일) 복문, 중문 등 한 문장에서 단위는 가장 많이 사용된 것으로 통일한다. 수치 차이가 클 경우 소수 첫째 자리까지 표기한다.
N.12 (고어) 고어가 고유명사 안에 있으면 그대로 쓰고, 단독으로 사용 시에는 현대어로 바꾼다.
N.13 (외래어/용어풀이): 용어 풀이 시 전문 사전의 정의를 평이한 공공언어로 순화하여 서술한다.
지형 및 방향 표기 정의 (Geography & Direction Definitions)
D.1 (시점/방향 기준) 방향은 국가유산을 바라보는 관람자의 관점에서 기술한다.
D.2 (예외 기준) 안내판이 국가유산을 직접 가리지 않도록 관람 동선과 동떨어진 곳에 설치된 경우, 방향은 안내판이 설치된 현재 위치를 기준으로 기술한다.
D.3 (방위 사용) 동서남북의 방위는 날씨에 따라 식별이 어려울 수 있으므로 사용하지 않는다.
D.4 (방위 예외) 지형이나 이론 등 일반적 학설을 설명하는 특수한 경우, 또는 종합안내판/권역안내판에는 방위를 사용할 수 있다.
D.5 (권역 안내) 국가유산이 다수 밀집되어 혼동을 줄 수 있는 경우, 권역안내판 지도에 각 국가유산을 구분하여 적는 방법을 권장한다.
형식 및 내용 예외 사항 (Exception Definitions)
DEFINE [Module A-2] AS """"외국인""""
Module_ID: A-2,
Target_Audience: 외국인
Document_Type: 국가유산 안내문
Target_Definition: 국가유산 관람객(외국인)
Document_Purpose: 외국인 관람객에게 한국 국가유산의 정보와 가치를 알리기 위한 시설물 텍스트를 생성
내용 및 구조 정의 (Content & Structure Definitions)
C.1 (정보 계층) 외국인 관람객은 한국 역사에 대한 배경지식이 다름을 인지하고, 유산 이해에 필수적인 정보는 보강하되 복잡한 인물 관계나 세부 역사는 축소·생략한다.
C.2 (정보전달 및 분량) 객관적이고 공인된 사실 위주로 기술하며, 최종 결과물은 영어 단어 기준 150~200단어 내외를 엄격히 준수한다.
C.3 (용어 정의) 첫 단락에 국문 용어(예: Seowon, Daeungjeon)의 영문 정의와 용도를 반드시 포함한다.
C.4 (맥락 연계) 국가유산을 개별적으로 서술하기보다는, 상호 연관되는 유산, 관련된 역사적 인물이나 사건 등과 연계하여 유기적으로 설명한다.
C.5 (세계사 연계) 외국인들이 친숙하게 느낄 수 있는 세계사 또는 아시아의 역사와 연계하여 설명한다.
C.6 (첫 문장 구성) "이것은 무엇인가?"에 대한 답을 최우선으로 배치하여 유산의 정체성을 즉시 인지시킨다.
C.7 (단락 구성) 설명 내용에 따라 적절한 길이로 단락을 구분하여 가독성을 높인다. (예: 서원의 정의, 제향인물, 연혁, 공간 구성, 가치 등으로 단락을 나눌 수 있음)
C.8 (감상 안내) 건물, 그림, 조각, 탑 등의 중요하거나 독특한 요소를 설명하여 관람객의 감상법을 안내한다. (회화) 불교회화의 경우, 주요 도상과 상징적 의미를 해석하여 감상법을 안내한다.
C.9 (전적 특성) 불교전적(경전, 기록)의 경우, 인쇄/필사 방식의 역사적 가치(예: 목판 인쇄술의 우수성) 및 희소성을 강조하여 가치를 부각한다.
C.10 (규모 정보) 해당 국가유산의 형태, 크기, 규모 등에 대한 설명은 생략하거나 최소화한다. (예외: C.20 참조)
C.11 (세계유산) 유네스코 세계유산 등재 정보는 명확히 표시한다.
C.12 (지역 정보) 해당 유산이 소재한 지역의 지명 변화 과정 등은 해당 유산과 직접적으로 관련 있는 내용만 추려서 작성한다.
C.13 (정보 선별) 상량문 기록, 신문 기사 등 학술적 추정 근거는 가독성을 위해 생략한다.
C.14 (지정 사항) 국가유산 지정종목 및 지정명칭 변경 사항은 대상 국가유산의 가치와 의미를 이해하는 데 필요한 사항이 아니므로 생략한다.
C.15 (현장 정서) 독자가 속한 문화적 배경에 따라 현장에서 느끼는 정서가 다를 수 있으므로, 주변 경관에 대한 자세한 묘사나 느낌은 생략한다.
C.16 (언어) 어려운 용어나 긴 문장 대신, 누구나 쉽게 이해할 수 있는 평이하고 명쾌한 문장으로 작성한다.
C.17 (독자 정의): 초등학생부터 성인까지 배경지식 없이도 이해 가능한 '보편적 공공언어'를 사용함.
C.18 (가독성 구조): 긴 문장은 피하고, 내용에 따라 적절히 문단을 나누어 시각적 편의성을 높임.
C.20 (규모 정보 예외): 일반 유산은 규모를 생략하나, **괘불(불교회화)**처럼 기능과 밀접한 경우 구체적 수치로 설명함.
표기 형식 정의 (Format Definitions)
F.1 (번안 원칙) 국문 해설문의 단순 번역을 금지하며, 외국인 독자의 이해도와 관심사를 고려하여 영문 해설문을 별도로 번안해야 한다.
F.2 (번안 프로세스) 안내문 작성은 다음의 3단계를 거쳐 최종 영문을 생성하는 프로세스를 준수한다: 1) 한국어 초안 → 2) 번안용 한국어 (외국인 시각으로 재구성) → 3) 최종 영문
F.3 (타 언어 번역) 타 언어(중국어, 일본어 등) 안내문이 필요한 경우, 최종 영문 안내문을 원문으로 하여 해당 언어로 번역하는 방식을 따른다.
F.4 (문체) 간결하고 객관적인 서술형 종결어미를 사용하며, 감성적 수식어구는 배제한다.
F.5 (어휘) 어려운 용어나 긴 문장 대신, 누구나 쉽게 이해할 수 있는 평이하고 명쾌한 문장으로 작성해야 한다.
F.6 (전문 용어) 불가피하게 전문 용어를 사용해야 하는 경우, 해당 용어의 의미를 괄호 안에 덧붙이거나 별도의 문장으로 설명한다.
F.7 (괄호) 괄호를 사용할 때, 반드시 앞 단어에서 한 칸 띄어 쓴다. (예: word (parenthesis))
F.8 (구두점) 여러 단어를 나열할 때는 쉼표 (,)를 사용하며, 가운뎃점 (·) 및 물결표 (~)는 사용하지 않는다.
F.9 (특수 부호) 홑낫표(「」), 겹낫표(『』), 홑화살괄호(〈 〉), 겹화살괄호(《 》) 등을 사용하지 않는다.
F.10 (서명/작품) 서명이나 작품명, 한국어 일반명사를 음역할 경우 반드시 이탤릭체로 표기함.
F.11 (국가유산 명칭) 국가유산 명칭은 『문화재명칭 영문 표기 기준 규칙』의 핵심 원칙(지정 유형+명칭+고유 명칭 순, 지정 유형 번역 금지)을 따르며, 길이가 길어 줄 나눔이 필요한 경우 의미 단위에 따라 줄 나눔을 한다.
F.12 (띄어쓰기/대문자) 영문 명칭의 띄어쓰기는 문화재 지정 명칭 국문의 단어 단위로 띄어 쓰는 것을 원칙으로 한다. 도서/회화 등 고유한 이름 전체를 로마자로 표기하는 경우, 첫 글자만 대문자로 쓰고 나머지 단어의 첫 글자는 소문자로 표기할 수 있다.
F.13 (줄 나눔) 영문 명칭의 길이가 길어 줄 나눔이 필요한 경우, 의미 단위에 따라 줄 나눔을 한다. 줄 끝에서 단어를 이음표(-)로 끊어 쓰지 않는다.
F.14 (지명 생략) 국문 명칭이 지명을 포함하는 경우, 도로 표지판 등 영문 표기에서는 소재지 표시를 위한 지명은 상황에 따라 생략할 수 있다.
F.15 (작가 표기) 명칭에 작가 이름이 포함된 경우는 전치사(by)를 이용하여 표기한다.
F.16 (불교 전적/회화) 불교 관련 전적은 제목 전체를 로마자로 표기하되 괄호 안에 의미역 표기를 병기할 수 있다. 불화 작품은 작품의 종류와 사찰 이름을 먼저 기술하고 괄호 속에 내용 주제를 의미역으로 표기한다.
한자 및 숫자 표기 정의 (Character & Numeric Definitions)
N.1 (시기 병기) 왕조나 특정 시대 언급 시 반드시 **존속 기간(Year)**을 병기한다. (예: Goryeo period (918–1392))
N.2 (왕조 기간) 한 왕조의 전기와 후기를 구분해 쓸 경우 'the early period of the Goryeo dynasty (918-1392)' 형식을 사용한다.
N.3 (기년 표기): 기원전/후는 BCE, CE를 사용한다.
N.4 (재위 표기): 왕의 재위 기간은 **'r.'**을 써서 생몰년과 구분한다. (예: King Sukjong (r. 1674–1720))
N.5 (줄표) 기간, 거리, 범위 등을 나타낼 때는 줄표(-)를 쓴다.
N.6 (단위 서식): 숫자와 단위('cm', 'm') 사이에는 반드시 한 칸의 공백을 둔다. (예: 10 m)
N.7 (규격) 규모 설명 시 단위는 통일하여 가로, 세로, 높이, 두께 순으로 표기한다. 회화 및 불교전적은 세로, 가로 순으로 적는다.
N.8 (음역 표기) 『국어의 로마자 표기법』을 따르되, 인명·지명·건물명 등 필수적인 경우로 최소화한다.
N.9 (음역 대상) 인명, 지명, 건물의 이름 등 꼭 필요한 경우에만 음역 표기를 사용한다.
N.10 (외국어 표기) 외국의 인명, 지명, 서명 등은 해당 국가의 로마자 표기법에 따라 표기하며, 『국어의 로마자 표기법』을 따르지 않는다.
지형 및 방향 표기 정의 (Geography & Direction Definitions)
D.1 (방향 기준) 방향은 국가유산을 바라보는 관람자의 관점에서 기술한다.
D.2 (예외 기준) 안내판이 국가유산을 직접 가리지 않도록 관람 동선과 동떨어진 곳에 설치된 경우, 방향은 안내판이 설치된 현재 위치를 기준으로 기술한다.
D.3 (방위 사용) 식별이 어려운 동서남북 방위는 원칙적으로 사용하지 않는다.
D.4 (방위 예외) 지형이나 이론 등 일반적 학설을 설명하는 특수한 경우, 또는 종합안내판/권역안내판에는 방위를 사용할 수 있다.
D.5 (권역 안내) 국가유산이 다수 밀집되어 혼동을 줄 수 있는 경우, 권역안내판 지도에 각 국가유산을 구분하여 적는 방법을 권장한다.
형식 및 내용 예외 사항 (Exception Definitions)
C.20 (규모 정보 예외) 해당 국가유산의 형태나 크기, 규모 등에 대한 설명은 생략하는 것이 일반적이나, 괘불(불교회화)과 같은 유형처럼 크기와 규모가 유산의 기능과 밀접한 경우에는 설명에 포함한다.
DEFINE [Module B] AS """"유형""""
1. 아동(Children):
B.A.1 (언어/어휘) 초등학교 저학년 수준의 어휘를 사용하며, 문장은 매우 짧고 단순하게 구성한다. 전문 용어는 쉬운 비유(예: '스님의 무덤', '돌로 만든 탑')로 대체한다.
B.A.2 (내용 깊이) 역역사적 사실보다 흥미로운 설화, 전설(C.2) 중심으로 구성하며 학문적 가치는 최소화한다.
B.A.3 (감상 안내) 감상 안내(C.6)를 질문이나 행동 지침 형태로 전환한다.
B.A.4 (시기 표기): '1000년 전', '삼국시대 신라'와 같이 대략적인 시점 위주로 설명한다.
B.A.5 (문체): 친근한 대화체를 일부 허용하되, 정보 전달 문장은 '~이다.' 형식을 유지한다.
B.A.6 (분량 제한): 공백 포함 300자 이내를 엄격히 준수한다.
2. 일반(General Public):
B.G.1 (표준 공공언어): 평이한 표준 공공언어를 사용한다. 전문 용어 사용 시 괄호를 사용하지 않고 문장 내에서 풀이하거나 위첨자(소자)를 활용한다.
B.G.2 (내용 균형): 역사적 사실(C.4)과 문화적 가치(C.5)를 중심으로 하되, 설화(C.2)를 적절히 배합한다.
B.G.3 (정보 위계): 첫 문장에서 해당 유산의 대표적 가치를 명쾌하게 전달한다.
B.G.4 (분량 제한): 공백 포함 500자 내외를 엄격히 준수한다. (최대 4문단)
3. 전문가(Experts): 
B.E.1 (학술적 밀도): 전문 학술 용어의 사용을 허용하며 정보의 밀도를 높인다.
B.E.2 (심화 서술): 제작 기법(N.10), 구체적 사료 근거, 시맨틱 개체(인물, 화승 등)를 상세히 서술한다.
B.E.3 (전문 용어 처리): 난해한 용어는 본문 내 풀이 대신 안내판 하단 주석(각주) 방식을 우선 사용한다.
B.E.4 (데이터 정밀도): 연도는 절대 연도(N.6)를 기록하며, 도량형(N.9) 수치를 소수 첫째 자리까지 정확히 기술한다.
B.E.5 (분량 제한): 공백 포함 800자 내외를 준수한다.
4. 시니어(Seniors):
B.S.1 (가독성 우선): 한자어에 익숙함을 고려하되, 현대 공공언어 사용을 원칙으로 하여 문장을 간결하게 구성한다.
B.S.2 (서사 구조): 역사적 사건을 시간 흐름(연대기순)에 따라 배치하여 정보의 안정감을 높인다.
B.S.3 (존중 어조): 관람자의 연륜을 존중하는 정중하고 안정적인 어조를 유지한다.
B.S.4 (시각적 배려): 정보의 밀도를 낮추고 문단 간 구분을 명확히 하여 눈의 피로를 최소화하는 문장을 생성한다.
B.S.5 (분량 제한): 공백 포함 500자 내외를 준수한다. (일반형과 동일하되 가독성 위주 구성)
DEFINE [Module References] AS """"Src_M_2024"""": “문화재청 안내문 제작 표준 가이드라인 (2024)”
DEFINE [Module References] AS """"Src_M_2019"""": “문화재 영어 안내문 작성 가이드라인(개정판) (2019)”
""" # 20260317 로 업데이트 # 줄일 필요 또는 고정하던지해야 성능 떨어짐.

cypher_prompt = PromptTemplate( #쿼리 생성 프롬프트 내장 기능을 더 조회해볼것.
    input_variables=["schema", "question"],
    template="""
너는 Neo4j Cypher 전문가이다.
반드시 아래 스키마에 존재하는 라벨, 관계, 속성만 사용한다.

중요 규칙:
1. Cypher만 출력한다. 설명 금지.
2. MATCH, WHERE, RETURN, LIMIT만 사용한다.
3. CREATE, MERGE, DELETE, SET, REMOVE, CALL 금지.
4. 노드 라벨은 반드시 아래 형식으로 쓴다:
   MATCH (p:`LabelName`)
5. 여러 라벨을 OR로 비교할 때는 반드시 아래 형식으로 쓴다:
   WHERE p:`LabelA` OR p:`LabelB`
6. 속성 접근은 반드시 아래 형식으로 쓴다:
   p.propertyName
7. 절대 이런 문법을 쓰지 마라:
   p:`LabelA OR p`:`LabelB`
   p`.property
8. 결과는 최대 10개만 반환한다.

그래프 스키마:
{schema}

질문:
{question}
""",
)

qa_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    cypher_prompt=cypher_prompt,
    verbose=True,
    allow_dangerous_requests=True, #조사
    return_intermediate_steps=True,  #조사 
    top_k=10,
)


# 2) 입력 모델
class GenerateIn(BaseModel):
    prompt: dict
    
class E5Embedder(Embedder):
    def __init__(self):
        super().__init__()
        self.model = SentenceTransformer("intfloat/multilingual-e5-small")

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(
            f"query: {text}",
            normalize_embeddings=True
        ).tolist()

embedder = E5Embedder()


# 3) Neo4j에서 지식 조회 : Cypher 조회형 RAG 테스트
def get_people_context(ch_id: str = "CH000001") -> str:
    query = """
    MATCH (p:Person)-[r]->(a:Artwork {ch_id: $ch_id})
    RETURN p.name_modern AS name,
           p.rank AS rank,
           p.affiliation AS affiliation,
           type(r) AS rel_type,
           r.note AS note
    ORDER BY rel_type
    """

    records, _, _ = driver.execute_query(
        query,
        ch_id=ch_id,
    )

    if not records:
        return "참여 인물 정보 없음"

    # 🔥 1. 관계 그룹화 (PDF에서 중요 포인트)
    grouped = {}
    for r in records:
        rel = r["rel_type"]

        # BELONGS_TO는 통계용이라 제외 (PDF 권장)
        if rel == "BELONGS_TO":
            continue

        if rel not in grouped:
            grouped[rel] = []

        grouped[rel].append(r)

    # 🔥 2. 자연어 변환 (LLM 입력용)
    lines = []
    for rel, items in grouped.items():
        lines.append(f"[{rel}]")

        for p in items[:10]:  # 너무 길어지면 제한
            lines.append(
                f"- {p['name']} ({p['rank']}, {p['affiliation']})"
                + (f" / {p['note']}" if p["note"] else "")
            )

        lines.append("")  # 줄바꿈

    context = "\n".join(lines).strip()

    return context

def get_icon_symbol_context(ch_id: str = "CH000001") -> str:
    query = """
    MATCH (i:Icon)-[:APPEARS_IN]->(a:Artwork {ch_id: $ch_id})
    WHERE i.role IN ['본존', '6대여래', '6대보살']
    RETURN i.name AS name,
           i.mudra AS mudra,
           i.attribute AS attribute,
           i.role AS role
    ORDER BY
      CASE i.role
        WHEN '본존' THEN 1
        WHEN '6대여래' THEN 2
        WHEN '6대보살' THEN 3
        ELSE 4
      END,
      i.name
    """

    records, _, _ = driver.execute_query(
        query,
        ch_id=ch_id,
        database_=NEO4J_DB
    )

    if not records:
        return "본존불 및 주요 권속 도상 정보 없음"

    lines = []
    lines.append("[본존불 및 주요 권속의 상징물 정보]")

    for r in records:
        name = r["name"] or ""
        mudra = r["mudra"] or "정보 없음"
        attribute = r["attribute"] or "정보 없음"
        role = r["role"] or "정보 없음"

        lines.append(
            f"- {name} / 역할: {role} / 수인: {mudra} / 지물: {attribute}"
        )

    return "\n".join(lines)

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


class GenerateIn(BaseModel):
    prompt: str | dict
    model: str | None = None  # 없으면 .env의 MODEL 사용
    

        
@app.post("/api/generate_0417") # embedding vector DB에서 유사한 스타일의 안내문 검색 + Neo4j 조회 포함 버전 + GraphRAG 적용 버전
async def generate_raw(payload: GenerateIn):
    
    retriever = HybridRetriever(
    driver=driver,
    vector_index_name="heritage_vector_index",
    fulltext_index_name="heritage_fulltext_index",
    embedder=embedder,
    neo4j_database=NEO4J_DB,
    )

    query = "장곡사 미륵불 괘불탱의 특징과 제작 배경을 알려줘"

    # 1) 임베딩 확인
    vec = embedder.embed_query(query)
    print("벡터 타입:", type(vec))
    print("벡터 차원:", len(vec))
    print("벡터 앞 5개:", vec[:5])

    # 2) retriever 결과 확인
    result = retriever.search(
        query_text=query,
        top_k=5
    )
    model_name = "gemini-2.5-flash" # api 버전에 따라 모델명 변경 필요
    gemini = genai.GenerativeModel(model_name)
    
# ✅ 프롬프트 엔지니어링 (RAG context 포함)
    prompt_obj = payload.prompt

    role = prompt_obj.get("role")
    depth = prompt_obj.get("depth")
    detail = prompt_obj.get("detail")

    print("디버그",role, depth, detail) # 디버그용
    # 임베딩 벡터 DB에서 유사한 스타일의 안내문 검색
    # 여기서 Neo4j 조회
    # artwork_name = "장곡사 미륵불 괘불탱"
    neo4j_context = get_people_context("CH000001") # 예시로 인물 ID 사용, 실제로는 작품 ID로 조회해야 할 수도 있음

    engineered_prompt = f"""
    {system}
    ### [User Input Data]
    // 아래 내용을 채워서 명령을 실행한다.
    1. 기본 정보
    - {{대상 유산}}: [장곡사 미륵불 괘불탱]
    - {{분류}}: [장곡사 미륵불 괘불탱]
    - {{명칭_한글}}: [장곡사 미륵불 괘불탱]
    - {{명칭_한자}}: [長谷寺 彌勒佛 掛佛幀]
    - {{명칭_영어}}: [Hanging Painting of Janggoksa Temple (Maitreya Buddha)]
    - {{관람객 국적}}: {role}
    // [내국인 | 외국인]
    - {{관람객 유형}}: {depth} 
    // [아동 | 일반 | 전문가 | 시니어]
    - {{안내문 유형}}: [개별] 
    // [종합 | 권역 | 개별]
    - {{목표 언어(선택)}}: {detail}
    // [예: 영어, 일본어, 또는 공란]
    2. {{문화유산 지식 데이터}} (Knowledge Base)
    // 생성의 근거가 되는 인문 지식 데이터
    (1) 사실 정보
    - 국가유산 지정 등급: [국보]
    - 제작연도_서기: [1673]
    - 제작시기_연호: [강희 12년, 현종 14년]
    - 시대: [조선]
    - 크기/재질: [세로 898cm, 가로 586cm/마본채색(삼베에 그린 것으로, 비단에 그린 것이 아니다)]
    - 출토/소장: [장곡사]
    - 주제분류: [미륵불괘불도, 영산회상도]
    - 형식_구도: [대관보살형 입상, 군도 형식, 장엄신]
    - 주존불 [미륵존불]
    - 주요협시 목록: [비로자나불, 노사나불, 대묘상보살, 법림보살]
    - 그 외 협시: {result}
    - 수화승: [철학(哲學)]
    - 참여 인물: {neo4j_context}
    - 조성배경: [화기의 서두에는 왕실의 안녕을 비는 관용적인 축원 문구가 기술되어 있고, 이어지는 본문에는 1673년 장곡사에서 영산대회(靈山大會)를 위해 괘불을 조성했다는 내용과 함께 모든 중생의 성불을 비는 회향문이 적혀 있다.]
    - 핵심내용: [화기에는 """"영산대회괘불탱"""", 방제에는 """"미륵존불""""이라 명시되어 본존이 """"석가모니불""""과 """"미륵불""""의 성격을 동시에 지님을 알 수 있다. 화면은 """"비로자나불""""과 """"노사나불""""을 함께 배치한 삼신불 형식을 따르면서 동시에 미륵의 협시인 """"대묘상""""·""""법림보살""""이 등장하는 독특한 형태이다. 이는 연꽃 줄기(용화수)를 든 본존불이 영산회상도의 구성과 결합하여 나타난 희소한 사례로, 미륵불로서의 특징과 영산회상의 배치가 공존하는 조선 후기 불화의 복합적 양상을 보여주는 중요한 자료이다.]
    - 
    (2) 시소러스 (Thesaurus & Glossary)
    // 전문 용어의 의미와 외국인용 번역 가이드

    DEFINE [Thesaurus: Term] AS """"""""미륵존불“
    - 대표명_한국어: 미륵존불
    - 대표명_영어: Maitreya Buddha
    - 대표명_한자번체: 彌勒尊佛
    - 핵심정의: 미래에 성불하여 하생(下生)할 미륵.

    - 대표명_한국어: 비로자나불
    - 대표명_영어: Vairocana Buddha
    - 대표명_한자번체: 毘盧遮那佛
    - 핵심정의: 불교의 진리를 상징하는 부처. 화엄종의 중심 부처. '두루 비치는 빛'을 뜻하며 원래 인도어로 '태양'을 의미. 밀교(금강승)에서는 대일여래(大日如來).

    DEFINE [Thesaurus: Term] AS """"""""노사나불""""""""
    - 대표명_한국어: 노사나불
    - 대표명_영어: Locana Buddha
    - 대표명_한자번체: 盧舍那佛
    - 핵심정의: 비로자나불의 보신불(報身佛)로, 오랜 수행을 통해 공덕을 쌓아 원만하게 깨달음을 성취한 부처이다.

    DEFINE [Thesaurus: Term] AS """"""""대묘상보살“- 대표명_한국어: 대묘상보살
    - 대표명_영어: 
    - 대표명_한자번체: 大妙相菩薩
- 핵심정의: 대묘상보살(大妙相菩薩)은 미륵불의 협시보살 중 하나로, 미륵경전 대신 밀교경전에서 처음 언급된 후 조선시대 1678년에 제작된 청양 장곡사 미륵불괘불탱에서 법림보살(法林菩薩)과 함께 미륵불의 협시보살로 등장하고 있어 법림보살과 함께 미륵불의 공식적인 협시보살로 정착된 것으로 보인다.
    DEFINE [Thesaurus: Term] AS """"""""법림보살""""""""
    - 대표명_한국어: 법림보살
  - 대표명_영어: 
  - 대표명_한자번체: 法林菩薩
  - 핵심정의: 법림보살(法林菩薩)은 미륵불(彌勒佛)의 협시보살(脇侍菩薩) 중 한 하나로, 초기 경전에는 언급이 없으나 조선시대 이후 간행된 불교 의례집인 『염불작법』과 불화(예: 장곡사 미륵괘불) 등에서 대묘상보살과 함께 미륵불의 협시로 정착된 보살이다.  (3) 참고문장
    (3) 모범 답안/참조 문안
    // 톤앤매너 참고용 문장 (선택 사항)
    ---
[EXECUTION COMMAND]
위 [User Input Data]를 로드하고, [SYSTEM] 로직을 가동하여 결과를 출력하라."""
    # print("엔지니어링된 프롬프트:", engineered_prompt) # 디버그용
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
    

class GraphQAIn(BaseModel):
    prompt: dict

@app.post("/api/graph-cypher-qa")
async def graph_cypher_qa(payload: GraphQAIn):
    model_name = "gemini-2.5-flash" # api 버전에 따라 모델명 변경 필요
    gemini = genai.GenerativeModel(model_name)
    
    try:
        prompt_obj = payload.prompt or {}

        role = prompt_obj.get("role", "내국인")
        depth = prompt_obj.get("depth", "일반")
        detail = prompt_obj.get("detail", "한국어")

        # 질문이 따로 없으면 기본 질문
        # user_query = prompt_obj.get(
        #     "query",
        #     "이 그래프에서 Person이 누구인지 알려줘"
        # )
        queries = {
            # "제작연도": "장곡사 미륵불 괘불탱의 제작 연도를 알려줘",
            "참여 인물": "장곡사 미륵불 괘불탱의 참여 인물을 알려줘", 
            # "주요 도상": "장곡사 미륵불 괘불탱의 주요 도상을 알려줘",
            # "본존과 협시": "장곡사 미륵불 괘불탱의 본존과 협시를 알려줘",
        } 
        # dh2026 목적 고정. 쿼리.
        
        THESAURUS_TERMS = {
            "미륵존불": "미륵존불",
            "비로자나불": "비로자나불",
            # "노사나불": "노사나불",
            # "대묘상보살": "대묘상보살",
            # "법림보살": "법림보살",
        }
        
        results = {}

        for key, q in queries.items():
            try:
                r = qa_chain.invoke({"query": q})

                results[key] = {
                    "answer": r.get("result"),
                    "steps": r.get("intermediate_steps", [])
                }

            except Exception as e:
                results[key] = {
                    "error": str(e)
                }

        thesaurus_results = {}

        for key, term in THESAURUS_TERMS.items():
            q = f"""
            RDF 그래프에서 '{term}'에 대한 정보를 찾아줘.
            가능하면 한국어 대표명, 영어명, 한자명, 핵심정의를 포함해서 정리해줘. 
            """
        # 싸이퍼 쿼리 만들어주는 플러그인, 쿼리 불러오는 프롬프트 엔제니어링 진행, 
            try:
                r = qa_chain.invoke({"query": q})
                thesaurus_results[key] = r.get("result")
            except Exception as e:
                thesaurus_results[key] = f"조회 실패: {str(e)}"
        
        engineered_prompt = f"""
    {system}
    ### [User Input Data]
    // 아래 내용을 채워서 명령을 실행한다.
    1. 기본 정보
    - {{대상 유산}}: [장곡사 미륵불 괘불탱]
    - {{분류}}: [장곡사 미륵불 괘불탱]
    - {{명칭_한글}}: [장곡사 미륵불 괘불탱]
    - {{명칭_한자}}: [長谷寺 彌勒佛 掛佛幀]
    - {{명칭_영어}}: [Hanging Painting of Janggoksa Temple (Maitreya Buddha)]
    - {{관람객 국적}}: {role}
    // [내국인 | 외국인]
    - {{관람객 유형}}: {depth} 
    // [아동 | 일반 | 전문가 | 시니어]
    - {{안내문 유형}}: [개별] 
    // [종합 | 권역 | 개별]
    - {{목표 언어(선택)}}: {detail}
    // [예: 영어, 일본어, 또는 공란]
    2. {{문화유산 지식 데이터}} (Knowledge Base)
    // 생성의 근거가 되는 인문 지식 데이터
    (1) 사실 정보
    - 국가유산 지정 등급: [국보]
    - 제작연도_서기: [1673]
    - 제작시기_연호: [강희 12년, 현종 14년]
    - 시대: [조선]
    - 크기/재질: [세로 898cm, 가로 586cm/마본채색(삼베에 그린 것으로, 비단에 그린 것이 아니다)]
    - 출토/소장: [장곡사]
    - 주제분류: [미륵불괘불도, 영산회상도]
    - 형식_구도: [대관보살형 입상, 군도 형식, 장엄신]
    - 주존불 [미륵존불]
    - 주요협시 목록: [비로자나불, 노사나불, 대묘상보살, 법림보살]
    - 그 외 협시: [80여 명의 시주자 동참 (사회/경제적 중요성)]
    - 수화승: [철학(哲學)]
    - 참여 인물: {results.get("참여 인물", {}).get("answer")}
    - 조성배경: [화기의 서두에는 왕실의 안녕을 비는 관용적인 축원 문구가 기술되어 있고, 이어지는 본문에는 1673년 장곡사에서 영산대회(靈山大會)를 위해 괘불을 조성했다는 내용과 함께 모든 중생의 성불을 비는 회향문이 적혀 있다.]
    - 핵심내용: [화기에는 """"영산대회괘불탱"""", 방제에는 """"미륵존불""""이라 명시되어 본존이 """"석가모니불""""과 """"미륵불""""의 성격을 동시에 지님을 알 수 있다. 화면은 """"비로자나불""""과 """"노사나불""""을 함께 배치한 삼신불 형식을 따르면서 동시에 미륵의 협시인 """"대묘상""""·""""법림보살""""이 등장하는 독특한 형태이다. 이는 연꽃 줄기(용화수)를 든 본존불이 영산회상도의 구성과 결합하여 나타난 희소한 사례로, 미륵불로서의 특징과 영산회상의 배치가 공존하는 조선 후기 불화의 복합적 양상을 보여주는 중요한 자료이다.]
    - 
    (2) 시소러스 (Thesaurus & Glossary)
    // 전문 용어의 의미와 외국인용 번역 가이드
    {thesaurus_text}
        DEFINE [Thesaurus: Term] AS """"""""노사나불""""""""
    - 대표명_한국어: 노사나불
    - 대표명_영어: Locana Buddha
    - 대표명_한자번체: 盧舍那佛
    - 핵심정의: 비로자나불의 보신불(報身佛)로, 오랜 수행을 통해 공덕을 쌓아 원만하게 깨달음을 성취한 부처이다.

    DEFINE [Thesaurus: Term] AS """"""""대묘상보살“- 대표명_한국어: 대묘상보살
    - 대표명_영어: 
    - 대표명_한자번체: 大妙相菩薩
    - 핵심정의: 대묘상보살(大妙相菩薩)은 미륵불의 협시보살 중 하나로, 미륵경전 대신 밀교경전에서 처음 언급된 후 조선시대 1678년에 제작된 청양 장곡사 미륵불괘불탱에서 법림보살(法林菩薩)과 함께 미륵불의 협시보살로 등장하고 있어 법림보살과 함께 미륵불의 공식적인 협시보살로 정착된 것으로 보인다.
        DEFINE [Thesaurus: Term] AS """"""""법림보살""""""""
        - 대표명_한국어: 법림보살
    - 대표명_영어: 
    - 대표명_한자번체: 法林菩薩
    - 핵심정의: 법림보살(法林菩薩)은 미륵불(彌勒佛)의 협시보살(脇侍菩薩) 중 한 하나로, 초기 경전에는 언급이 없으나 조선시대 이후 간행된 불교 의례집인 『염불작법』과 불화(예: 장곡사 미륵괘불) 등에서 대묘상보살과 함께 미륵불의 협시로 정착된 보살이다.  (3) 참고문장
        (3) 모범 답안/참조 문안
        // 톤앤매너 참고용 문장 (선택 사항)
    ---
[EXECUTION COMMAND]
위 [User Input Data]를 로드하고, [SYSTEM] 로직을 가동하여 결과를 출력하라."""
    # print("엔지니어링된 프롬프트:", engineered_prompt) # 디버그용
        response = gemini.generate_content(engineered_prompt)
        print(results)
        return {
            "results": results,
            "thesaurus_results": thesaurus_results,
            "role": role,
            "depth": depth,
            "detail": detail,
            "model": model_name,
            "text": response.text,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))