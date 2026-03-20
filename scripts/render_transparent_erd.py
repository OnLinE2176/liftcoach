import requests
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
mmd_path = os.path.join(APP_DIR, "erd_diagram.mmd")
png_path = os.path.join(APP_DIR, "erd_diagram_transparent.png")

with open(mmd_path, "r", encoding="utf-8") as f:
    original_code = f.read()

# Add theme customization for transparent background and white lines/text
custom_theme = """%%{init: {
  "theme": "base",
  "themeVariables": {
    "background": "transparent",
    "primaryColor": "transparent",
    "primaryTextColor": "#ffffff",
    "primaryBorderColor": "#ffffff",
    "lineColor": "#ffffff",
    "secondaryColor": "transparent",
    "tertiaryColor": "transparent",
    "fontFamily": "arial"
  }
}}%%
"""

mermaid_code = custom_theme + original_code

print("Rendering transparent ERD via Kroki...")
try:
    response = requests.post(
        "https://kroki.io/mermaid/png",
        data=mermaid_code.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=60,
    )
    response.raise_for_status()
    with open(png_path, "wb") as f:
        f.write(response.content)
    print(f"Successfully saved to {png_path}")
except Exception as e:
    print(f"Error: {e}")
