import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions
import requests

# Cargar variables de entorno (solo en desarrollo/local)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)

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


@app.route("/api/create-session", methods=["POST"])
def create_session():
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500

    payload = request.get_json() or {}
    avatar_id = payload.get("avatar_id")
    voice_id = payload.get("voice_id")
    language = payload.get("language", "en")

    try:
        response = requests.post(
            "https://api.heygen.com/v2/streaming.new",
            headers={"X-Api-Key": api_key},
            json={
                "avatar_id": avatar_id,
                "voice": {"voice_id": voice_id},
                "language": language,
                "quality": "medium"
            }
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/send-message", methods=["POST"])
def send_message():
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500

    payload = request.get_json() or {}
    try:
        response = requests.post(
            "https://api.heygen.com/v2/streaming.send",
            headers={"X-Api-Key": api_key},
            json=payload
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/get-access-token", methods=["POST"])
def get_access_token():
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500

    try:
        response = requests.post(
            "https://api.heygen.com/v2/streaming.create_token",
            headers={"X-Api-Key": api_key}
        )
        print("HeyGen raw response:", response.text)
        data = response.json()
        token = data.get("data", {}).get("token")
        if not token:
            return jsonify({"error": "No se recibió token"}), 500
        return jsonify({"access_token": token}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------
# Preguntas a PDFs
# -------------------------------
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

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

print(app.url_map)
