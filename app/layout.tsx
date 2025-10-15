import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css"; // Ruta corregida

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Espacio Sommelier | Asistente de Carnes IA",
  description: "Asistente de IA de Espacio Sommelier experto en carnes.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // Se elimina la variable de fuente de la clase
    // Se añade suppressHydrationWarning para ignorar el conflicto del body
    <html lang="en"> 
      <body suppressHydrationWarning={true}>
        {children}
      </body>
    </html>
  );
}