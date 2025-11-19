import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions
import requests
from flask_cors import CORS

# Cargar variables de entorno (solo en desarrollo/local)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)

# -------------------------------
# Configuración de CORS
# -------------------------------
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://tusommeliervirtual.com").split(",")
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# Variables globales
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
@app.route("/api/healthcheck", methods=["GET"])
def api_healthcheck():
    return jsonify({"status": "ok"}), 200

@app.route("/healthcheck", methods=["GET"])
def root_healthcheck():
    return jsonify({"status": "ok"}), 200

# -------------------------------
# HeyGen endpoints
# -------------------------------
@app.route("/api/get-access-token", methods=["POST"])
def get_access_token():
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500
    try:
        # ⚡ Crear sesión de streaming en HeyGen
        response = requests.post(
            "https://api.heygen.com/v1/streaming.create",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "avatar_id": "Dexter_Doctor_Standing2_public",  # 👈 tu avatar elegido
                "voice_id": "VOZ_ID_REAL"                      # 👈 reemplazar con un voice_id válido
            }
        )
        print("Respuesta HeyGen streaming:", response.status_code, response.text)  # log para debug
        data = response.json()
        token = data.get("data", {}).get("client_secret")
        return jsonify({"data": {"token": token}, "error": None}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/avatars", methods=["GET"])
def get_avatars():
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500
    try:
        response = requests.get(
            "https://api.heygen.com/v2/avatars",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        print("Respuesta HeyGen avatars:", response.status_code, response.text)  # log para debug
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/voices", methods=["GET"])
def get_voices():
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500
    try:
        response = requests.get(
            "https://api.heygen.com/v2/voices",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        print("Respuesta HeyGen voices:", response.status_code, response.text)  # log para debug

        # Intentar parsear como JSON
        try:
            voices = response.json()
        except Exception:
            return jsonify({"error": "Respuesta no es JSON", "raw": response.text}), response.status_code

        # Asegurarnos que voices sea dict y tenga 'data'
        data = voices.get("data", [])
        if not isinstance(data, list):
            return jsonify({"error": "Formato inesperado", "raw": voices}), response.status_code

        # Filtrar solo voces masculinas en español
        filtered = [
            v for v in data
            if v.get("gender") == "male" and v.get("language", "").startswith("es")
        ]

        return jsonify({"data": filtered}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Query PDFs endpoint
# -------------------------------
@app.route("/api/query", methods=["POST"])
def query_pdfs():
    data = request.get_json()
    question = data.get("question")
    if not question:
        return jsonify({"error": "Pregunta requerida"}), 400

    try:
        results = collection.query(query_texts=[question], n_results=3)
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
