import streamlit as st
import os
import tempfile
import time
from datetime import datetime
from Copper import process_pdf 
from sorting import optimize_by_material, save_cut_plan_csv, save_cut_plan_pdf
import pandas as pd

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Copper Cut Plan Optimizer", layout="wide")
st.title("📄 Copper Cut Plan Optimizer")

uploaded_files = st.file_uploader(
    "Upload one or more PDF files", type=["pdf"], accept_multiple_files=True
)

if uploaded_files:
    st.info(f"📥 {len(uploaded_files)} file(s) uploaded. Click 'Submit' to process.")
    if st.button("🚀 Submit"):

        all_regular_parts = []
        all_kanban_parts = []

        start_time = time.time()
        progress = st.progress(0, text="🔄 Starting PDF processing...")

        for idx, uploaded_file in enumerate(uploaded_files):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name

            try:
                regular, kanban = process_pdf(tmp_path)
                all_regular_parts.extend(regular)
                all_kanban_parts.extend(kanban)
            except Exception as e:
                st.error(f"❌ Failed to process {uploaded_file.name}: {e}")
            finally:
                os.remove(tmp_path)

            percent_complete = int((idx + 1) / len(uploaded_files) * 100)
            progress.progress((idx + 1) / len(uploaded_files), text=f"Processing file {idx + 1}/{len(uploaded_files)} ({percent_complete}%)")

        elapsed = time.time() - start_time
        st.success(f"✅ Processing complete in {elapsed:.2f} seconds.")

        if not all_regular_parts and not all_kanban_parts:
            st.warning("⚠️ No parts extracted from uploaded PDFs.")
        else:
            cuttable = [p for p in all_regular_parts if p.get("size") not in [None, "", 0]]
            non_cuttable = [p for p in all_regular_parts if p.get("size") in [None, "", 0]]

            cut_plans = optimize_by_material(cuttable)
            extras = {
                "KANBAN Items": all_kanban_parts,
                "Other Items": non_cuttable
            }

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = f"cut_plan_{timestamp}.csv"
            pdf_file = f"cut_plan_{timestamp}.pdf"

            save_cut_plan_csv(cut_plans, csv_file, extras)
            save_cut_plan_pdf(cut_plans, pdf_file, extras)

            st.subheader("📊 Optimized Cut Plan")
            for material, plans in cut_plans.items():
                st.markdown(f"### 🧱 Material: `{material}`")
                rows = []
                for i, (cuts, used) in enumerate(plans, 1):
                    for j, (length, mtg, name, part_no) in enumerate(cuts, 1):
                        rows.append({
                            "Bar": f"Bar {i}",
                            "Cut": f"Cut {j}",
                            "Length (in)": length,
                            "Part No.": part_no,
                            "Part Name": name,
                            "MTG #": mtg,
                            "Remaining": round(144 - used, 2) if j == 1 else None
                        })
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)

            if all_kanban_parts:
                st.subheader("📦 KANBAN Items")
                st.dataframe(pd.DataFrame(all_kanban_parts), use_container_width=True)

            if non_cuttable:
                st.subheader("❌ Non-Cuttable Items")
                st.dataframe(pd.DataFrame(non_cuttable), use_container_width=True)

            with open(csv_file, "rb") as f:
                st.download_button("⬇️ Download CSV", f, file_name=csv_file, mime="text/csv")

            with open(pdf_file, "rb") as f:
                st.download_button("⬇️ Download PDF", f, file_name=pdf_file, mime="application/pdf")

            os.remove(csv_file)
            os.remove(pdf_file)

