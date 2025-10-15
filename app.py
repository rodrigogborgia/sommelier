from flask import Flask, request, jsonify
# Importamos la clase para crear la plantilla de prompt
from langchain.prompts import PromptTemplate 
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from flask_cors import CORS 

# --- Configuración RAG ---
CHROMA_PATH = "chroma_db" 
EMBEDDINGS = OpenAIEmbeddings(model="text-embedding-3-small")
LLM = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2) 

try:
    # Cargar la base de datos de conocimiento 
    DB = Chroma(persist_directory=CHROMA_PATH, embedding_function=EMBEDDINGS)
except Exception as e:
    print("\n❌ ERROR CRÍTICO: La base de datos 'chroma_db' no se encontró o no se pudo cargar.")
    print("Asegúrate de ejecutar 'python3.11 indexer.py' con éxito antes de correr el servidor.")
    exit()

# Definición de la personalidad del avatar (System Prompt)
# Agregamos las variables {context} y {question} para el prompt
SYSTEM_PROMPT_TEXT = """
Tu nombre es Sammy, y eres una sommelier de carnes altamente calificada.
Tu objetivo es guiar una cata de carnes y responder preguntas de los participantes basándote 
EXCLUSIVAMENTE en el contexto que se te proporciona de los documentos de la cata.

INSTRUCCIONES CLAVE:
1. Siempre debes responder en ESPAÑOL.
2. Sé formal, amigable y muy concisa.
3. Limita tus respuestas a un máximo de 3 oraciones cortas.
4. Si la pregunta no se puede responder con la información proporcionada (el contexto), 
   responde: "Esa información no está en mis documentos de cata. ¿Puedo ayudarte con otra pregunta sobre carnes?"
5. No menciones que utilizas documentos o bases de datos vectoriales.

Contexto: {context}
Pregunta: {question}
"""

# CREACIÓN CLAVE: Convertimos la cadena de texto en un objeto PromptTemplate
CUSTOM_PROMPT = PromptTemplate.from_template(SYSTEM_PROMPT_TEXT)

RAG_CHAIN = ConversationalRetrievalChain.from_llm(
    llm=LLM, 
    retriever=DB.as_retriever(search_kwargs={"k": 3}),  # Busca los 3 trozos más relevantes
    # Pasamos el objeto PromptTemplate corregido
    combine_docs_chain_kwargs={"prompt": CUSTOM_PROMPT}, 
    verbose=False
)

# --- Configuración del Servidor Flask ---
app = Flask(__name__)
# Habilitar CORS para permitir la comunicación con HeyGen
CORS(app) 

# Lista para almacenar el historial de conversación (es crucial para RAG)
chat_history = [] 

@app.route('/api/ask', methods=['POST'])
def ask_avatar():
    global chat_history
    
    data = request.get_json()
    user_question = data.get('question')

    if not user_question:
        return jsonify({"answer": "Por favor, envía una pregunta."}), 400

    # Ejecuta la cadena RAG con el historial
    result = RAG_CHAIN.invoke(
        {"question": user_question, "chat_history": chat_history}
    )
    
    response_text = result['answer']

    # Actualiza el historial
    chat_history.append((user_question, response_text))
    
    # Devuelve la respuesta en formato JSON
    return jsonify({"answer": response_text})


if __name__ == '__main__':
    # El servidor correrá en el puerto 5000 (localhost:5000)
    app.run(debug=True, port=5000)
