import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions

# Cargar variables de entorno (solo en desarrollo)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)

# Variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
PORT = int(os.getenv("PORT", 5000))
CHROMADB_PATH = os.getenv("CHROMADB_PATH", "./chroma_db")

# Inicializar cliente persistente de ChromaDB
client = chromadb.PersistentClient(path=CHROMADB_PATH)
collection = client.get_or_create_collection(
    name="pdf_collection",
    embedding_function=embedding_functions.DefaultEmbeddingFunction()
)

# Indexar PDFs al iniciar (solo una vez)
pdf_dir = os.path.join(os.path.dirname(__file__), "pdfs")
for filename in os.listdir(pdf_dir):
    if filename.endswith(".pdf"):
        doc = fitz.open(os.path.join(pdf_dir, filename))
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                doc_id = f"{filename}_{page_num}"
                if not collection.get(ids=[doc_id])["ids"]:
                    collection.add(
                        documents=[text],
                        metadatas=[{"source": filename, "page": page_num}],
                        ids=[doc_id]
                    )
        doc.close()

# Healthcheck original
@app.route("/health", methods=["GET"])
def health():
    """Endpoint de healthcheck estándar"""
    return jsonify({"status": "ok"}), 200

# Nuevo healthcheck bajo /api/healthcheck
@app.route("/api/healthcheck", methods=["GET"])
def api_healthcheck():
    """Endpoint de healthcheck para frontend/Nginx"""
    return jsonify({"status": "ok"}), 200

@app.route("/api/get-access-token", methods=["GET"])
def get_access_token():
    if not HEYGEN_API_KEY:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500
    return jsonify({"access_token": "mocked_token"}), 200

@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")

    if not question.strip():
        return jsonify({"error": "Pregunta vacía"}), 400

    results = collection.query(
        query_texts=[question],
        n_results=3
    )

    if results["documents"]:
        return jsonify({
            "answer": results["documents"][0][0],
            "source": results["metadatas"][0][0]
        }), 200
    else:
        return jsonify({"answer": "No encontré información en los PDFs."}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
