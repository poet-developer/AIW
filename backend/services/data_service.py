
def pick_lang(labels, lang="ko"):
    """n10s ARRAY '값@lang' → lang 일치 값 추출."""
    if not labels:
        return None
    
    if isinstance(labels, str):
        labels = [labels]

    for v in labels:
        if isinstance(v, str) and v.endswith(f"@{lang}"):
            return v.rsplit("@", 1)[0]
    
    # Return the first value if no language-specific value is found
    if labels and isinstance(labels[0], str):
        return labels[0].split("@")[0]
    
    return labels[0] if labels else None

def extract_work_summary(result): # 작품의 주요 정보를 추출하여 안내문 생성에 활용할 수 있는 형태로 가공하는 헬퍼 함수
    contributors = result.get("contributors", [])
    figures = result.get("figures", [])

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
