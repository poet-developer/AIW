import pandas as pd
from neo4j import GraphDatabase

# ── 설정 (본인 환경에 맞게 수정) ────────────────────────
URI      = "bolt://localhost:7687"  # Neo4j URI (Bolt 프로토콜)
USER     = "neo4j"
PASSWORD = "janggoksa1234"          # STEP 1에서 설정한 비밀번호
CSV_DIR  = "../db"   # CSV 파일이 있는 폴더
# ────────────────────────────────────────────────────────

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# 연결 테스트
with driver.session() as s:
    result = s.run("RETURN 1 AS test")
    print("✅ Neo4j 연결 성공:", result.single()["test"])

# CSV 로드
meta    = pd.read_csv(f"{CSV_DIR}/janggoksa_metadata.csv").fillna("")
persons = pd.read_csv(f"{CSV_DIR}/janggoksa_persons.csv").fillna("")
icons   = pd.read_csv(f"{CSV_DIR}/janggoksa_icons.csv").fillna("")
rels    = pd.read_csv(f"{CSV_DIR}/janggoksa_relations.csv").fillna("")

# ── 1) 불화 노드 ─────────────────────────────────────
print("\n1/4 불화(Artwork) 노드 적재...")
with driver.session() as s:
    for _, r in meta.iterrows():
        s.run("""
            MERGE (a:Artwork {ch_id: $ch_id})
            SET a.name_ko     = $name_ko,
                a.name_hanja  = $name_hj,
                a.location    = $location,
                a.grade       = $grade,
                a.era         = $era,
                a.year        = $year,
                a.material    = $material,
                a.subject     = $subject,
                a.main_buddha = $main_buddha
        """,
        ch_id       = str(r["CH_ID/PK"]),
        name_ko     = str(r["명칭_한글"]),
        name_hj     = str(r["명칭_한자"]),
        location    = str(r["소장처/소재지"]),
        grade       = str(r["국가유산_지정등급"]),
        era         = str(r["시대"]),
        year        = str(r["제작연도_절대연도"]),
        material    = str(r["재질"]),
        subject     = str(r["주제"]),
        main_buddha = str(r["주존불"]),
        )
print("  ✅ 완료")

# ── 2) 인물 노드 ─────────────────────────────────────
print("2/4 인물(Person) 노드 적재...")
with driver.session() as s:
    for _, r in persons.iterrows():
        s.run("""
            MERGE (p:Person {person_id: $pid})
            SET p.name_orig   = $name_orig,
                p.name_modern = $name_modern,
                p.category    = $category,
                p.role_orig   = $role_orig,
                p.role_modern = $role_modern,
                p.rank        = $rank,
                p.affiliation = $affil,
                p.ch_id       = $ch_id
        """,
        pid         = str(r["Person_Data_ID/PK"]),
        name_orig   = str(r["인물명_원문"]),
        name_modern = str(r["인물명_현대어"]),
        category    = str(r["대분류"]),
        role_orig   = str(r["역할_원문"]),
        role_modern = str(r["역할_현대어"]),
        rank        = str(r["신분/품계"]),
        affil       = str(r["소속/본관"]),
        ch_id       = str(r["CH_ID/FK"]),
        )
print("  ✅ 완료")

# ── 3) 도상 노드 ─────────────────────────────────────
print("3/4 도상(Icon) 노드 적재...")
with driver.session() as s:
    for _, r in icons.iterrows():
        s.run("""
            MERGE (i:Icon {icon_id: $icon_id})
            SET i.name       = $name,
                i.category   = $cat,
                i.role       = $role,
                i.position   = $pos,
                i.mudra      = $mudra,
                i.attribute  = $attr,
                i.entity_id  = $eid,
                i.ch_id      = $ch_id
        """,
        icon_id = str(r["Icon_Data_ID/PK"]),
        name    = str(r["도상명"]),
        cat     = str(r["도상_분류"]),
        role    = str(r["역할"]),
        pos     = str(r["위치"]),
        mudra   = str(r["수인"]),
        attr    = str(r["지물"]),
        eid     = str(r["Entity_ID/FK"]),
        ch_id   = str(r["CH_ID/FK"]),
        )
print("  ✅ 완료")

# ── 4) 관계 엣지 ─────────────────────────────────────
print("4/4 관계(Relation) 적재...")
with driver.session() as s:
    for _, r in rels.iterrows():
        src  = str(r["Source_ID (누가)"])
        tgt  = str(r["Target_ID (무엇을/어디에)"])
        rel  = str(r["Relation (어떻게)"]).upper().replace(" ", "_").replace("-", "_")
        note = str(r["비고"])

        # Person → Artwork 관계
        if src.startswith("PD_") and tgt.startswith("CH"):
            s.run(f"""
                MATCH (p:Person {{person_id: $src}})
                MATCH (a:Artwork {{ch_id: $tgt}})
                MERGE (p)-[r:{rel}]->(a)
                SET r.note = $note
            """, src=src, tgt=tgt, note=note)

        # Icon → Artwork 관계
        elif src.startswith("IC_") and tgt.startswith("CH"):
            s.run(f"""
                MATCH (i:Icon {{icon_id: $src}})
                MATCH (a:Artwork {{ch_id: $tgt}})
                MERGE (i)-[r:{rel}]->(a)
                SET r.note = $note
            """, src=src, tgt=tgt, note=note)

# Icon → Artwork APPEARS_IN 자동 연결
with driver.session() as s:
    s.run("""
        MATCH (i:Icon), (a:Artwork)
        WHERE i.ch_id = a.ch_id
        MERGE (i)-[:APPEARS_IN]->(a)
    """)

# Person → Artwork BELONGS_TO 자동 연결
with driver.session() as s:
    s.run("""
        MATCH (p:Person), (a:Artwork)
        WHERE p.ch_id = a.ch_id
        MERGE (p)-[:BELONGS_TO]->(a)
    """)

print("  ✅ 완료")
print("\n🎉 전체 적재 완료!")
driver.close()