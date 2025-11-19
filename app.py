import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions
import requests
from flask_cors import CORS

# -------------------------------
# Cargar variables de entorno
# -------------------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)

# -------------------------------
# Configuración de CORS
# -------------------------------
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://tusommeliervirtual.com").split(",")
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# -------------------------------
# Variables globales
# -------------------------------
PORT = int(os.getenv("PORT", 5000))
CHROMADB_PATH = os.getenv("CHROMADB_PATH", "./chroma_db")

# -------------------------------
# Helpers
# -------------------------------
def get_api_key():
    """Obtiene la API key de HeyGen o lanza error si no está configurada."""
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        raise RuntimeError("HEYGEN_API_KEY no configurado")
    return api_key

def log_response(tag, response):
    """Loguea status, headers y cuerpo de la respuesta HTTP."""
    print(f"[{tag}] Status: {response.status_code}")
    print(f"[{tag}] Headers: {response.headers}")
    print(f"[{tag}] Raw response: {response.text}")

def safe_json_response(tag, response):
    """Valida que la respuesta sea JSON y la devuelve, o error si no lo es."""
    log_response(tag, response)
    if "application/json" in response.headers.get("Content-Type", ""):
        return response.json()
    return {"error": "Respuesta no-JSON de HeyGen", "raw": response.text}

def init_pdf_index():
    """Indexa PDFs en ChromaDB al iniciar la aplicación."""
    client = chromadb.PersistentClient(path=CHROMADB_PATH)
    collection = client.get_or_create_collection(
        name="pdf_collection",
        embedding_function=embedding_functions.DefaultEmbeddingFunction()
    )
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
    return collection

# Inicializar colección de PDFs
collection = init_pdf_index()

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
    try:
        api_key = get_api_key()
        response = requests.post(
            "https://api.heygen.com/v1/streaming.create_token",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "avatar_id": "Dexter_Doctor_Standing2_public",
                "voice_id": "1a32e06dde934e69ba2a98a71675dc16"
            }
        )
        data = safe_json_response("STREAMING", response)
        token = data.get("data", {}).get("token")
        return jsonify({"data": {"token": token}, "error": None}), response.status_code
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/avatars", methods=["GET"])
def get_avatars():
    try:
        api_key = get_api_key()
        response = requests.get(
            "https://api.heygen.com/v2/avatars",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return jsonify(safe_json_response("AVATARS", response)), response.status_code
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/voices", methods=["GET"])
def get_voices():
    try:
        api_key = get_api_key()
        response = requests.get(
            "https://api.heygen.com/v2/voices",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return jsonify(safe_json_response("VOICES", response)), response.status_code
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# HeyGen streaming session (new)
# -------------------------------
@app.route("/api/start-session", methods=["POST"])
def start_session():
    try:
        api_key = get_api_key()
        response = requests.post(
            "https://api.heygen.com/v1/streaming.new",   # ✅ endpoint correcto
            headers={
                "x-api-key": api_key,                   # ✅ usar x-api-key
                "accept": "application/json",
                "content-type": "application/json"
            },
            json={
                "avatar_id": "Dexter_Doctor_Standing2_public",
                "voice_id": "1a32e06dde934e69ba2a98a71675dc16",
                "quality": "medium",
                "video_encoding": "VP8",
                "disable_idle_timeout": False,
                "version": "v2",
                "stt_settings": {
                    "provider": "deepgram",
                    "confidence": 0.55
                },
                "activity_idle_timeout": 120
            }
        )
        data = safe_json_response("NEW_SESSION", response)
        token = data.get("data", {}).get("client_secret")
        session_id = data.get("data", {}).get("session_id")

        if not token or not session_id:
            return jsonify({"error": "No se recibió token o session_id de HeyGen", "raw": data}), 500

        return jsonify({
            "data": {
                "token": token,
                "session_id": session_id
            },
            "error": None
        }), response.status_code
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
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
