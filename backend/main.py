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

# 시스템 프롬프트 로드 - 안내문 생성 시 활용되는 고정
guidelines = load_prompt("services/prompts/system_prompt.md") # 20260317 로 업데이트 # 줄일 필요 또는 고정하던지해야 성능 떨어짐.

ENTITY_URI_MAP = {
    "미륵존불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000002",
    "비로자나불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000004",
    "노사나불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000005",
    "대묘상보살": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000010",
    "법림보살": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000011",
}

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

def get_iconographic_entity(entity_uri: str):
    rows = graph.query(
        """
        MATCH (e:chaid__IconographicFigure {uri: $ENTITY_URI})
        OPTIONAL MATCH (w:chaid__BuddhistPainting {uri: $CH_URI})
        OPTIONAL MATCH (e)<-[:chaid__isAttributeOf]-(attr:crm__E55_Type)

        RETURN
          e.skos__prefLabel AS pref_labels,
          e.skos__altLabel AS alt_labels,
          e.skos__definition AS definition_scholarly,
          e.skos__editorialNote AS child_note,
          e.chaid__hasAttributeText AS attribute_text,
          collect(DISTINCT {
            uri: attr.uri,
            pref_labels: attr.skos__prefLabel,
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

def get_flower_entity():
    rows = graph.query(
        """
        MATCH (e:crm__E55_Type)
        WHERE e.uri IN [
        "http://www.dh.aks.ac.kr/ontologies/CHAID#E000075",
        "http://www.dh.aks.ac.kr/ontologies/CHAID#E000076"
        ]
        OPTIONAL MATCH (w:chaid__BuddhistPainting {uri: $CH_URI})
        OPTIONAL MATCH (e)-[:chaid__isAttributeOf]->(fig:chaid__IconographicFigure)

        WITH e, w,
             collect(DISTINCT {
                uri: fig.uri,
                pref_labels: fig.skos__prefLabel
             }) AS host_figures

        RETURN
          e.uri AS entity_uri,
          e.skos__prefLabel AS pref_labels,
          e.skos__altLabel AS alt_labels,
          e.skos__definition AS definition_scholarly,
          e.skos__editorialNote AS child_note,
          e.skos__notation AS notation,
          host_figures AS host_figures,
          w.chaid__creationBackground AS work_creation_background,
          w.chaid__significance AS work_significance

        ORDER BY e.uri
        """,
        params={
            "CH_URI": "http://www.dh.aks.ac.kr/resource/CHAID/painting/CH000001",
        },
    )

    return rows if rows else {} # 용화수는 두 개의 URI가 있어서 리스트로 반환하도록 함 [0]은 연꽃가지 [1] 용화가지

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

미륵존불 = entity_graph_query(ENTITY_URI_MAP["미륵존불"])
비로자나불 = entity_graph_query(ENTITY_URI_MAP["비로자나불"])
노사나불 = entity_graph_query(ENTITY_URI_MAP["노사나불"])
대묘상보살 = entity_graph_query(ENTITY_URI_MAP["대묘상보살"])
법림보살 = entity_graph_query(ENTITY_URI_MAP["법림보살"])

용화수 = get_flower_entity() # 용화수 도상 정보 조회

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

        lang = "ko" if role == "내국인" else "en"

        # 고정 질문과 + 그래프에서 조회한 참여 인물 데이터를 프롬프트에 넣어서 안내문 생성
        engineered_prompt = f"""
    {guidelines}
    ### [User Input Data]
    // 아래 내용을 채워서 명령을 실행한다.
    1. 기본 정보
    - {{대상 유산}}: {pick_lang(result["work_label"], lang)}
    - {{분류}}: {pick_lang(result["work_label"], lang)}
    - {{명칭_한글}}: {pick_lang(result["work_label"], lang)}
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
    - 국가유산 지정 등급: {pick_lang(result["designation_grade"], lang)}
    - 제작연도_서기: {result["year_created"][0]}
    - 제작시기_연호: {pick_lang(result["year_expression"], lang)}
    - 시대: {pick_lang(result["era_label"], lang)}
    - 크기/재질: [세로 {result["total_height_cm"][0]}, 가로 {result["total_width_cm"][0]}/{pick_lang(result["material"], lang)}
    - 출토/소장: {pick_lang(result["address"], lang)}
    - 주제분류: {pick_lang(result["theme"], lang)}
    - 형식_구도: {pick_lang(result["composition"], lang)}
    - 주존불: {pick_lang(result["main_figure_text"], lang)}
    - 주요협시 목록: {pick_lang(result["attendant_figures_text"], lang)}
    - 수화승: {chief_painter_text}
    - 참여 인물: {result["contributors"]}
    - 조성배경: {pick_lang(result["creation_background"], lang)}
    - 핵심내용: {pick_lang(result["significance"], lang)}

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
        label = prompt_obj.get("label")
        
        lang = "ko" if role == "내국인" else "en"
        
        print("Received prompt:", role) # 디버그용

        if label ==  '1':   
            selected_icon = entity_graph_query(ENTITY_URI_MAP["미륵존불"])
        elif label == '2':
            selected_icon = entity_graph_query(ENTITY_URI_MAP["노사나불"])
        elif label == '3':
            selected_icon = entity_graph_query(ENTITY_URI_MAP["비로자나불"])
        elif label == '8':
            selected_icon = entity_graph_query(ENTITY_URI_MAP["대묘상보살"])
        elif label == '9':
            selected_icon = entity_graph_query(ENTITY_URI_MAP["법림보살"])
        elif label == '용화수':
            selected_icon = get_flower_entity()
        else:
            raise HTTPException(status_code=400, detail="Invalid label value")
        
        print("Selected iconographic entity:", selected_icon) # 디버그용

        engineered_prompt = f"""
        {guidelines}
        ### [User Input Data] (객체 설명용)
        1. 기본 정보
        - {{대상 유산}}: [장곡사 미륵불 괘불탱의 {pick_lang(selected_icon["pref_labels"], lang)}]
        - {{상위 유산}}: [장곡사 미륵불 괘불탱]
        - {{관람객 국적}}: {role}
        - {{관람객 유형}}: {depth} 
        - {{안내문 유형}}: [세부_객체] 
        // [종합 | 권역 | 개별 | 세부_객체] 중 선택
        - {{목표 언어(선택)}}: {detail}

        2. {{문화유산 지식 데이터}} (Knowledge Base: 미륵존불)
        (1) 사실 정보 (대상 객체 중심)
        {selected_icon}
        
        (2) 시소러스 (Thesaurus)
        DEFINE [Thesaurus: Term] AS ] "{pick_lang(selected_icon["pref_labels"], "ko")}" 
        - 대표명_한국어: {pick_lang(selected_icon["pref_labels"], "ko")}
        - 대표명_영어: {pick_lang(selected_icon["pref_labels"], "en")}
        - 대표명_한자번체: {pick_lang(selected_icon["pref_labels"], "ko-Hani")}

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

