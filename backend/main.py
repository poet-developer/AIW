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
    auth=(NEO4J_USER, NEO4J_PASSWORD),
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
guidelines = load_prompt("services/prompts/system_prompt.md") # 20260615로 업데이트
people_guidelines = load_prompt("services/prompts/people_prompt.md")
item_guidelines = load_prompt("services/prompts/item_prompt.md")
hwagi_guidelines = load_prompt("services/prompts/hwagi_prompt.md")

CH_URI = "http://www.dh.aks.ac.kr/resource/CHAID/painting/CH000001" # 장곡사 미륵불 괘불탱 URI
ENTITY_URI_MAP = {
    "미륵존불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000002",
    "비로자나불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000004",
    "노사나불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000005",
    "대묘상보살": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000010",
    "법림보살": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000011",
}
SYMBOL_URI = "http://www.dh.aks.ac.kr/ontologies/CHAID#E000076" # 용화수 도상 URI

def get_basic_info():
    return graph.query("""MATCH (h) WHERE h.uri ENDS WITH 'CH000001'
OPTIONAL MATCH (h)-[:chaid__designationGrade]->(g)
OPTIONAL MATCH (h)-[:chaid__classification]->(c)
OPTIONAL MATCH (h)-[:chaid__era]->(era)
OPTIONAL MATCH (h)-[:chaid__hasRepository]->(repo)
RETURN h.rdfs__label              AS work_label,
       h.chaid__yearExpression    AS year_expression,
       h.chaid__yearCreated       AS year_created,
       coalesce(era.rdfs__label, era.skos__prefLabel)                                    AS period,
       coalesce(g.rdfs__label, g.skos__prefLabel, split(g.uri,'/grade/')[1])             AS designation_grade,
       h.chaid__totalHeightCm     AS total_height_cm,   
       h.chaid__totalWidthCm      AS total_width_cm,    
       h.chaid__canvasHeightCm    AS canvas_height_cm,  
       h.chaid__canvasWidthCm     AS canvas_width_cm,   
       h.chaid__materialDescription AS material,
       coalesce(c.rdfs__label, c.skos__prefLabel, split(c.uri,'/classification/')[1])    AS classification,
       h.chaid__theme             AS theme,             
       coalesce(repo.rdfs__label, repo.skos__prefLabel)                                  AS repository,
       h.chaid__address           AS address;            
""")

def entire_graph_query():
    return graph.query("""
    MATCH (w:chaid__BuddhistPainting {uri: $CH_URI})
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
    w.uri AS work_uri, w.rdfs__label AS work_label,
    w.chaid__yearCreated AS year_created, w.chaid__yearExpression AS year_expression,
    w.chaid__address AS address, w.chaid__theme AS theme,
    w.chaid__composition AS composition, w.chaid__materialDescription AS material,
    w.chaid__totalHeightCm AS total_height_cm, w.chaid__totalWidthCm AS total_width_cm,
    w.chaid__canvasHeightCm AS canvas_height_cm, w.chaid__canvasWidthCm AS canvas_width_cm,
    w.chaid__mainFigureText AS main_figure_text,
    w.chaid__attendantFiguresText AS attendant_figures_text,
    w.chaid__otherFiguresText AS other_figures_text,
    w.chaid__creationBackground AS creation_background,
    w.chaid__significance AS significance,
    grade.skos__prefLabel AS designation_grade,
    era.skos__prefLabel AS era_label,
    cls.skos__prefLabel AS classification_label,
    venue.skos__prefLabel AS ceremonial_venue,
    inscription_blocks, figures, contributors
    """,
    params={
            "CH_URI": CH_URI,
        },
    )[0]

def entity_graph_query(entity_uri: str): # 특정 도상(예시: 미륵존불)의 상세 정보 조회 - 도상 자체의 속성 + 관련된 작품에서의 정보(조성배경, 핵심내용) + 도상의 속성(형식, 주제 등)
    rows = graph.query(
        """
MATCH (e:chaid__IconographicFigure {uri: $ENTITY_URI})
OPTIONAL MATCH (w:chaid__BuddhistPainting {uri: $CH_URI})
OPTIONAL MATCH (w)-[:chaid__hasPlacement]->(plc:crm__E13_Attribute_Assignment)-[:crm__P141_assigned]->(e)

CALL (e) {
  OPTIONAL MATCH (e)<-[:chaid__isAttributeOf]-(attr:crm__E55_Type)
  WHERE attr IS NOT NULL
  RETURN collect(DISTINCT {
    uri: attr.uri,
    pref_labels: attr.skos__prefLabel,
    alt_labels: attr.skos__altLabel,
    child_note: attr.skos__editorialNote
  }) AS attributes
}

CALL (plc) {
  OPTIONAL MATCH (plc)-[:crm__P2_has_type]->(pos)
  WHERE pos IS NOT NULL AND pos.uri CONTAINS '/canvasPosition/'
  RETURN collect(DISTINCT pos.skos__prefLabel) AS position_labels
}

CALL (plc) {
  OPTIONAL MATCH (plc)-[:crm__P2_has_type]->(mudra)
  WHERE mudra IS NOT NULL AND mudra.uri CONTAINS '/mudra/'
  RETURN collect(DISTINCT mudra.skos__prefLabel) AS mudra_labels
}

CALL (plc) {
  OPTIONAL MATCH (plc)-[:crm__P2_has_type]->(item)
  WHERE item IS NOT NULL AND item.uri CONTAINS '/attribute/'
  RETURN collect(DISTINCT item.skos__prefLabel) AS attribute_concept_labels
}

RETURN
  e.uri AS entity_uri,
  COALESCE(e.skos__prefLabel, []) AS pref_labels,
  COALESCE(e.skos__altLabel, []) AS alt_labels,
  COALESCE(e.skos__definition, []) AS definition_scholarly,
  COALESCE(e.skos__editorialNote, []) AS child_note,
  COALESCE(e.chaid__hasAttributeText, []) AS attribute_text,
  COALESCE(e.skos__notation, []) AS notation,
  COALESCE(attributes, []) AS attributes,
  COALESCE(plc.rdfs__comment, "") AS detail_feature,
  COALESCE(plc.chaid__iconographicCategory, "") AS iconographic_category,
  COALESCE(plc.chaid__iconographicRole, "") AS iconographic_role,
  COALESCE(position_labels, []) AS position_labels,
  COALESCE(mudra_labels, []) AS mudra_labels,
  COALESCE(attribute_concept_labels, []) AS attribute_concept_labels,
  COALESCE(w.chaid__creationBackground, "") AS work_creation_background,
  COALESCE(w.chaid__significance, "") AS work_significance
        """,
        params={
            "ENTITY_URI": entity_uri,
            "CH_URI": CH_URI,
        },
    )

    return rows[0] if rows else {}

def get_hwagi_entity():
    rows = graph.query(
        """
        MATCH (w:chaid__BuddhistPainting {uri: $CH_URI})-[:chaid__hasInscriptionBlock]->(b:chaid__InscriptionBlock)
        WITH w, collect({
        uri: b.uri,
        name: b.rdfs__label,
        original: b.chaid__blockTextOriginal,
        translation: b.chaid__blockTextTranslation
        }) AS blocks
        RETURN
        blocks AS inscription_blocks,
        w.chaid__creationBackground AS work_creation_background,
        w.chaid__significance AS work_significance
        """,
        params={
            "CH_URI": CH_URI,
        },
    )

    return rows[0] if rows else {}

def get_symbol_entity():
    rows = graph.query(
        """
        MATCH (e:crm__E55_Type {uri: $SYMBOL_URI})
        OPTIONAL MATCH (w:chaid__BuddhistPainting {uri: $CH_URI})
        OPTIONAL MATCH (e)-[:chaid__isAttributeOf]->(fig:chaid__IconographicFigure)
        WITH e, w, collect(DISTINCT {uri: fig.uri, pref_labels: fig.skos__prefLabel}) AS host_figures
        RETURN
        e.uri AS entity_uri,
        e.skos__prefLabel AS pref_labels,
        e.skos__altLabel AS alt_labels,
        e.skos__definition AS definition_scholarly,
        e.skos__editorialNote AS child_note,
        e.skos__notation AS notation,
        host_figures,
        w.chaid__creationBackground AS work_creation_background,
        w.chaid__significance AS work_significance
        """,
        params={
            "CH_URI": CH_URI,
            "SYMBOL_URI": SYMBOL_URI
        },
    )

    return rows[0] if rows else {} # 용화수는 두 개의 URI가 있어서 리스트로 반환하도록 함 [0]은 연꽃가지 [1] 용화가지

def get_thesaurus_entity():
    rows = graph.query(
        """
        MATCH (w:chaid__BuddhistPainting {uri: $CH_URI})-[:crm__P62_depicts]->(fig:chaid__IconographicFigure)
        RETURN
        fig.uri AS entity_uri,
        fig.skos__prefLabel AS pref_labels,
        fig.skos__altLabel AS alt_labels,
        fig.skos__definition AS definition_scholarly,
        fig.skos__editorialNote AS child_note,
        fig.skos__notation AS notation,
        fig.chaid__hasAttributeText AS attribute_text
        ORDER BY fig.uri
        """,
        params={
            "CH_URI": CH_URI,
        },
    )

    return rows

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
        

# ── 헬퍼 ──
def pick_lang(labels, lang):
    """n10s ARRAY '값@lang' → lang 일치 값 추출."""
    if not labels: return None
    for v in labels:
        if v.endswith(f"@{lang}"): return v.rsplit("@", 1)[0]
    return None

#수화승 : 철학
# chief_painters = [
#     pick_lang(p["name_modern"], "ko")
#     for p in result["contributors"]
#     if "수화승@ko" in (p.get("role_modern") or [])
# ]
# chief_painter_text = ", ".join(chief_painters)
basic_info = get_basic_info() # 작품의 기본 정보 조회
result = entire_graph_query() #전체 작품 조회
hwagi = get_hwagi_entity() # 화기 정보 조회

미륵존불 = entity_graph_query(ENTITY_URI_MAP["미륵존불"])
비로자나불 = entity_graph_query(ENTITY_URI_MAP["비로자나불"])
노사나불 = entity_graph_query(ENTITY_URI_MAP["노사나불"])
대묘상보살 = entity_graph_query(ENTITY_URI_MAP["대묘상보살"])
법림보살 = entity_graph_query(ENTITY_URI_MAP["법림보살"])

용화수 = get_symbol_entity() # 용화수 도상 정보 조회
시소러스 = get_thesaurus_entity() # 도상 시소러스 정보 조회 (전체 작품에서 묘사된 도상들의 라벨·정의 등)
print("기본정보조회",basic_info) # 작품의 기본 정보 디버그용
# print("전체 작품 정보:", result) # 디버그용
# print("화기 정보:", hwagi) # 디버그용
# print("용화수 도상 정보:", 용화수) # 디버그용
# # print("미륵존불 도상 정보:", 미륵존불) # 디버그용
# print("비로자나불 도상 정보:", 비로자나불) # 디버그용
# print("노사나불 도상 정보:", 노사나불) # 디버그용
# print("대묘상보살 도상 정보:", 대묘상보살) # 디버그용

def extract_work_summary(result): # 작품의 주요 정보를 추출하여 안내문 생성에 활용할 수 있는 형태로 가공하는 헬퍼 함수
    contributors = result.get("contributors", [])
    figures = result.get("figures", [])

    def pick_lang(values, lang="ko"):
        if not values:
            return ""

        if isinstance(values, str):
            values = [values]

        for v in values:
            if isinstance(v, str) and v.endswith(f"@{lang}"):
                return v.replace(f"@{lang}", "")

        return values[0].split("@")[0] if isinstance(values[0], str) else values[0]

    main_figure_name = ""
    if result.get("main_figure_text"):
        main_figure_name = pick_lang(result["main_figure_text"], "ko")

    main_figure_attribute = {}

    for fig in figures:
        labels = fig.get("pref_labels", [])

        if any(main_figure_name in label for label in labels):
            main_figure_attribute = {
                "ko": pick_lang(fig.get("attribute_text", []), "ko"),
                "en": pick_lang(fig.get("attribute_text", []), "en"),
                "ko-Hani": pick_lang(fig.get("attribute_text", []), "ko-Hani"),
                "raw": fig.get("attribute_text", []),
                "attributes": fig.get("attributes", [])
            }
            break

    def filter_contributors(keyword_list):
        filtered = []

        for c in contributors:
            role_modern = pick_lang(c.get("role_modern", []), "ko")

            if any(k in role_modern for k in keyword_list):
                filtered.append({
                    "name_ko": pick_lang(c.get("name_modern", []), "ko"),
                    "name_hani": pick_lang(c.get("name_original", []), "ko-Hani"),
                    "role_ko": pick_lang(c.get("role_modern", []), "ko"),
                    "role_hani": pick_lang(c.get("role_original", []), "ko-Hani"),
                    "affiliation_ko": pick_lang(c.get("affiliation", []), "ko"),
                    "uri": c.get("uri", "")
                })

        return filtered

    summary = {
        "형식·구도": {
            "ko": pick_lang(result.get("composition", []), "ko"),
            "raw": result.get("composition", [])
        },
        "의식장소": {
            "ko": pick_lang(result.get("ceremonial_venue", []), "ko"),
            "ko-Hani": pick_lang(result.get("ceremonial_venue", []), "ko-Hani"),
            "raw": result.get("ceremonial_venue", [])
        },
        "본존(주존불)": {
            "ko": pick_lang(result.get("main_figure_text", []), "ko"),
            "ko-Hani": pick_lang(result.get("main_figure_text", []), "ko-Hani"),
            "en": pick_lang(result.get("main_figure_text", []), "en"),
            "raw": result.get("main_figure_text", [])
        },
        "주요 협시": {
            "ko": pick_lang(result.get("attendant_figures_text", []), "ko"),
            "raw": result.get("attendant_figures_text", [])
        },
        "기타 권속": {
            "ko": pick_lang(result.get("other_figures_text", []), "ko"),
            "raw": result.get("other_figures_text", [])
        },
        "본존 지물(hasAttribute, v2.5)": main_figure_attribute,
        "도상 총 수": len(figures),
        "수화승(painter)": filter_contributors(["수화승"]),
        "참여 화승": filter_contributors(["참여화승"]),
        "사찰 소임(temple_role)": filter_contributors([
            "증명", "지전", "공양주", "대화주", "산인", "삼보"
        ]),
        "시주자(sponsor)": filter_contributors([
            "시주", "보시"
        ])
    }

    return summary
def convert_thesaurus_item(item):

    return {
        "entity_uri": item.get("entity_uri", ""),

        "name_ko": pick_lang(item.get("pref_labels", []), "ko"),
        "name_hani": pick_lang(item.get("pref_labels", []), "ko-Hani"),
        "name_en": pick_lang(item.get("pref_labels", []), "en"),

        "alt_ko": [
            pick_lang([x], "ko")
            for x in (item.get("alt_labels") or [])
            if "@ko" in x
        ],

        "definition_ko": pick_lang(
            item.get("definition_scholarly", []),
            "ko"
        ),

        "child_note_ko": pick_lang(
            item.get("child_note", []),
            "ko"
        ),

        "attribute_ko": pick_lang(
            item.get("attribute_text", []),
            "ko"
        ),

        "notation": item.get("notation", [""])[0]
    }
work_summary = extract_work_summary(result)
converted_thesaurus = [convert_thesaurus_item(x) for x in 시소러스]
# print("시소로스", 시소러스) # 도상 시소러스 정보 디버그용
# print(hwagi["work_creation_background"])
# print(hwagi["work_significance"])


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

        # 고정 질문과 + 그래프에서 조회한 참여 인물 데이터를 프롬프트에 넣어서 안내문 생성
        engineered_prompt = f"""{guidelines}
  
    [User Input Data]
    
    1. 기본 정보 및 매트릭스 파라미터
    - 대상 유산: [장곡사 미륵불 괘불탱]    
    - 관람객 국적: [{role}]
    - 관람객 유형: [{depth}]
    - 목표 언어: [{detail}]    

    2. 문화유산 지식 데이터 (Knowledge Base)

    (1) 작품 사실 정보 (A 공통, prefix: KHP)
    {basic_info}                          

    (2) 도상 시소러스 블록 (prefix: KHP/DDB/DD 등)
    {converted_thesaurus}

    (3) 유형별 항목 (B 영역 — 회화 기준)
    - 형식·구도: [{work_summary["형식·구도"]["ko"]}]
    - 의식장소: [{work_summary["의식장소"]["ko"]}]
    - 본존(주존불): [{work_summary["본존(주존불)"]["ko"]}]
    - 주요 협시: [{work_summary["주요 협시"]["ko"]}]
    - 기타 권속: [{work_summary["기타 권속"]["ko"]}]
    - 본존 지물(hasAttribute, v2.5): [{work_summary["본존 지물(hasAttribute, v2.5)"]}]
    - 도상 총 수: {work_summary["도상 총 수"]}구
    - 수화승(painter): {work_summary["수화승(painter)"]}
    - 참여 화승: {work_summary["참여 화승"]}
    - 사찰 소임(temple_role): {work_summary["사찰 소임(temple_role)"]}
    - 시주자(sponsor): {work_summary["시주자(sponsor)"]}

    (4) 텍스트 원문 기록 (B 영역 — 회화=화기, prefix: Hwagi 등)
    {hwagi['inscription_blocks']}

    (5) 작품 해석 메타 (C 공통, R5 핵심, prefix: KHP)
    - 작품 화기 해석 (creation_background): "{hwagi['work_creation_background']}"
    - 작품 학술 평가 (significance): "{hwagi['work_significance']}"

    (6) 모범 답안/참조 문안
    -다./이다.로 끝나는 문장으로 작성하라.
"""
    
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
        
        # lang = "ko" if role == "내국인" else "en"

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
            selected_icon = get_symbol_entity()
        elif label == '화기':
            selected_icon = get_hwagi_entity()
        else:
            raise HTTPException(status_code=400, detail="Invalid label value")
        
        if label in ['1', '2', '3', '8', '9']:
            
            engineered_prompt = f"""{people_guidelines}
            
            # [User Input Data]
            1. 기본 정보 및 매트릭스 파라미터
            - 대상 유산: [장곡사 미륵불 괘불탱]
            - 관람객 국적: [{role}]
            - 관람객 유형: [{depth}]
            - 목표 언어: [{detail}]

            2. 문화유산 검증 지식 베이스
            (1) 작품 사실 정보 (A 공통, prefix: KHP)
            {basic_info} 
            (2) 도상 시소러스 fact (prefix: WL/DDB/DD 등)
            - 도상 URI 및 명칭: [{selected_icon['entity_uri']}] / @ko=[{pick_lang(selected_icon['pref_labels'],"ko")}]/ @ko-Hani=[{pick_lang(selected_icon['pref_labels'],"ko-Hani")}]/ @en=[{pick_lang(selected_icon['pref_labels'],"en")}]/ @zh-Hans=[{pick_lang(selected_icon['pref_labels'],"zh-Hans")}]/ @ja=[{pick_lang(selected_icon['pref_labels'],"ja")}]
            - 학술 정의 및 어린이용 풀이: "{selected_icon['definition_scholarly']}" / "{selected_icon['child_note']}"
            - 도상 분류 및 역할: "{selected_icon['iconographic_category']}" / "{selected_icon['iconographic_role']}"
            (3) 본 작품 내 placement fact (prefix: KHP)
            - 작품 한정 위치 및 수인: "{selected_icon['position_labels']}" / "{selected_icon['mudra_labels']}"
            - 작품 한정 지물 및 상세 묘사: "{selected_icon['attribute_concept_labels']}" / "{selected_icon['attribute_text']}" / "{selected_icon['detail_feature']}"
            (4) 작품 해석 메타 (C 공통, prefix: KHP)
            - 작품 화기 해석 (work_creation_background): "{hwagi["work_creation_background"]}"
            - 작품 학술 평가 (work_significance): "{hwagi["work_significance"]}"
            """

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
        elif label in ['용화수']:
            engineered_prompt = f"""{item_guidelines}
            # [User Input Data]
            1. 기본 정보 및 매트릭스 파라미터
            - 대상 유산: [장곡사 미륵불 괘불탱]
            - 관람객 국적: [{role}]
            - 관람객 유형: [{depth}]
            - 목표 언어: [{detail}]

            2. 문화유산 검증 지식 베이스
            (1) 작품 사실 정보 (A 공통, prefix: KHP)
            {basic_info}
            (2) 지물 시소러스 fact (prefix: WL/DDB/DD 등)
            - 지물 URI 및 명칭: [{selected_icon['entity_uri']}] / @ko=[{pick_lang(selected_icon['pref_labels'],"ko")}]/ @ko-Hani=[{pick_lang(selected_icon['pref_labels'],"ko-Hani")}]/ @en=[{pick_lang(selected_icon['pref_labels'],"en")}]/ @zh-Hans=[{pick_lang(selected_icon['pref_labels'],"zh-Hans")}]/ @ja=[{pick_lang(selected_icon['pref_labels'],"ja")}]
            - 학술 정의 및 어린이용 풀이: "{selected_icon['definition_scholarly']}" / "{selected_icon['child_note']}"
            (3) host 도상 정보 (prefix: KHP)
            - 이 지물을 든 도상 (host_figures): {entity_graph_query(ENTITY_URI_MAP["미륵존불"])}
            (4) 작품 해석 메타 (C 공통, prefix: KHP)
            - 작품 화기 해석 (work_creation_background): "{hwagi["work_creation_background"]}"
            - 작품 학술 평가 (work_significance): "{hwagi["work_significance"]}"
            """

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
        elif label in ['화기']:
            engineered_prompt = f"""{hwagi_guidelines}
            # [User Input Data]
            1. 기본 정보 및 매트릭스 파라미터
            - 대상 유산: [장곡사 미륵불 괘불탱]
            - 관람객 국적: [{role}]
            - 관람객 유형: [{depth}]
            - 목표 언어: [{detail}

            2. 문화유산 검증 지식 베이스
            (1) 작품 사실 정보 (A 공통, prefix: KHP)
            {basic_info}
            (2) 텍스트 기록 블록 (prefix: Hwagi 등)
            {selected_icon['inscription_blocks']}
            // 백엔드가 선택 블록(단일 또는 5블록 통합)의 블록명·원문·번역 묶음을 자연어로 빌드하여 동적 주입
            (3) 작품 해석 메타 (C 공통, R5 핵심, prefix: KHP)
            - 작품 화기 해석 (creation_background): "{hwagi["work_creation_background"]}"
            * 핵심 키워드 감지 필수: [관용적 축원 문구 / 특정 조성 목적 / 회향문 및 발원]
            - 작품 학술 평가 (significance): "{hwagi["work_significance"]}"
            """

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

