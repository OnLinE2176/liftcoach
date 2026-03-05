#!/usr/bin/env python3
"""
Batch render all updated Mermaid diagrams to PNG using Kroki API.
"""
import requests
import sys
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))

DIAGRAMS = [
    ("architecture.mmd", "architecture.png"),
    ("deployment_architecture.mmd", "deployment_architecture.png"),
    ("sequence_diagram.mmd", "sequence_diagram.png"),
    ("erd_diagram.mmd", "erd_diagram.png"),
]

def render_mermaid_to_png(mermaid_code, output_file):
    """Render Mermaid diagram to PNG using Kroki API."""
    print(f"  Rendering -> {os.path.basename(output_file)}...")
    try:
        response = requests.post(
            "https://kroki.io/mermaid/png",
            data=mermaid_code.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
            timeout=60,
        )
        response.raise_for_status()
        with open(output_file, "wb") as f:
            f.write(response.content)
        size_kb = os.path.getsize(output_file) / 1024
        print(f"  [OK] Saved ({size_kb:.0f} KB)")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [FAIL] Error: {e}", file=sys.stderr)
        return False

def render_mermaid_to_svg(mermaid_code, output_file):
    """Render Mermaid diagram to SVG using Kroki API."""
    print(f"  Rendering -> {os.path.basename(output_file)}...")
    try:
        response = requests.post(
            "https://kroki.io/mermaid/svg",
            data=mermaid_code.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
            timeout=60,
        )
        response.raise_for_status()
        with open(output_file, "wb") as f:
            f.write(response.content)
        size_kb = os.path.getsize(output_file) / 1024
        print(f"  [OK] Saved ({size_kb:.0f} KB)")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [FAIL] Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success_count = 0
    total = len(DIAGRAMS)

    for mmd_file, png_file in DIAGRAMS:
        mmd_path = os.path.join(APP_DIR, mmd_file)
        png_path = os.path.join(APP_DIR, png_file)
        svg_path = os.path.join(APP_DIR, mmd_file.replace(".mmd", ".svg"))

        print(f"\n[{mmd_file}]")
        if not os.path.exists(mmd_path):
            print(f"  [FAIL] File not found: {mmd_path}")
            continue

        with open(mmd_path, "r", encoding="utf-8") as f:
            code = f.read()

        ok_png = render_mermaid_to_png(code, png_path)
        ok_svg = render_mermaid_to_svg(code, svg_path)
        if ok_png and ok_svg:
            success_count += 1

    print(f"\n{'='*40}")
    print(f"Done: {success_count}/{total} diagrams rendered successfully.")
    sys.exit(0 if success_count == total else 1)
