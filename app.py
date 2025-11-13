import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import fitz  # PyMuPDF

# Cargar variables desde .env (solo en desarrollo)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)

# Variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
PORT = int(os.getenv("PORT", 5000))
CHROMADB_PATH = os.getenv("CHROMADB_PATH", "./chroma_db")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/get-access-token", methods=["GET"])
def get_access_token():
    """
    Este endpoint actúa como proxy seguro hacia HeyGen.
    En producción, deberías implementar la llamada real a la API de HeyGen
    usando HEYGEN_API_KEY. Aquí devolvemos un mock para simplificar.
    """
    if not HEYGEN_API_KEY:
        return jsonify({"error": "HEYGEN_API_KEY no configurado"}), 500

    # TODO: implementar llamada real a HeyGen API
    return jsonify({"access_token": "mocked_token"}), 200


@app.route("/api/ask", methods=["POST"])
def ask():
    """
    Recibe una pregunta y busca la respuesta en los PDFs de /pdfs.
    """
    data = request.get_json()
    question = data.get("question", "").lower()

    pdf_dir = os.path.join(os.path.dirname(__file__), "pdfs")
    answers = []

    for filename in os.listdir(pdf_dir):
        if filename.endswith(".pdf"):
            doc = fitz.open(os.path.join(pdf_dir, filename))
            for page in doc:
                text = page.get_text().lower()
                if question in text:
                    answers.append(text)
            doc.close()

    if answers:
        return jsonify({"answer": answers[0][:500]}), 200
    else:
        return jsonify({"answer": "No encontré información en los PDFs."}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
