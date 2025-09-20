from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI  # Only for generation
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings  # Local embeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

# --- Load environment variables ---
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable not set")

# --- Setup paths ---
BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "data" / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

# --- Global storage for vector stores (filename -> FAISS vector store) ---
vector_stores = {}

# --- Create FastAPI app ---
app = FastAPI()

# --- Enable CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Root endpoint ---
@app.get("/")
def home():
    return {"message": "Backend running successfully with Hybrid Gemini + Local Embeddings"}

# --- Upload endpoint (extract text, chunk with LangChain, store in FAISS with local embeddings) ---
@app.post("/upload")
async def upload_pdf(file: UploadFile):
    try:
        # Save the PDF
        pdf_path = PDF_DIR / file.filename
        with open(pdf_path, "wb") as f:
            f.write(await file.read())

        # Extract text
        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or ""

        # Split text into chunks using LangChain
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=50,
            length_function=len
        )
        chunks = text_splitter.split_text(full_text)

        # Create local embeddings using Hugging Face
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vector_store = FAISS.from_texts(chunks, embeddings)
        vector_stores[file.filename] = vector_store

        return {
            "filename": file.filename,
            "total_chars": len(full_text),
            "num_chunks": len(chunks),
            "preview": full_text[:300]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# --- Ask endpoint (use LangChain retrieval chain with Gemini for generation) ---
@app.post("/ask")
async def ask_question(filename: str = Form(...), question: str = Form(...)):
    try:
        if filename not in vector_stores:
            return {"error": f"No data found for '{filename}'. Upload the PDF first."}

        # Retrieve vector store
        vector_store = vector_stores[filename]

        # Set up Gemini LLM (only used here, within free tier limits)
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3
        )

        # Prompt template for RAG
        system_prompt = (
            "You are a helpful assistant that answers questions based on provided document excerpts. "
            "Answer concisely and cite relevant parts if possible."
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Context: {context}\n\nQuestion: {input}\nAnswer:")
        ])

        # Create retrieval chain
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        retrieval_chain = create_retrieval_chain(
            vector_store.as_retriever(search_kwargs={"k": 3}),
            question_answer_chain
        )

        # Run the query
        result = retrieval_chain.invoke({"input": question})
        answer = result["answer"]
        top_docs = result["context"]

        return {
            "question": question,
            "filename": filename,
            "answer": answer,
            "top_matches": [
                {"chunk": doc.page_content, "score": 1.0} for doc in top_docs
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}