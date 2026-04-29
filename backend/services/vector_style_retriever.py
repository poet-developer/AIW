# services/vector_style_retriever.py

def retrieve_style_context(vectordb, query: str, k: int = 3) -> str:
    docs = vectordb.similarity_search(query=query, k=k)

    if not docs:
        return ""

    results = []
    for doc in docs:
        text = " ".join(doc.page_content.split())
        results.append(text[:300])
    print(f"Retrieved {len(results)} style examples for query: '{query}'")

    return "\n\n".join(results)