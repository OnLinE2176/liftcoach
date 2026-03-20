#!/usr/bin/env python3
"""
Render Mermaid diagram to high-resolution PNG using mermaid.ink API
"""
import requests
import base64
import sys
from pathlib import Path

# Mermaid diagram code
mermaid_code = """graph TD
    A([Launch Web App]) --> B{Have an Account?}
    B -- No --> C[Register]
    C --> D[Login]
    B -- Yes --> D
    
    D --> E{User Role?}
    
    %% Admin Flow
    E -- Admin --> F[Admin Dashboard]
    F --> G[Content Management System <br> Update Logo, Theme, Lessons]
    F --> H[User Management <br> Deactivate / Soft-Delete]
    
    %% Regular User Flow
    E -- Regular User --> I[Access LiftCoach Web App]
    I --> J[Home Interface]
    
    J --> K[Profile]
    K --> L[Edit Profile]
    L --> J
    
    J --> M[View Gallery]
    M --> J
    
    J --> N[Select Input Mode]
    
    N --> O[Live Camera]
    N --> P[Upload Video]
    
    O --> Q[Perform Lift <br> Snatch / Clean & Jerk]
    Q --> R[Capture Set <br> Auto-Calibration]
    
    P --> S[Select File]
    S --> T[Process File]
    
    R --> U[Analysis View <br> Skeleton / Ghost Overlay]
    T --> U
    
    U --> V{Save to Gallery?}
    V -- Yes --> W[Save Video with Input]
    V -- No --> J
    
    W --> X{Do Another?}
    X -- Yes --> N
    X -- No --> J
    
    J --> Y([End Session])"""

def render_mermaid_to_png(mermaid_code, output_file, scale=4):
    """
    Render Mermaid diagram to PNG using Kroki API (alternative service)
    
    Args:
        mermaid_code: The Mermaid diagram code
        output_file: Path to save the PNG file
        scale: Scale factor for high resolution (default: 4 = 4x resolution)
    """
    import json
    
    # First try mermaid.live API (POST request)
    print(f"Rendering Mermaid diagram to {output_file}...")
    
    try:
        # Use mermaid.live rendering service
        kroki_url = "https://kroki.io/mermaid/png"
        
        data = mermaid_code
        
        # Try with Kroki service
        response = requests.post(
            kroki_url,
            data=data,
            headers={"Content-Type": "text/plain"},
            timeout=30
        )
        response.raise_for_status()
        
        # Save the PNG file
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        file_size = Path(output_file).stat().st_size
        print(f"✓ Successfully saved to {output_file}")
        print(f"  File size: {file_size / (1024 * 1024):.2f} MB")
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Error rendering diagram: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    output_path = Path(__file__).parent / "diagram_3_highres.png"
    
    if render_mermaid_to_png(mermaid_code, str(output_path), scale=4):
        print(f"\nHigh-resolution PNG saved to: {output_path.absolute()}")
        sys.exit(0)
    else:
        sys.exit(1)
