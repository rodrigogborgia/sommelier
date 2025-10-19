    import os
    import json
    import logging
    import base64
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    from dotenv import load_dotenv

    # Importaciones de LangChain para RAG y Gemini
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import PyPDFLoader, TextLoader
    from langchain_community.vectorstores import Chroma
    from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
    from langchain.chains import ConversationalRetrievalChain, RetrievalQA
    from langchain.memory import ConversationBufferMemory

    # --- Configuración Inicial ---
    load_dotenv()

    # Asegúrate de que la clave de API de Google Gemini esté disponible
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        # Esto es crítico para Render, si la variable de entorno falta
        logging.error("GEMINI_API_KEY no está configurada. La aplicación fallará.")
        raise ValueError("GEMINI_API_KEY no está configurada.")

    # Configuración de Logging
    logging.basicConfig(level=logging.INFO)

    app = Flask(__name__)
    # Permitir CORS para que Vercel pueda comunicarse con Render
    CORS(app)

    # --- Configuración de RAG (Vector Database y Chain) ---
    CHROMA_PATH = "chroma"
    DOCS_PATH = "docs"
    vectorstore = None
    rag_chain = None

    def setup_rag():
        """Inicializa el sistema RAG (vector store y chain)."""
        global vectorstore, rag_chain
        logging.info("Iniciando setup_rag...")

        # 1. Comprobar si la base de datos Chroma ya existe
        if os.path.exists(CHROMA_PATH) and os.path.isdir(CHROMA_PATH):
            logging.info("Base de datos Chroma existente detectada. Cargando...")
            try:
                # Reutilizar la base de datos existente
                vectorstore = Chroma(
                    persist_directory=CHROMA_PATH,
                    embedding_function=GoogleGenerativeAIEmbeddings(model="text-embedding-004")
                )
            except Exception as e:
                logging.error(f"Error al cargar Chroma DB existente: {e}. Reconstruyendo...")
                vectorstore = None
        
        # Si no existe o falló al cargar, se crea la base de datos
        if vectorstore is None:
            logging.info("Construyendo nueva base de datos Chroma...")
            
            documents = []
            
            # --- FIX: Verificar que la carpeta docs exista antes de intentar leerla ---
            if not os.path.exists(DOCS_PATH):
                logging.warning(f"Directorio de documentos no encontrado: {DOCS_PATH}. El RAG no tendrá contexto local.")
                return

            # Cargar documentos (solo PDF para el ejemplo)
            for filename in os.listdir(DOCS_PATH):
                filepath = os.path.join(DOCS_PATH, filename)
                if filename.endswith(".pdf"):
                    try:
                        loader = PyPDFLoader(filepath)
                        documents.extend(loader.load())
                        logging.info(f"Cargado: {filename}")
                    except Exception as e:
                        logging.error(f"Error al cargar PDF {filename}: {e}")
                elif filename.endswith(".txt"):
                    # Para archivos de texto simples
                    try:
                        loader = TextLoader(filepath)
                        documents.extend(loader.load())
                        logging.info(f"Cargado: {filename}")
                    except Exception as e:
                        logging.error(f"Error al cargar TXT {filename}: {e}")

            if not documents:
                logging.warning("No se encontraron documentos en la carpeta 'docs'. El RAG no tendrá contexto.")
                return

            # Dividir documentos en chunks para la incrustación
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            split_documents = text_splitter.split_documents(documents)
            logging.info(f"Documentos divididos en {len(split_documents)} trozos.")

            # Crear y persistir el vector store
            vectorstore = Chroma.from_documents(
                documents=split_documents,
                embedding=GoogleGenerativeAIEmbeddings(model="text-embedding-004"),
                persist_directory=CHROMA_PATH
            )
            vectorstore.persist()
            logging.info("Base de datos Chroma creada y persistida.")

        # 2. Inicializar el modelo y la cadena
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
        
        # Usar RetrievalQA para manejar solo la consulta sin historial
        rag_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff", # 'stuff' es simple y bueno para contexto pequeño/mediano
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}), # Busca los 3 chunks más relevantes
            return_source_documents=False # No necesitamos devolver las fuentes al HeyGen
        )
        logging.info("Chain de RetrievalQA inicializada.")


    # Inicialización de RAG al iniciar la aplicación
    with app.app_context():
        setup_rag()


    @app.route('/api/rag', methods=['POST'])
    def rag_endpoint():
        """
        Endpoint principal para recibir la pregunta de HeyGen y devolver la respuesta RAG.
        
        Espera un JSON con la pregunta del usuario.
        """
        try:
            data = request.json
            
            # La pregunta del usuario viene en el campo 'prompt'
            user_prompt = data.get('prompt')
            
            if not user_prompt:
                return jsonify({"error": "No prompt provided"}), 400

            logging.info(f"Pregunta recibida: {user_prompt}")

            # 1. Ejecutar la consulta RAG
            if rag_chain is None:
                 # Si no se pudo configurar el RAG, se usa solo Gemini
                 llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
                 response_text = llm.invoke(user_prompt).content
                 logging.warning("RAG no disponible. Usando solo Gemini para la respuesta.")
            else:
                # Ejecución normal de la cadena de conocimiento (RAG)
                response = rag_chain.invoke({"query": user_prompt})
                response_text = response['result']
            
            logging.info(f"Respuesta generada: {response_text}")

            # 2. Construir la respuesta final para HeyGen
            # HeyGen requiere la respuesta en un formato específico (voice, text)
            
            # --- CONFIGURACIÓN DE VOZ (CRÍTICA PARA ESPAÑOL) ---
            # Asegura que el avatar hable con un tono de español (LATAM) para la fluidez.
            HEYGEN_VOICE_CONFIG = {
                "voice_id": "es-US-Standard-B", # Voz femenina estándar en español (LATAM)
                "style": "Friendly",             # Tono amigable
                "pitch": "medium",               # Tono medio
                "speed": "medium",               # Velocidad media
            }
            
            # Formato de respuesta requerido por HeyGen
            response_data = {
                "text": response_text,
                "config": HEYGEN_VOICE_CONFIG
            }
            
            # 3. Devolver la respuesta a HeyGen
            return jsonify(response_data), 200

        except Exception as e:
            logging.error(f"Error interno en el endpoint RAG: {e}")
            return jsonify({"error": str(e)}), 500

    if __name__ == '__main__':
        # Esto es solo para pruebas locales, Render usará Gunicorn/Waitress
        app.run(host='0.0.0.0', port=5000)
