# Sommelier Backend

Este repositorio contiene el backend en **Flask** para el proyecto Sommelier.  
Su propósito es actuar como proxy seguro hacia la API de HeyGen y proveer endpoints para consultar documentos PDF.

## 🚀 Funcionalidades

- **HeyGen Access Token**  
  Endpoint `/api/get-access-token` que conecta con la API de HeyGen usando la variable de entorno `HEYGEN_API_KEY`.  
  El frontend llama a este endpoint para obtener un token seguro y crear sesiones interactivas.

- **Consulta de PDFs**  
  Endpoint `/api/ask` que recibe una pregunta y busca la respuesta en los PDFs almacenados en la carpeta `/pdfs`.  
  Actualmente usa búsqueda literal; se puede mejorar con embeddings y ChromaDB para consultas semánticas.

- **Healthcheck**  
  Endpoint `/api/health` para verificar que el servicio está activo.

## 📂 Estructura del proyecto

