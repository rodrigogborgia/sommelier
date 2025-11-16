import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions
import requests
from flask_cors import CORS  # 👈 importar CORS

# Cargar variables de entorno (solo en desarrollo/local)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)

# -------------------------------
# Configuración de CORS
# -------------------------------
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://tusommeliervirtual.com").split(",")
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# Variables globales que no cambian
PORT = int(os.getenv("PORT", 5000))
CHROMADB_PATH = os.getenv("CHROMADB_PATH", "./chroma_db")

# Inicializar cliente persistente de ChromaDB
client = chromadb.PersistentClient(path=CHROMADB_PATH)
collection = client.get_or_create_collection(
    name="pdf_collection",
    embedding_function=embedding_functions.DefaultEmbeddingFunction()
)

# Indexar PDFs al iniciar
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

# -------------------------------
# Healthchecks
# -------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/api/healthcheck", methods=["GET"])
def api_healthcheck():
    return jsonify({"status": "ok"}), 200

# -------------------------------
# HeyGen endpoints
# -------------------------------
@app.route("/api/avatars", methods=["GET"])
def get_avatars():
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500

    try:
        response = requests.get(
            "https://api.heygen.com/v2/avatars",
            headers={"X-Api-Key": api_key}
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... (resto de endpoints igual que ya tenés)

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

print(app.url_map)
