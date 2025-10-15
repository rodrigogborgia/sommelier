/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-geist-mono)"],
      },
      // --- AQUÍ SE INYECTA LA PALETA DE COLORES DE LA MARCA ---
      colors: {
        // 'primary' es el color que usa la plantilla de HeyGen para botones y acentos.
        primary: {
          DEFAULT: '#880000', // Un tono de rojo oscuro/burdeos elegante (Color de acento)
          light: '#B00000',
          dark: '#5C0000',
        },
        // Definimos un gris muy oscuro para el fondo general si es necesario
        'background-dark': '#1a1a1a', 
        // Color para el texto principal
        'text-light': '#f3f4f6', 
      },
      // --------------------------------------------------------
    },
  },
  darkMode: "class",
}