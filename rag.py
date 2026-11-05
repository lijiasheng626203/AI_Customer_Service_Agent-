from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS


# 1. 加载知识库文档
KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent / "knowledge_base"
loader = DirectoryLoader(
    str(KNOWLEDGE_BASE_DIR),
    glob="*.txt",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"}
)

documents = loader.load()
print(f"加载了 {len(documents)} 个文档")

if not documents:
    raise ValueError("知识库中没有找到 .txt 文件，请检查 knowledge_base 文件夹。")


# 2. 文本切分
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

chunks = text_splitter.split_documents(documents)
print(f"切分后得到 {len(chunks)} 个文本块")


# 3. 使用本地 Ollama 模型生成 Embedding
embeddings = OllamaEmbeddings(
    model="nomic-embed-text"
)


# 4. 创建 FAISS 向量数据库
vectorstore = FAISS.from_documents(
    chunks,
    embeddings
)


# 5. 创建 Retriever
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 3}
)

print("RAG 知识库创建完成！")
