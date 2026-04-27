from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from dotenv import load_dotenv
import google.generativeai as genai
from services.load_prompt import load_prompt # 프롬프트를 별도 파일로 관리하기 위한 유틸 함수

from neo4j import GraphDatabase

from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY_3")) 

app = FastAPI(title="장곡사 미륵불 괘불탱 안내문")

# 앱 시작 시 연결 확인

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
# curl http://49.247.14.81:11434/api/tags

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

# schema를 최신 상태로 읽어오기
graph.refresh_schema()

# 2) LLM과 체인 설정 (google gemini 2.5 flash 모델 사용 - 20260427 기준 최신 모델명)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY_IRO"),
    temperature=0,
)
guidelines = load_prompt("services/prompts/system_prompt.md") # 20260317 로 업데이트 # 줄일 필요 또는 고정하던지해야 성능 떨어짐.

cypher_prompt = PromptTemplate(
    input_variables=["schema", "question"],
    template="""
너는 Neo4j Cypher 전문가이다.
반드시 아래 스키마에 존재하는 라벨, 관계, 속성만 사용한다.

중요 규칙:
1. Cypher만 출력한다.
2. MATCH, WHERE, RETURN, LIMIT만 사용한다.
3. CREATE, MERGE, DELETE, SET, REMOVE, CALL 금지.
4. MATCH 괄호 안에서 OR를 쓰지 마라.
5. 여러 라벨 후보는 WHERE에서 OR로 처리한다.
6. 코드블록 표시 ```cypher```를 붙이지 마라.

그래프 스키마:
{schema}

질문:
{question}
"""
)

qa_chain = GraphCypherQAChain.from_llm(
    llm=llm, # llm_cypher는 쿼리 생성용, 최종안내문 llm과는 다른 모델.
    graph=graph, #schema는 그래프에서 자동으로 읽어오지만, 스키마가 너무 크거나 복잡하면 프롬프트에 직접 넣어서 쿼리 생성에 활용할 수도 있다.
    cypher_prompt=cypher_prompt,
    # include_types=["Artwork", "Person", "Icon", "CREATED_BY", "DEPICTS"], #조회할 노드 라벨과 관계 타입을 지정해서 쿼리 생성 시 활용하도록 함. (지정 안하면 스키마 전체에서 조회)
    verbose=True, #체인 실행 시 디버그 로그 출력 여부
    validate_cypher=True, #생성된 Cypher 쿼리가 유효한지 검증 (문법 체크)
    allow_dangerous_requests=True, #위험한 쿼리 허용 거절 (예: 전체 노드 삭제하는 쿼리 등)
    return_intermediate_steps=True,  #최종 답변 외에 중간에 생성된 Cypher 쿼리와 그래프에서 반환된 원시 결과도 함께 반환 (디버그 및 분석용) 
    top_k=10,
)

# 1. 라우터 프롬프트
router_prompt = PromptTemplate(
    input_variables=["question"],
    template="""
다음 질문을 보고 적절한 쿼리 타입을 하나만 선택하라.

옵션:
1. 참여 인물 조회
2. 도상 정보 조회
3. 제작 연도 조회
4. 기타

질문:
{question}

답:
"""
)

router_chain = router_prompt | llm | StrOutputParser()


participant_query = """
MATCH (p)
WHERE (
  p:ns0__E21_Person
  OR p:ns2__HistoricalPerson
  OR p:ns4__Person
)
AND p.ns2__affiliationText CONTAINS "장곡사"
RETURN
  p.rdfs__label AS name,
  p.ns4__name AS modern_name,
  p.ns2__nameOriginal AS original_name,
  p.ns2__roleModern AS role,
  p.ns2__roleOriginal AS original_role,
  p.rdfs__comment AS description
LIMIT 20
"""

participants = graph.query(participant_query)
print("참여인물", participants)
# 3) 근거 기반 답변 생성 함수
def answer_with_evidence(question: str):
    evidence_query = """
    MATCH (n)
    WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS "장곡사")
    RETURN labels(n) AS labels, keys(n) AS props, n
    LIMIT 20
    """

    evidence = graph.query(evidence_query)

    final_prompt = f"""
        다음 Neo4j 조회 결과만 근거로 질문에 답하라.
        근거 데이터에 없는 내용은 추측하지 말고 "근거 데이터에서 확인되지 않습니다"라고 답하라.

        질문:
        {question}

        근거 데이터:
        {evidence}

        답변:
        """

    response = llm.invoke(final_prompt)

    return {
        "question": question,
        "evidence": evidence,
        "answer": response
    }
    
def run_graph_query(question: str):
    route = router_chain.invoke({"question": question}).strip()
    print("선택된 route:", route)

    if "참여 인물" in route:
        return {
            "route": route,
            "data": graph.query(participant_query)
        }

    elif "도상" in route:
        return {
            "route": route,
            "data": graph.query("""
            MATCH (n)
            WHERE n:ns2__IconographicFigure
            RETURN
              n.rdfs__label AS label,
              n.skos__prefLabel AS prefLabel,
              n.skos__definition AS definition,
              n.rdfs__comment AS comment
            LIMIT 20
            """)
        }

    elif "제작 연도" in route:
        return {
            "route": route,
            "data": graph.query("""
            MATCH (n)
            WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS "1673")
            RETURN labels(n) AS labels, keys(n) AS props, n
            LIMIT 10
            """)
        }

    else:
        # 전혀 새로운 질문은 여기로 보냄
        return {
            "route": route,
            "mode": "llm_cypher_fallback",
            "data": qa_chain.invoke({"query": question})
        }

result = run_graph_query("장곡사 미륵불 괘불탱의 제작시기를 알려줘")
print(result)

result = answer_with_evidence("장곡사 미륵불 괘불탱은 무슨 역사적 의의가 있어?")
print("근거", result["answer"])

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
        
        
# def query_graph(queries):
#     results = {}

#     for key, q in queries.items():
#         try:
#             r = qa_chain.invoke({"query": q})

#             results[key] = {
#                     "answer": r.get("result"),
#                     "steps": r.get("intermediate_steps", [])
#             }

#         except Exception as e:
#             results[key] = {
#                 "error": str(e)
#             }
#     return results

# def query_graph_thesaurus(terms):
#     results = {}

#     for key, term in terms.items():
#         q = f"""
#         RDF 그래프에서 '{term}'에 대한 정보를 찾아줘.
#         가능하면 한국어 대표명, 영어명, 한자명, 핵심정의를 포함해서 정리해줘. 
#         """
#     # 싸이퍼 쿼리 만들어주는 플러그인, 쿼리 불러오는 프롬프트 엔제니어링 진행, 
#         try:
#             r = qa_chain.invoke({"query": q})
#             results[key] = r.get("result")
#         except Exception as e:
#             results[key] = f"조회 실패: {str(e)}"
#     return results
    

# class GraphQAIn(BaseModel):
#     prompt: dict

# @app.post("/api/graph-cypher-qa")
# async def graph_cypher_qa(payload: GraphQAIn):
#     model_name = "gemini-2.5-flash" # api 버전에 따라 모델명 변경 필요
#     gemini = genai.GenerativeModel(model_name)
    
#     try:
#         prompt_obj = payload.prompt or {}

#         role = prompt_obj.get("role", "내국인")
#         depth = prompt_obj.get("depth", "일반")
#         detail = prompt_obj.get("detail", "한국어")

#         # 질문이 따로 없으면 기본 질문
#         # user_query = prompt_obj.get(
#         #     "query",
#         #     "이 그래프에서 Person이 누구인지 알려줘"
#         # )
#         queries = { #사용자 입력 쿼리
#             # "제작연도": "장곡사 미륵불 괘불탱의 제작 연도를 알려줘",
#             "참여 인물": "장곡사 미륵불 괘불탱의 참여 인물을 알려줘", 
#             # "주요 도상": "장곡사 미륵불 괘불탱의 주요 도상을 알려줘",
#             # "본존과 협시": "장곡사 미륵불 괘불탱의 본존과 협시를 알려줘",
#         } 
#         # dh2026 목적 고정. 쿼리.
        
#         THESAURUS_TERMS = { #시소러스 조회용 고정 용어
#             "미륵존불": "미륵존불",
#             "비로자나불": "비로자나불",
#             # "노사나불": "노사나불",
#             # "대묘상보살": "대묘상보살",
#             # "법림보살": "법림보살",
#         }

#         results = query_graph(queries)
#         # thesaurus_results = query_graph_thesaurus(THESAURUS_TERMS)
#         print("그래프 쿼리 결과:", results)
#         # print("시소러스 쿼리 결과:", thesaurus_results)
        
# #         engineered_prompt = f"""
# #     {guidelines}
# #     ### [User Input Data]
# #     // 아래 내용을 채워서 명령을 실행한다.
# #     1. 기본 정보
# #     - {{대상 유산}}: [장곡사 미륵불 괘불탱]
# #     - {{분류}}: [장곡사 미륵불 괘불탱]
# #     - {{명칭_한글}}: [장곡사 미륵불 괘불탱]
# #     - {{명칭_한자}}: [長谷寺 彌勒佛 掛佛幀]
# #     - {{명칭_영어}}: [Hanging Painting of Janggoksa Temple (Maitreya Buddha)]
# #     - {{관람객 국적}}: {role}
# #     // [내국인 | 외국인]
# #     - {{관람객 유형}}: {depth} 
# #     // [아동 | 일반 | 전문가 | 시니어]
# #     - {{안내문 유형}}: [개별] 
# #     // [종합 | 권역 | 개별]
# #     - {{목표 언어(선택)}}: {detail}
# #     // [예: 영어, 일본어, 또는 공란]
# #     2. {{문화유산 지식 데이터}} (Knowledge Base)
# #     // 생성의 근거가 되는 인문 지식 데이터
# #     (1) 사실 정보
# #     - 국가유산 지정 등급: [국보]
# #     - 제작연도_서기: [1673]
# #     - 제작시기_연호: [강희 12년, 현종 14년]
# #     - 시대: [조선]
# #     - 크기/재질: [세로 898cm, 가로 586cm/마본채색(삼베에 그린 것으로, 비단에 그린 것이 아니다)]
# #     - 출토/소장: [장곡사]
# #     - 주제분류: [미륵불괘불도, 영산회상도]
# #     - 형식_구도: [대관보살형 입상, 군도 형식, 장엄신]
# #     - 주존불 [미륵존불]
# #     - 주요협시 목록: [비로자나불, 노사나불, 대묘상보살, 법림보살]
# #     - 그 외 협시: [80여 명의 시주자 동참 (사회/경제적 중요성)]
# #     - 수화승: [철학(哲學)]
# #     - 참여 인물: {results.get("참여 인물", {}).get("answer")}
# #     - 조성배경: [화기의 서두에는 왕실의 안녕을 비는 관용적인 축원 문구가 기술되어 있고, 이어지는 본문에는 1673년 장곡사에서 영산대회(靈山大會)를 위해 괘불을 조성했다는 내용과 함께 모든 중생의 성불을 비는 회향문이 적혀 있다.]
# #     - 핵심내용: [화기에는 """"영산대회괘불탱"""", 방제에는 """"미륵존불""""이라 명시되어 본존이 """"석가모니불""""과 """"미륵불""""의 성격을 동시에 지님을 알 수 있다. 화면은 """"비로자나불""""과 """"노사나불""""을 함께 배치한 삼신불 형식을 따르면서 동시에 미륵의 협시인 """"대묘상""""·""""법림보살""""이 등장하는 독특한 형태이다. 이는 연꽃 줄기(용화수)를 든 본존불이 영산회상도의 구성과 결합하여 나타난 희소한 사례로, 미륵불로서의 특징과 영산회상의 배치가 공존하는 조선 후기 불화의 복합적 양상을 보여주는 중요한 자료이다.]
# #     - 
# #     (2) 시소러스 (Thesaurus & Glossary)
# #     // 전문 용어의 의미와 외국인용 번역 가이드
# #     {thesaurus_text}
# #         DEFINE [Thesaurus: Term] AS """"""""노사나불""""""""
# #     - 대표명_한국어: 노사나불
# #     - 대표명_영어: Locana Buddha
# #     - 대표명_한자번체: 盧舍那佛
# #     - 핵심정의: 비로자나불의 보신불(報身佛)로, 오랜 수행을 통해 공덕을 쌓아 원만하게 깨달음을 성취한 부처이다.

# #     DEFINE [Thesaurus: Term] AS """"""""대묘상보살“- 대표명_한국어: 대묘상보살
# #     - 대표명_영어: 
# #     - 대표명_한자번체: 大妙相菩薩
# #     - 핵심정의: 대묘상보살(大妙相菩薩)은 미륵불의 협시보살 중 하나로, 미륵경전 대신 밀교경전에서 처음 언급된 후 조선시대 1678년에 제작된 청양 장곡사 미륵불괘불탱에서 법림보살(法林菩薩)과 함께 미륵불의 협시보살로 등장하고 있어 법림보살과 함께 미륵불의 공식적인 협시보살로 정착된 것으로 보인다.
# #         DEFINE [Thesaurus: Term] AS """"""""법림보살""""""""
# #         - 대표명_한국어: 법림보살
# #     - 대표명_영어: 
# #     - 대표명_한자번체: 法林菩薩
# #     - 핵심정의: 법림보살(法林菩薩)은 미륵불(彌勒佛)의 협시보살(脇侍菩薩) 중 한 하나로, 초기 경전에는 언급이 없으나 조선시대 이후 간행된 불교 의례집인 『염불작법』과 불화(예: 장곡사 미륵괘불) 등에서 대묘상보살과 함께 미륵불의 협시로 정착된 보살이다.  (3) 참고문장
# #         (3) 모범 답안/참조 문안
# #         // 톤앤매너 참고용 문장 (선택 사항)
# #     ---
# # [EXECUTION COMMAND]
# # 위 [User Input Data]를 로드하고, [SYSTEM] 로직을 가동하여 결과를 출력하라."""
# #     # print("엔지니어링된 프롬프트:", engineered_prompt) # 디버그용
# #         response = gemini.generate_content(engineered_prompt)
# #         print(results)
# #         return {
# #             "results": results,
# #             "thesaurus_results": thesaurus_results,
# #             "role": role,
# #             "depth": depth,
# #             "detail": detail,
# #             "model": model_name,
# #             "text": response.text,
# #         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))