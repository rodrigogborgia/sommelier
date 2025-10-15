// InteractiveAvatarNextJSDemo/app/page.tsx
"use client";

import InteractiveAvatar from "@/components/InteractiveAvatar";
import Image from "next/image"; 

export default function App() {
  return (
    // Contenedor principal: permite scroll vertical y fondo oscuro
    <div className="w-screen flex flex-col bg-zinc-900 overflow-y-auto"> 
      {/* Contenedor central: AHORA CON MENOS PADDING INFERIOR (pb-4) */}
      <div className="w-[900px] flex flex-col items-start justify-start gap-5 mx-auto pt-8 pb-4">
        
        {/* --- CABECERA DE LA MARCA: LOGO ESPACIO SOMMELIER --- */}
        <div className="w-full text-center mb-8">
          <Image
            src="/Espacio_sommelier.png" 
            alt="Logo Espacio Sommelier"
            width={300} 
            height={60} 
            priority={true} 
            className="mx-auto"
          />
          <h1 className="text-xl font-semibold text-gray-300 mt-2">
            Asistente Sommelier de Carnes con IA
          </h1>
        </div>
        {/* ----------------------------------------------------- */}

        <div className="w-full">
          <InteractiveAvatar />
        </div>
      </div>
    </div>
  );
}