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

genai.configure(api_key=os.getenv("GEMINI_API_KEY_1")) 
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
# 전역 활용되는 LLM
# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     google_api_key=os.getenv("GEMINI_API_KEY_IRO"),
#     temperature=0,
# )

# 시스템 프롬프트 로드 - 안내문 생성 시 활용되는 고정
guidelines = load_prompt("services/prompts/system_prompt.md") # 20260317 로 업데이트 # 줄일 필요 또는 고정하던지해야 성능 떨어짐.

# # 쿼리 자체를 만드는 코드 : 특정 정보만 요구하는 정보 설계를 할때는 비효율이 발생하여, 예외처리할때만 사용하도록 합니다.
# cypher_prompt = PromptTemplate(
#     input_variables=["schema", "question"],
#     template="""
# 너는 Neo4j Cypher 전문가이다.
# 반드시 아래 스키마에 존재하는 라벨, 관계, 속성만 사용한다.

# 중요 규칙:
# 1. Cypher만 출력한다.
# 2. MATCH, WHERE, RETURN, LIMIT만 사용한다.
# 3. CREATE, MERGE, DELETE, SET, REMOVE, CALL 금지.
# 4. MATCH 괄호 안에서 OR를 쓰지 마라.
# 5. 여러 라벨 후보는 WHERE에서 OR로 처리한다.
# 6. 코드블록 표시 ```cypher```를 붙이지 마라.

# 그래프 스키마:
# {schema}

# 질문:
# {question}
# """
# )

# # QA 체인 생성 - LLM이 질문을 보고 Cypher 쿼리를 생성 -> 그래프에서 실행 -> 결과 반환
# qa_chain = GraphCypherQAChain.from_llm(
#     llm=llm, # llm_cypher는 쿼리 생성용, 최종안내문 llm과는 다른 모델.
#     graph=graph, #schema는 그래프에서 자동으로 읽어오지만, 스키마가 너무 크거나 복잡하면 프롬프트에 직접 넣어서 쿼리 생성에 활용할 수도 있다.
#     cypher_prompt=cypher_prompt,
#     # include_types=["Artwork", "Person", "Icon", "CREATED_BY", "DEPICTS"], #조회할 노드 라벨과 관계 타입을 지정해서 쿼리 생성 시 활용하도록 함. (지정 안하면 스키마 전체에서 조회)
#     verbose=True, #체인 실행 시 디버그 로그 출력 여부
#     validate_cypher=True, #생성된 Cypher 쿼리가 유효한지 검증 (문법 체크)
#     allow_dangerous_requests=True, #위험한 쿼리 허용 거절 (예: 전체 노드 삭제하는 쿼리 등)
#     return_intermediate_steps=True,  #최종 답변 외에 중간에 생성된 Cypher 쿼리와 그래프에서 반환된 원시 결과도 함께 반환 (디버그 및 분석용) 
#     top_k=10,
# )


# 1. 라우터 프롬프트
router_prompt = PromptTemplate(
    input_variables=["question"],
    template="""
다음 질문을 보고 적절한 쿼리 타입을 하나만 선택하라.

옵션:
1. 참여 인물 조회
2. 도상 정보 조회
3. 제작 연도 조회
4. 시소러스 용어 조회
5. 기타

질문:
{question}

답:
"""
)

# router_chain_main = router_prompt | llm | StrOutputParser()

# # 3) 근거 기반 답변 생성 함수
# def answer_with_evidence(question: str):
#     evidence_query = """
#     MATCH (n)
#     WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS "장곡사")
#     RETURN labels(n) AS labels, keys(n) AS props, n
#     LIMIT 20
#     """

#     evidence = graph.query(evidence_query)

#     final_prompt = f"""
#         다음 Neo4j 조회 결과만 근거로 질문에 답하라.
#         근거 데이터에 없는 내용은 추측하지 말고 "근거 데이터에서 확인되지 않습니다"라고 답하라.

#         질문:
#         {question}

#         근거 데이터:
#         {evidence}

#         답변:
#         """

#     response = llm.invoke(final_prompt)

#     return {
#         "question": question,
#         "evidence": evidence,
#         "answer": response
#     }
def entire_graph_query():
    return graph.query("""
    MATCH (w:chaid__BuddhistPainting {uri: 'http://www.dh.aks.ac.kr/resource/CHAID/painting/CH000001'})

    OPTIONAL MATCH (w)-[:chaid__designationGrade]->(grade)
    OPTIONAL MATCH (w)-[:chaid__era]->(era)
    OPTIONAL MATCH (w)-[:chaid__classification]->(cls)
    OPTIONAL MATCH (w)-[:chaid__ceremonialVenue]->(venue)
    
    OPTIONAL MATCH (w)-[:chaid__hasInscriptionBlock]->(b:chaid__InscriptionBlock)
    WITH w, grade, era, cls, venue,
        collect(DISTINCT {
        uri: b.uri, name: b.rdfs__label,
        original: b.chaid__blockTextOriginal,
        translation: b.chaid__blockTextTranslation
        }) AS inscription_blocks

    OPTIONAL MATCH (w)-[:crm__P62_depicts]->(fig:chaid__IconographicFigure)
    OPTIONAL MATCH (fig)-[:chaid__hasAttribute]->(attr:crm__E55_Type)
    WITH w, grade, era, cls, venue, inscription_blocks, fig,
        collect(DISTINCT {uri: attr.uri, pref_labels: attr.skos__prefLabel,
                        child_note: attr.skos__editorialNote}) AS fig_attrs
    WITH w, grade, era, cls, venue, inscription_blocks,
        collect(DISTINCT {
        uri: fig.uri,
        pref_labels: fig.skos__prefLabel,
        alt_labels: fig.skos__altLabel,
        definition_scholarly: fig.skos__definition,
        child_note: fig.skos__editorialNote,
        attribute_text: fig.chaid__hasAttributeText,
        notation: fig.skos__notation,
        attributes: fig_attrs
        }) AS figures

    OPTIONAL MATCH (w)-[:chaid__hasContributor]->(p:chaid__HistoricalPerson)
    WITH w, grade, era, cls, venue, inscription_blocks, figures,
        collect(DISTINCT {
        uri: p.uri, label: p.rdfs__label,
        name_modern: p.foaf__name,
        name_original: p.chaid__nameOriginal,
        role_original: p.chaid__roleOriginal,
        role_modern: p.chaid__roleModern,
        entity_type: p.chaid__entityType,
        affiliation: p.chaid__affiliationText,
        member_count: p.chaid__memberCount
        }) AS contributors

    RETURN
    w.uri                          AS work_uri,
    w.rdfs__label                  AS work_label,
    w.chaid__yearCreated           AS year_created,
    w.chaid__yearExpression        AS year_expression,
    w.chaid__address               AS address,
    w.chaid__theme                 AS theme,
    w.chaid__composition           AS composition,
    w.chaid__materialDescription   AS material,
    w.chaid__totalHeightCm         AS total_height_cm,
    w.chaid__totalWidthCm          AS total_width_cm,
    w.chaid__canvasHeightCm        AS canvas_height_cm,
    w.chaid__canvasWidthCm         AS canvas_width_cm,
    w.chaid__mainFigureText        AS main_figure_text,
    w.chaid__attendantFiguresText  AS attendant_figures_text,
    w.chaid__otherFiguresText      AS other_figures_text,
    w.chaid__creationBackground    AS creation_background,
    w.chaid__significance          AS significance,

    grade.skos__prefLabel          AS designation_grade,
    era.skos__prefLabel            AS era_label,
    cls.skos__prefLabel            AS classification_label,
    venue.skos__prefLabel          AS ceremonial_venue,

    inscription_blocks,
    figures,
    contributors
    """)[0]

def entity_graph_query(entity_uri: str): # 특정 도상(예시: 미륵존불)의 상세 정보 조회 - 도상 자체의 속성 + 관련된 작품에서의 정보(조성배경, 핵심내용) + 도상의 속성(형식, 주제 등)
    rows = graph.query(
        """
        MATCH (e:chaid__IconographicFigure {uri: $ENTITY_URI})
        OPTIONAL MATCH (w:chaid__BuddhistPainting {uri: $CH_URI})
        OPTIONAL MATCH (e)<-[:chaid__isAttributeOf]-(attr:crm__E55_Type)

        RETURN
          e.uri AS entity_uri,
          e.skos__prefLabel AS pref_labels,
          e.skos__altLabel AS alt_labels,
          e.skos__definition AS definition_scholarly,
          e.skos__editorialNote AS child_note,
          e.chaid__hasAttributeText AS attribute_text,
          e.skos__notation AS notation,

          collect(DISTINCT {
            uri: attr.uri,
            pref_labels: attr.skos__prefLabel,
            alt_labels: attr.skos__altLabel,
            child_note: attr.skos__editorialNote
          }) AS attributes,

          w.chaid__creationBackground AS work_creation_background,
          w.chaid__significance AS work_significance
        """,
        params={
            "ENTITY_URI": entity_uri,
            "CH_URI": "http://www.dh.aks.ac.kr/resource/CHAID/painting/CH000001",
        },
    )

    return rows[0] if rows else {}
    
    
    
# def run_graph_query_select(question: str):
    route = router_chain_main.invoke({"question": question}).strip()
    print("선택된 route:", route)

    if "참여 인물" in route:
        return {
            "route": route,
            "data": graph.query("""
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
            """)
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
        

result = entire_graph_query() #전체 작품 조회

# ── 헬퍼 ──
def pick_lang(labels, lang):
    """n10s ARRAY '값@lang' → lang 일치 값 추출."""
    if not labels: return None
    for v in labels:
        if v.endswith(f"@{lang}"): return v.rsplit("@", 1)[0]
    return None

#수화승 : 철학
chief_painters = [
    pick_lang(p["name_modern"], "ko")
    for p in result["contributors"]
    if "수화승@ko" in (p.get("role_modern") or [])
]
chief_painter_text = ", ".join(chief_painters)

미륵존불 = entity_graph_query('http://www.dh.aks.ac.kr/ontologies/CHAID#E000002')
비로자나불 = entity_graph_query('http://www.dh.aks.ac.kr/ontologies/CHAID#E000004')
노사나불 = entity_graph_query('http://www.dh.aks.ac.kr/ontologies/CHAID#E000005')
대묘상보살 = entity_graph_query('http://www.dh.aks.ac.kr/ontologies/CHAID#E000010')
법림보살 = entity_graph_query('http://www.dh.aks.ac.kr/ontologies/CHAID#E000011')

class GraphQAIn(BaseModel):
    prompt: dict

@app.post("/api/graph-cypher-qa")
async def graph_cypher_qa(payload: GraphQAIn):
    model_name = "gemini-2.5-flash" # api 버전에 따라 모델명 변경 필요
    gemini = genai.GenerativeModel(model_name)
    
    try:
        prompt_obj = payload.prompt or {}

        role = prompt_obj.get("role")
        depth = prompt_obj.get("depth")
        detail = prompt_obj.get("detail")
        
        print("Received prompt:", prompt_obj)
        
        # 고정 질문과 + 그래프에서 조회한 참여 인물 데이터를 프롬프트에 넣어서 안내문 생성
        engineered_prompt = f"""
    {guidelines}
    ### [User Input Data]
    // 아래 내용을 채워서 명령을 실행한다.
    1. 기본 정보
    - {{대상 유산}}: {pick_lang(result["work_label"], "ko")}
    - {{분류}}: {pick_lang(result["work_label"], "ko")}
    - {{명칭_한글}}: {pick_lang(result["work_label"], "ko")}
    - {{명칭_한자}}: {pick_lang(result["work_label"], "ko-Hani")}
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
    - 국가유산 지정 등급: {pick_lang(result["designation_grade"], "ko")}
    - 제작연도_서기: {result["year_created"][0]}
    - 제작시기_연호: {pick_lang(result["year_expression"], "ko")}
    - 시대: {pick_lang(result["era_label"], "ko")}
    - 크기/재질: [세로 {result["total_height_cm"][0]}, 가로 {result["total_width_cm"][0]}/{pick_lang(result["material"], "ko")}
    - 출토/소장: {pick_lang(result["address"], "ko")}
    - 주제분류: {pick_lang(result["theme"], "ko")}
    - 형식_구도: {pick_lang(result["composition"], "ko")}
    - 주존불 {pick_lang(result["main_figure_text"], "ko")}
    - 주요협시 목록: {pick_lang(result["attendant_figures_text"], "ko")}]
    - 수화승: {chief_painter_text}
    - 참여 인물: {result["contributors"]}
    - 조성배경: {pick_lang(result["creation_background"], "ko")}
    - 핵심내용: {pick_lang(result["significance"], "ko")}

    (2) 시소러스 (Thesaurus & Glossary)
    // 전문 용어의 의미와 외국인용 번역 가이드
    DEFINE [Thesaurus: Term] AS "{pick_lang(미륵존불["pref_labels"], "ko")}"
    - 대표명_한국어: {pick_lang(미륵존불["pref_labels"], "ko")}
    - 대표명_영어: {pick_lang(미륵존불["pref_labels"], "en")}
    - 대표명_한자번체: {pick_lang(미륵존불["pref_labels"], "ko-Hani")}
    
    DEFINE [Thesaurus: Term] AS "{pick_lang(비로자나불["pref_labels"], "ko")}"
    - 대표명_한국어: {pick_lang(비로자나불["pref_labels"], "ko")}
    - 대표명_영어: {pick_lang(비로자나불["pref_labels"], "en")}
    - 대표명_한자번체: {pick_lang(비로자나불["pref_labels"], "ko-Hani")}

    DEFINE [Thesaurus: Term] AS "{pick_lang(노사나불["pref_labels"], "ko")}"
    - 대표명_한국어: {pick_lang(노사나불["pref_labels"], "ko")}
    - 대표명_영어: {pick_lang(노사나불["pref_labels"], "en")}
    - 대표명_한자번체: {pick_lang(노사나불["pref_labels"], "ko-Hani")}

    DEFINE [Thesaurus: Term] AS ] "{pick_lang(대묘상보살["pref_labels"], "ko")}" 
    - 대표명_한국어: {pick_lang(대묘상보살["pref_labels"], "ko")}
    - 대표명_영어: {pick_lang(대묘상보살["pref_labels"], "en")}
    - 대표명_한자번체: {pick_lang(대묘상보살["pref_labels"], "ko-Hani")}

    DEFINE [Thesaurus: Term] AS "{pick_lang(법림보살["pref_labels"], "ko")}"
    - 대표명_한국어: {pick_lang(법림보살["pref_labels"], "ko")}
    - 대표명_영어: {pick_lang(법림보살["pref_labels"], "en")}
    - 대표명_한자번체: {pick_lang(법림보살["pref_labels"], "ko-Hani")}
    
        (3) 모범 답안/참조 문안
        -다./이다.로 끝나는 문장으로 작성하라.
    ---
[EXECUTION COMMAND]
위 [User Input Data]를 로드하고, [SYSTEM] 로직을 가동하여 결과를 출력하라."""
    # print("엔지니어링된 프롬프트:", engineered_prompt) # 디버그용
        response = gemini.generate_content(engineered_prompt)
        # print(results)
        return {
            # "results": results,
            # "thesaurus_results": thesaurus_results,
            "role": role,
            "depth": depth,
            "detail": detail,
            "model": model_name,
            "text": response.text,
        }
        


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
from pydantic import BaseModel

class GraphQAIn(BaseModel):
    prompt: dict
    
    
@app.post("/api/select_prompt")
async def generate_prompt(payload: GraphQAIn):
    model_name = "gemini-2.5-flash" # api 버전에 따라 모델명 변경 필요
    gemini = genai.GenerativeModel(model_name)

    try:
        prompt_obj = payload.prompt or {}

        role = prompt_obj.get("role")
        depth = prompt_obj.get("depth")
        detail = prompt_obj.get("detail")
        
        print("도상, Received prompt:", prompt_obj)

        engineered_prompt = f"""### [User Input Data] (객체 설명용)
        1. 기본 정보
        - {{대상 유산}}: [장곡사 미륵불 괘불탱의 미륵존불] 
        // 전체 명칭이 아닌 설명하고자 하는 '세부 객체명'을 입력
        - {{상위 유산}}: [장곡사 미륵불 괘불탱]
        - {{관람객 국적}}: {role}
        - {{관람객 유형}}: {depth} 
        - {{안내문 유형}}: [세부_객체] 
        // [종합 | 권역 | 개별 | 세부_객체] 중 선택
        - {{목표 언어(선택)}}: {detail}

        2. {{문화유산 지식 데이터}} (Knowledge Base: 미륵존불)
        (1) 사실 정보 (대상 객체 중심)
        - 객체 위치: [화면 중앙에 거대하게 서 있음]
        - 도상 특징_지물: [오른손으로 연꽃 가지(용화수)를 들고 있음]
        - 도상 특징_복식: [부처임에도 불구하고 머리에 화려한 보관(보석관)을 쓰고 있음]
        - 수인(손모양): [변형된 항마촉지인 또는 설법인]
        - 일반적 정의: [석가모니불의 뒤를 이어 56억 7천만 년 후에 세상에 내려와 중생을 구제하는 미래의 부처]
        - 이 괘불만의 특징: [보통 미륵불은 의자에 앉아 있거나 서 있는 모습으로 나타나는데, 여기서는 영산회상도의 본존불처럼 묘사됨. 연꽃을 든 것은 용화회상을 상징함.]

        (2) 시소러스 (Thesaurus)
        - 미륵존불: Maitreya Buddha (The Future Buddha)
        - 용화수: Dragon Flower Tree (Symbol of Maitreya's enlightenment)

        3. [추가 제약 조건] (Constraint for Object Description)
        - **제약 1 (내용 구성):** '일반적 정의(미륵불이 누구인가)'로 시작하여, '이 괘불 속 미륵불의 시각적 특징(연꽃, 보관 등)'으로 이어지는 **2단 구성**을 따를 것.
        - **제약 2 (분량):** 관람객이 그림의 특정 부분을 보며 읽는 용도이므로, **2~3문장 내외(200자 이내)**로 핵심만 간결하게 작성할 것.
        - **제약 3 (어조):** 전체 유래보다는 **"그림 속 모습"을 묘사**하는 데 집중할 것."""

        response = gemini.generate_content(engineered_prompt)
        
        return {
            # "results": results,
            # "thesaurus_results": thesaurus_results,
            "role": role,
            "depth": depth,
            "detail": detail,
            "model": model_name,
            "text": response.text,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

