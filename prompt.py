import json
from typing import Dict, Optional
import openai
from PIL import Image
import base64
import io
import re

def image_to_base64(image: Image.Image) -> str:
    """Convert PIL image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def extract_part_data(image_base64: str) -> Optional[Dict]:
    """Extract part specifications using GPT-4o"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            #response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at identifying and extracting manufacturing tables from engineering documents. "
                        "You MUST look for the specific table format used in Hammond Power Solutions documents."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                "FIND AND EXTRACT ONLY THE MAIN PARTS TABLE THAT HAS THIS EXACT STRUCTURE:\n"
                                "1. Header row contains: HPS | TRANSFORMER # | B DWG. | QTY | JOB NO. | DUE DATE | MTG number\n"
                                "2. Second header contains: FINISH | PART | PART NAME | MATERIAL | SIZE | UNIT QTY. | ORDER QTY. | REMARKS\n"
                                "3. Subsequent rows contain part specifications with this pattern:\n"
                                "   - PART column has numbers (1, 2, 3...)\n"
                                "   - PART NAME will sometimes be like 'GROUND BUS'\n"
                                "   - MATERIAL contains specs like '1/8 X 3/4 PLATED CU'\n"
                                "   - SIZE contains lengths like '13.19\" LG.'\n\n"
                                "Ensure the 'size' value is a pure numeric string (e.g., '13.19') in inches — remove units like 'LG.', 'IN', and quotation marks.\n"
                                "\nAlso extract the MTG number from the title block (usually top right). "
                                "Return it as a string field: 'mtg_no'. Apply it to each part row."                                 
                                "Include the 'remarks' field from the REMARKS column for each part, if available.\n"
                                "IGNORE ALL OTHER TABLES AND CONTENT.\n"
                                "RETURN AS JSON WITH THIS STRUCTURE:\n"
                                '''{
                                    "table_found": boolean,
                                    "mtg_no": "MTG12345",
                                    "parts": [{
                                        "part_no": "2",
                                        "part_name": "GROUND BUS",
                                        "material": "1/8 X 3/4 PLATED CU",
                                        "size": "13.19\" LG.",
                                        "unit_qty": 1
                                        "remarks": "KANBAN in lots of 20"
                                    }]
                                }'''
                            )
                        }
                    ]
                }
            ],
            temperature=0.0  # Maximum determinism
        )
        #return json.loads(response.choices[0].message.content)
        content = response.choices[0].message.content.strip()

         # Clean up code block if GPT wrapped output in ```json ... ```
        if content.startswith("```json"):
            content = re.sub(r"^```json\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
        elif content.startswith("```"):
            content = re.sub(r"^```\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()

        if not content:
            print("Empty response from GPT")
            return {"table_found": False, "parts": []}

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print("JSON parsing failed:", e)
            print("Raw GPT response:\n", content)
            return {"table_found": False, "parts": []}
        
        
    except Exception as e:
        print(f"AI Extraction Error: {str(e)}")
        return {"table_found": False, "parts": []}