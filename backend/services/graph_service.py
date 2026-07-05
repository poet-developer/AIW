
import os
from neo4j import GraphDatabase
from langchain_neo4j import Neo4jGraph

# --- Constants ---
CH_URI = "http://www.dh.aks.ac.kr/resource/CHAID/painting/CH000001" # 장곡사 미륵불 괘불탱 URI
ENTITY_URI_MAP = {
    "미륵존불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000002",
    "비로자나불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000004",
    "노사나불": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000005",
    "대묘상보살": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000010",
    "법림보살": "http://www.dh.aks.ac.kr/ontologies/CHAID#E000011",
}
SYMBOL_URI = "http://www.dh.aks.ac.kr/ontologies/CHAID#E000076" # 용화수 도상 URI

# --- Neo4j Connection ---
def get_neo4j_driver():
    """Establishes connection to Neo4j and returns a driver object."""
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "janggoksa1234")
    
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def get_neo4j_graph():
    """Initializes and returns a Neo4jGraph object."""
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "janggoksa1234")
    NEO4J_DB = os.getenv("NEO4J_DB", "neo4j")

    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DB,
    )
    graph.refresh_schema()
    return graph

# --- Cypher Queries ---
def get_basic_info(graph: Neo4jGraph):
    return graph.query("""
        MATCH (h) WHERE h.uri ENDS WITH 'CH000001'
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

def entire_graph_query(graph: Neo4jGraph):
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
    params={"CH_URI": CH_URI})[0]

def entity_graph_query(graph: Neo4jGraph, entity_uri: str):
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

def get_hwagi_entity(graph: Neo4jGraph):
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
        params={"CH_URI": CH_URI},
    )
    return rows[0] if rows else {}

def get_symbol_entity(graph: Neo4jGraph):
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
    return rows[0] if rows else {}

def get_thesaurus_entity(graph: Neo4jGraph):
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
        params={"CH_URI": CH_URI},
    )
    return rows
