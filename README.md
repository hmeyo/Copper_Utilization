# ⚙️ Copper Utilization

**Copper Cut Plan Optimizer** is a **Streamlit-based web application** designed to automate and optimize **copper bar cutting** from MIPs.

The program extracts part data from engineering drawing PDFs using **OpenAI’s GPT-4o vision model**, classifies parts into categories (cuttable, KANBAN, and others), and generates **optimized cut plans** to **minimize copper waste**. It displays results interactively and provides **downloadable CSV and PDF cut sheets**.

---

## 📌 Features

- 🧠 **AI-Powered Table Extraction**  
  Extracts part tables from engineering PDFs using OpenAI GPT-4o vision.

- 🔍 **Material-Based Grouping**  
  Automatically groups parts by material type (e.g., 1/4 X 2 BARE CU).

- ✂️ **Copper Cut Optimization**  
  Uses a bin-packing algorithm to optimize cuts from standard 144" bars.

- 📦 **KANBAN + Non-Cuttable Handling**  
  Separates out parts with KANBAN remarks or missing size fields.

- 📄 **Clean Output Files**  
  Interactive results table with export to **CSV** and **PDF** cut plans.

- 🌐 **Multi-PDF Support**  
  Upload and process multiple PDF files in one session.

---

This tool helps production teams generate accurate, efficient copper cut plans **in seconds**, improving material utilization and reducing manual effort.
