#Use this Copper.py script to extract it works 

import os
from dotenv import load_dotenv
from pdf2image import convert_from_path
from typing import List, Dict, Tuple
import json
import openai
from PIL import Image
from prompt import extract_part_data, image_to_base64
from tabulate import tabulate
from collections import defaultdict
import csv 
from datetime import datetime
from sorting import optimize_by_material, save_cut_plan_csv

try:
    import streamlit as st
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    print("🔒 Failed to read API key from Streamlit secrets:", e)

# Load environment variables
# load_dotenv()
# openai.api_key = os.getenv("OPENAI_API_KEY")

def pdf_to_images(pdf_path: str) -> List[Image.Image]:
    """Convert PDF to high-quality images"""
    try:
        return convert_from_path(pdf_path, dpi=400, fmt='png')
    except Exception as e:
        print(f"Error converting PDF to images: {str(e)}")
        return []

def process_pdf(pdf_path: str) -> Tuple[List[Dict], List[Dict]]:
    """Process a PDF file and extract part data"""
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return [], []

    images = pdf_to_images(pdf_path)
    if not images:
        return [], []

    all_parts = []
    kanban_parts = []
    
    for i, img in enumerate(images):
        print(f"\nProcessing page {i + 1}/{len(images)}...")
        img_base64 = image_to_base64(img)
        result = extract_part_data(img_base64)
        
        if result and result.get("table_found", False):
            mtg_no = result.get("mtg_no", "UNKNOWN")
            parts = result.get("parts", [])

            page_regular_parts = 0
            page_kanban_parts = 0

            for part in parts:
                remarks = part.get("remarks", "").upper()
                part["mtg_no"] = mtg_no
                part.pop("dimensions", None)

                if "KANBAN" in remarks:
                    kanban_parts.append(part)
                    page_kanban_parts += 1
                    print(f"Moved part {part.get('part_no')} to KANBAN table.")
                else:
                    all_parts.append(part)
                    page_regular_parts += 1

            print(f"Page {i + 1}: {page_regular_parts} regular, {page_kanban_parts} KANBAN (MTG: {mtg_no})")
        else:
            print("No target table found on this page.")

    return all_parts, kanban_parts


def group_by_material(parts):
    """Group parts by material and summarize quantities"""
    grouped = defaultdict(list)
    
    for part in parts:
        material_key = part.get("material", "Unknown").strip().upper()
        grouped[material_key].append(part)
    return grouped


def main():
    pdf_files = [
        "mtgpkgMTG292158.pdf",  # Replace with your actual PDF files    
        #"mtgpkgMTG288863.pdf",
    ]
    all_regular_parts = []
    all_kanban_parts = []

    for pdf_path in pdf_files:
        print(f"\nProcessing PDF: {pdf_path}")
        regular_parts, kanban_parts = process_pdf(pdf_path)
        all_regular_parts.extend(regular_parts)
        all_kanban_parts.extend(kanban_parts)

    filename = f"grouped_parts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    print("\n=== Extraction Results ===")
    print(json.dumps({
        "regular_parts": all_regular_parts,
        "kanban_parts": all_kanban_parts
    }, indent=2))


    if not all_regular_parts and not all_kanban_parts:
        print("\nNo part data extracted from any PDF.")
        return  

    cuttable_parts = [p for p in all_regular_parts if p.get("size") not in [None, "", 0]]
    non_cuttable_parts = [p for p in all_regular_parts if p.get("size") in [None, "", 0]]

    print(f"\nCuttable parts: {len(cuttable_parts)}, Non-cuttable: {len(non_cuttable_parts)}")


    cut_plans = optimize_by_material(cuttable_parts)

    extras = {
        "KANBAN Items": all_kanban_parts,
        "Other Items": non_cuttable_parts
    }

    save_cut_plan_csv(cut_plans, filename, extras=extras)
    print(f"\nCut plan + KANBAN + Other items saved to {filename}") 

if __name__ == "__main__":
    main()
