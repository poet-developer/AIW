from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any


class Neo4jVectorStore:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        model_name: str = "intfloat/multilingual-e5-small",
        label: str = "Chunk",
        embedding_property: str = "embedding",
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self.label = label
        self.embedding_property = embedding_property
        self.model = SentenceTransformer(model_name)

    def close(self):
        self.driver.close()

    def embed_passage(self, text: str) -> List[float]:
        return self.model.encode(
            f"passage: {text}",
            normalize_embeddings=True
        ).tolist()

    def create_chunks_bulk(self, chunks: List[Dict[str, Any]]):
        rows = []
        for chunk in chunks:
            rows.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "source_type": chunk.get("source_type", ""),
                "ref_id": chunk.get("ref_id", ""),
                "embedding": self.embed_passage(chunk["text"]),
            })

        query = f"""
        UNWIND $rows AS row
        MERGE (c:{self.label} {{chunk_id: row.chunk_id}})
        SET c.text = row.text,
            c.source_type = row.source_type,
            c.ref_id = row.ref_id,
            c.{self.embedding_property} = row.embedding
        """

        with self.driver.session(database=self.database) as session:
            session.run(query, rows=rows)

        print(f"✅ {len(rows)}개 Chunk 저장 완료")