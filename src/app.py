import os
import asyncio
from playwright.async_api import async_playwright
from openai import OpenAI
from dotenv import load_dotenv


# =========================
# CONFIGURACIÓN
# =========================
load_dotenv()  # Carga variables del .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("No se detectó la variable de entorno OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
BASE_URL = "https://www.eluniverso.com/politica/"

# =========================
# FUNCIONES
# =========================

async def obtener_links_y_textos():
    """Abre un solo navegador, obtiene links de noticias y extrae su texto."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Abrir página principal de política
        await page.goto(BASE_URL, timeout=60000)
        await page.wait_for_timeout(3000)

        # Extraer hrefs
        hrefs = await page.locator("a").all_attribute_values("href")
        noticias = []
        for href in hrefs:
            if href and ("/noticias/" in href or "/202" in href):
                if href.startswith("/"):
                    href = "https://www.eluniverso.com" + href
                noticias.append(href)

        # eliminar duplicados y limitar a 3 noticias
        noticias = list(set(noticias))[:3]

        # Extraer texto de cada noticia
        textos = []
        for link in noticias:
            await page.goto(link, timeout=60000)
            await page.wait_for_timeout(3000)
            paragraphs = await page.locator("article p").all_text_contents()
            texto = "\n".join(paragraphs)
            textos.append((link, texto))

        await browser.close()
    return textos

def resumir_texto(texto):
    """Envía texto a OpenAI para generar resumen."""
    prompt = f"""
    Resume la siguiente noticia política en máximo 5 párrafos claros y objetivos:

    {texto}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un analista político profesional."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

async def main():
    """Pipeline completo: links → texto → resumen → imprimir."""
    noticias = await obtener_links_y_textos()

    for link, texto in noticias:
        print(f"\nProcesando: {link}")

        if len(texto) < 500:
            print("Texto demasiado corto, posible error al extraer.")
            continue

        resumen = resumir_texto(texto)
        print("\n🔹 RESUMEN:")
        print(resumen)
        print("=" * 80)

# =========================
# EJECUTAR EL SCRIPT
# =========================
if __name__ == "__main__":
    asyncio.run(main())