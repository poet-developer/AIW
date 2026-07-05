
from .load_prompt import load_prompt
from .data_service import pick_lang

# Load guideline prompts
guidelines = load_prompt("services/prompts/system_prompt.md")
people_guidelines = load_prompt("services/prompts/people_prompt.md")
item_guidelines = load_prompt("services/prompts/item_prompt.md")
hwagi_guidelines = load_prompt("services/prompts/hwagi_prompt.md")

def create_general_prompt(prompt_obj, basic_info, converted_thesaurus, work_summary, hwagi):
    """Generates the prompt for the general graph QA."""
    role = prompt_obj.get("role")
    depth = prompt_obj.get("depth")
    detail = prompt_obj.get("detail")

    return f"""{guidelines}
  
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

def create_selection_prompt(prompt_obj, basic_info, selected_icon, hwagi, full_entity_graph):
    """Generates the prompt for a specific selection (person, item, etc.)."""
    role = prompt_obj.get("role")
    depth = prompt_obj.get("depth")
    detail = prompt_obj.get("detail")
    label = prompt_obj.get("label")

    if label in ['1', '2', '3', '8', '9']:
        return f"""{people_guidelines}
        
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
        - 도상 URI 및 명칭: [{selected_icon.get('entity_uri')}] / @ko=[{pick_lang(selected_icon.get('pref_labels', []), "ko")}]/ @ko-Hani=[{pick_lang(selected_icon.get('pref_labels', []), "ko-Hani")}]/ @en=[{pick_lang(selected_icon.get('pref_labels', []), "en")}]/ @zh-Hans=[{pick_lang(selected_icon.get('pref_labels', []), "zh-Hans")}]/ @ja=[{pick_lang(selected_icon.get('pref_labels', []), "ja")}]
        - 학술 정의 및 어린이용 풀이: "{selected_icon.get('definition_scholarly')}" / "{selected_icon.get('child_note')}"
        - 도상 분류 및 역할: "{selected_icon.get('iconographic_category')}" / "{selected_icon.get('iconographic_role')}"
        (3) 본 작품 내 placement fact (prefix: KHP)
        - 작품 한정 위치 및 수인: "{selected_icon.get('position_labels')}" / "{selected_icon.get('mudra_labels')}"
        - 작품 한정 지물 및 상세 묘사: "{selected_icon.get('attribute_concept_labels')}" / "{selected_icon.get('attribute_text')}" / "{selected_icon.get('detail_feature')}"
        (4) 작품 해석 메타 (C 공통, prefix: KHP)
        - 작품 화기 해석 (work_creation_background): "{hwagi.get("work_creation_background")}"
        - 작품 학술 평가 (work_significance): "{hwagi.get("work_significance")}"
        """
    
    elif label == '용화수':
        return f"""{item_guidelines}
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
        - 지물 URI 및 명칭: [{selected_icon.get('entity_uri')}] / @ko=[{pick_lang(selected_icon.get('pref_labels', []), "ko")}]/ @ko-Hani=[{pick_lang(selected_icon.get('pref_labels', []), "ko-Hani")}]/ @en=[{pick_lang(selected_icon.get('pref_labels', []), "en")}]/ @zh-Hans=[{pick_lang(selected_icon.get('pref_labels', []), "zh-Hans")}]/ @ja=[{pick_lang(selected_icon.get('pref_labels', []), "ja")}]
        - 학술 정의 및 어린이용 풀이: "{selected_icon.get('definition_scholarly')}" / "{selected_icon.get('child_note')}"
        (3) host 도상 정보 (prefix: KHP)
        - 이 지물을 든 도상 (host_figures): {full_entity_graph}
        (4) 작품 해석 메타 (C 공통, prefix: KHP)
        - 작품 화기 해석 (work_creation_background): "{hwagi.get("work_creation_background")}"
        - 작품 학술 평가 (work_significance): "{hwagi.get("work_significance")}"
        """

    elif label == '화기':
        return f"""{hwagi_guidelines}
        # [User Input Data]
        1. 기본 정보 및 매트릭스 파라미터
        - 대상 유산: [장곡사 미륵불 괘불탱]
        - 관람객 국적: [{role}]
        - 관람객 유형: [{depth}]
        - 목표 언어: [{detail}]

        2. 문화유산 검증 지식 베이스
        (1) 작품 사실 정보 (A 공통, prefix: KHP)
        {basic_info}
        (2) 텍스트 기록 블록 (prefix: Hwagi 등)
        {selected_icon.get('inscription_blocks')}
        // 백엔드가 선택 블록(단일 또는 5블록 통합)의 블록명·원문·번역 묶음을 자연어로 빌드하여 동적 주입
        (3) 작품 해석 메타 (C 공통, R5 핵심, prefix: KHP)
        - 작품 화기 해석 (creation_background): "{hwagi.get("work_creation_background")}"
        * 핵심 키워드 감지 필수: [관용적 축원 문구 / 특정 조성 목적 / 회향문 및 발원]
        - 작품 학술 평가 (significance): "{hwagi.get("work_significance")}"
        """
    
    return None
