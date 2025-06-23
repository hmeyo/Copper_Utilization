from typing import List, Tuple, Dict
from collections import defaultdict
from tabulate import tabulate
import csv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def optimize_cut_plan(sizes: List[float], quantities: List[int], mtgs: List[str], master_length: float) -> List[Tuple[List[Tuple[float, str, str, str]], float]]:
    full_sizes = []
    for size, qty, mtg in zip(sizes, quantities, mtgs):
        full_sizes.extend([(size[0], mtg, size[1], size[2])] * qty)

    full_sizes.sort(reverse=True, key=lambda x: x[0])
    cut_plans = []

    while full_sizes:
        current_length = master_length
        cuts = []
        remaining = []

        for size, mtg, part_name, part_no in full_sizes:
            if size <= current_length:
                cuts.append((size, mtg, part_name, part_no))
                current_length -= size
            else:
                remaining.append((size, mtg, part_name, part_no))

        cut_plans.append((cuts, master_length - current_length))
        full_sizes = remaining

    return cut_plans

def optimize_by_material(part_data: List[Dict], master_length: float = 144.0) -> Dict[str, List[Tuple[List[Tuple[float, str, str, str]], float]]]:
    grouped = defaultdict(lambda: {'sizes': [], 'quantities': [], 'mtgs': []})
    all_cut_plans = {}

    for part in part_data:
        try:
            size = float(part.get("size", 0))
            qty = int(part.get("unit_qty", 0))
            mtg = part.get("mtg_no", "UNKNOWN").strip()
            name = part.get("part_name", "")
            number = str(part.get("part_no", ""))
            material = part.get("material", "Unknown").strip().upper()
            grouped[material]['sizes'].append((size, name, number))
            grouped[material]['quantities'].append(qty)
            grouped[material]['mtgs'].append(mtg)
        except (ValueError, TypeError):
            continue

    for material, data in grouped.items():
        print(f"\n=== Material: {material} ===")
        plans = optimize_cut_plan(data['sizes'], data['quantities'], data['mtgs'], master_length)
        all_cut_plans[material] = plans

        for i, (cuts, used_length) in enumerate(plans, start=1):
            sequence = [[f"Bar {i}", f"Cut {j+1}", cut[0], cut[3], cut[2], cut[1], master_length - used_length if j == 0 else ""] for j, cut in enumerate(cuts)]
            print(tabulate(sequence, headers=["Bar #", "Cut #", "Length (in)", "Part No.", "Part Name", "MTG #", "Remaining Offcut"], tablefmt="fancy_grid"))
        print(f"\nTotal Bars Used: {len(plans)}")

    return all_cut_plans

def save_cut_plan_csv(all_cut_plans: Dict[str, List[Tuple[List[Tuple[float, str, str, str]], float]]], filename: str, extras: Dict[str, List[Dict]] = None):
    master_length = 144.0
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for material, plans in all_cut_plans.items():
            writer.writerow([f"Material: {material}"])
            writer.writerow(["Bar #", "Cut #", "Length (in)", "Part No.", "Part Name", "MTG #", "Remaining Offcut"])

            for i, (cuts, used_length) in enumerate(plans, start=1):
                for j, (length, mtg, part_name, part_no) in enumerate(cuts, start=1):
                    writer.writerow([
                        f"Bar {i}",
                        f"Cut {j}",
                        length,
                        part_no,
                        part_name,
                        mtg,
                        master_length - used_length if j == 1 else ""
                    ])
            writer.writerow([])

        if extras:
            for label, rows in extras.items():
                writer.writerow([label])
                if rows:
                    headers = rows[0].keys()
                    writer.writerow(headers)
                    for row in rows:
                        writer.writerow([row.get(h, "") for h in headers])
                writer.writerow([])

def save_cut_plan_pdf(all_cut_plans, filename, extras=None):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica", 10)

    for material, plans in all_cut_plans.items():
        c.drawString(40, y, f"Material: {material}")
        y -= 15
        c.drawString(40, y, "Bar # | Cut # | Length (in) | Part No. | Part Name | MTG # | Remaining")
        y -= 15
        for i, (cuts, used_length) in enumerate(plans, start=1):
            for j, (cut, mtg, name, part_no) in enumerate(cuts, start=1):
                line = f"Bar {i} | Cut {j} | {cut} | {part_no} | {name} | {mtg} | {144 - used_length if j == 1 else ''}"
                c.drawString(40, y, line)
                y -= 15
                if y < 60:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = height - 40
            y -= 5
        y -= 20

    c.save()

