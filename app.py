import os
import requests
from flask import Flask, jsonify, request
import fitz  # PyMuPDF para leer PDFs

app = Flask(__name__)

# --- Configuración ---
HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY")
PDF_FOLDER = os.path.join(os.path.dirname(__file__), "pdfs")

# --- Endpoint para HeyGen ---
@app.route("/api/get-access-token", methods=["GET"])
def get_access_token():
    """
    Llama a la API de HeyGen para obtener un token de acceso.
    """
    url = "https://api.heygen.com/v1/interactive-avatar/token"
    headers = {"Authorization": f"Bearer {HEYGEN_API_KEY}"}
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify({"error": "HeyGen API request failed", "details": response.text}), 500

# --- Función auxiliar para leer PDFs ---
def read_pdfs():
    """
    Lee todos los PDFs en la carpeta /pdfs y devuelve su texto concatenado.
    """
    all_text = ""
    if not os.path.exists(PDF_FOLDER):
        return "No se encontró la carpeta /pdfs"

    for filename in os.listdir(PDF_FOLDER):
        if filename.endswith(".pdf"):
            filepath = os.path.join(PDF_FOLDER, filename)
            doc = fitz.open(filepath)
            for page in doc:
                all_text += page.get_text()
            doc.close()
    return all_text

# --- Endpoint para preguntas sobre PDFs ---
@app.route("/api/ask", methods=["POST"])
def ask_pdf():
    """
    Recibe una pregunta y busca la respuesta en los PDFs.
    """
    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    pdf_text = read_pdfs()

    # Estrategia simple: devolver un fragmento del texto que contenga la pregunta
    if question.lower() in pdf_text.lower():
        # Buscar la primera ocurrencia
        idx = pdf_text.lower().find(question.lower())
        snippet = pdf_text[max(0, idx-100): idx+200]
        return jsonify({"answer": snippet}), 200
    else:
        return jsonify({"answer": "No se encontró información relacionada en los PDFs"}), 200

# --- Healthcheck ---
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
