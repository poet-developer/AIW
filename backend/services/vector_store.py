from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

def load_style_vectordb():
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-small",
        encode_kwargs={"normalize_embeddings": True}
    )

    print("임베딩 로드 완료")

    vectordb = FAISS.load_local(
        folder_path="db/vectorDB_e5_small",
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )

    print("🔥 벡터DB 로드 완료")

    return vectordb