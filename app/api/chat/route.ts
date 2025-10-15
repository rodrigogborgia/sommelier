// /app/api/chat/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    try {
        // 1. Obtener la pregunta del usuario ('message') que viene del Front-end de HeyGen.
        const { message } = await req.json();

        // 2. Definir la URL de tu servidor Flask (Back-end RAG)
        // (Asegúrate de que el servidor Flask esté activo en el Terminal 1)
        const LOCAL_API_URL = 'http://127.0.0.1:5000/api/ask';

        console.log(`[PROXY] Enviando pregunta localmente a: ${LOCAL_API_URL}`);

        // 3. Llamada al servidor Flask
        const response = await fetch(LOCAL_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            // Enviamos el mensaje en el formato que tu API de Python espera ('question')
            body: JSON.stringify({
                question: message, 
            }),
        });

        if (!response.ok) {
            // Si Flask responde con un error 500, lo mostramos aquí
            throw new Error(`Error en el servidor Flask: ${response.statusText}`);
        }

        // 4. Obtener la respuesta de tu sommelier de carnes
        const data = await response.json();
        
        // 5. Devolver la respuesta a HeyGen. HeyGen usará este texto para hacer hablar al avatar.
        return NextResponse.json({ 
            response: data.answer // 'data.answer' contiene la respuesta final de GPT/RAG
        });

    } catch (error) {
        console.error('[PROXY] Error al procesar el chat:', error);
        return NextResponse.json({ error: 'Hubo un problema al conectar con el servidor experto en carnes.' }, { status: 500 });
    }
}