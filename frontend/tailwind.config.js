/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#ea580c", // TMU Orange-ish
                secondary: "#1e293b", // Slate 800
            }
        },
    },
    plugins: [],
}
