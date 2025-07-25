from typing import List, Tuple, Dict
from collections import defaultdict
from tabulate import tabulate
import csv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

'''
# Best-Fit Decreasing Algorithm (Greedy bin packing)
def optimize_cut_plan( sizes: List[Tuple[float, str, str]], quantities: List[int], mtgs: List[str], master_length: float) -> List[Tuple[List[Tuple[float, str, str, str]], float]]:
    
    # 1. Expand parts with quantities
    full_sizes = []
    for (size, part_name, part_no), qty, mtg in zip(sizes, quantities, mtgs):
        full_sizes.extend([(size, mtg, part_name, part_no)] * qty)
    
    # 2. Sort in descending order (critical for BFD)
    full_sizes.sort(reverse=True, key=lambda x: x[0])
    
    # 3. Best-Fit Decreasing Algorithm
    cut_plans = []
    
    for item in full_sizes:
        size, mtg, part_name, part_no = item
        best_bin = None
        min_remaining = master_length  # Track smallest remaining space
        
        # Check existing bins for the best fit
        for i, (cuts, used) in enumerate(cut_plans):
            remaining = master_length - used
            if size <= remaining and remaining < min_remaining:
                min_remaining = remaining
                best_bin = i
        
        # Place the item in the best bin (or start a new one)
        if best_bin is not None:
            cuts, used = cut_plans[best_bin]
            cuts.append(item)
            cut_plans[best_bin] = (cuts, used + size)
        else:
            cut_plans.append(([item], size))
    
    return cut_plans
'''
def optimize_cut_plan( sizes: List[Tuple[float, str, str]], quantities: List[int], mtgs: List[str], master_length: float) -> List[Tuple[List[Tuple[float, str, str, str]], float]]:
    # Prepare input
    full_parts = []
    for (size, name, part_no), qty, mtg in zip(sizes, quantities, mtgs):
        full_parts.extend([(size, mtg, name, part_no)] * qty)

    multiplier = 100
    int_parts = [(int(s * multiplier), mtg, name, part_no) for s, mtg, name, part_no in full_parts]
    int_lengths = [p[0] for p in int_parts]
    int_bar_length = int(master_length * multiplier)

    num_items = len(int_parts)
    num_bins = num_items  # worst case

    model = cp_model.CpModel()

    x = {}
    for i in range(num_items):
        for j in range(num_bins):
            x[i, j] = model.NewBoolVar(f'x_{i}_{j}')
    y = [model.NewBoolVar(f'y_{j}') for j in range(num_bins)]

    for i in range(num_items):
        model.Add(sum(x[i, j] for j in range(num_bins)) == 1)

    for j in range(num_bins):
        model.Add(
            sum(x[i, j] * int_lengths[i] for i in range(num_items)) <= int_bar_length
        )
        for i in range(num_items):
            model.AddImplication(x[i, j], y[j])

    model.Minimize(sum(y))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)

    bins = [[] for _ in range(num_bins)]
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for i in range(num_items):
            for j in range(num_bins):
                if solver.Value(x[i, j]):
                    bins[j].append(full_parts[i])
        bins = [(b, sum(x[0] for x in b)) for b in bins if b]
    else:
        print("❌ No feasible solution found.")
        bins = []

    return bins

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

