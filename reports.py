import os
from fpdf import FPDF
import pandas as pd

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Industrial Economics Analysis Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf_bytes(
    winner_name: str, 
    winner_npv: float, 
    study_period: int, 
    marr: float, 
    results_df: pd.DataFrame, 
    project_list: list,
    detailed_flows: dict,
    chart_image_path: str
) -> bytes:
    """
    Generates a comprehensive academic-style PDF report.
    """
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Helper to safely encode text (fix for Latin-1 crashes)
    def safe_txt(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')
    
    # --- SECTION 1: METHODOLOGY ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. Mathematical Framework", 0, 1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, safe_txt(
        "This analysis employs the Least Common Multiple (LCM) method to compare investment alternatives with unequal life spans. "
        f"All projects are evaluated over a common study period of {study_period} years. "
        "Future cash flows are discounted to their present value using the defined Minimum Attractive Rate of Return (MARR)."
    ))
    pdf.ln(3)
    
    # Formulas (Text representation)
    pdf.set_font("Courier", size=9)
    pdf.cell(0, 5, safe_txt(f"MARR (i) = {marr}%"), 0, 1)
    pdf.cell(0, 5, safe_txt("NPV      = Sum [ CF_t / (1 + i)^t ]"), 0, 1)
    pdf.cell(0, 5, safe_txt("Net Flow = Revenue - Op. Cost + Savings"), 0, 1)
    pdf.ln(5)

    # --- SECTION 2: PROJECT PARAMETERS ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. Project Inputs", 0, 1)
    
    # Header
    pdf.set_font("Arial", 'B', 9)
    widths = [35, 20, 25, 25, 25, 25, 25]
    headers = ["Name", "Life", "Inv($)", "Rev($)", "Cost($)", "Salv($)", "Repl($)"]
    
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 7, h, 1, 0, 'C')
    pdf.ln()
    
    # Rows
    pdf.set_font("Arial", size=9)
    for p in project_list:
        pdf.cell(widths[0], 7, safe_txt(p['Project Name'][:18]), 1)
        pdf.cell(widths[1], 7, str(p['Life Span (Years)']), 1, 0, 'C')
        pdf.cell(widths[2], 7, f"{p['Initial Investment']:,.0f}", 1, 0, 'R')
        pdf.cell(widths[3], 7, f"{p['Annual Revenue']:,.0f}", 1, 0, 'R')
        pdf.cell(widths[4], 7, f"{p['Annual Op. Cost']:,.0f}", 1, 0, 'R')
        pdf.cell(widths[5], 7, f"{p['Salvage Value']:,.0f}", 1, 0, 'R')
        pdf.cell(widths[6], 7, f"{p['Replacement Cost']:,.0f}", 1, 0, 'R')
        pdf.ln()
    
    pdf.ln(5)

    # --- SECTION 3: DETAILED CALCULATIONS ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. Step-by-Step Calculations", 0, 1)
    
    for p in project_list:
        name = p['Project Name']
        life = p['Life Span (Years)']
        inv = p['Initial Investment']
        rev = p['Annual Revenue']
        cost = p['Annual Op. Cost']
        sav = p['Annual Savings']
        salv = p['Salvage Value']
        repl = p['Replacement Cost']
        
        # Calculate Net Annual
        net_annual = rev - cost + sav
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, safe_txt(f"Project: {name}"), 0, 1)
        
        pdf.set_font("Arial", size=9)
        pdf.write(5, safe_txt(f"   • Net Annual Flow = {rev:,.0f} (Rev) - {cost:,.0f} (Cost) + {sav:,.0f} (Sav) = "))
        pdf.set_font("Arial", 'B', 9)
        pdf.write(5, safe_txt(f"${net_annual:,.0f}\n"))
        
        pdf.set_font("Arial", size=9)
        pdf.multi_cell(0, 5, safe_txt(
            f"   • Cycle: Every {life} years, the asset is retired (Salvage +${salv:,.0f}) and replaced (Cost -${repl:,.0f}). "
            "At the end of the study period, only Salvage is applied."
        ))
        
        # Show first few terms of equation
        pdf.set_font("Courier", size=8)
        term_str = f"   NPV = -{inv:,.0f} + {net_annual:,.0f}/(1.{(int(marr))})^1 + {net_annual:,.0f}/(1.{(int(marr))})^2 + ... "
        pdf.cell(0, 5, safe_txt(term_str), 0, 1)
        
        # Get final NPV for this project
        proj_res = next((r for index, r in results_df.iterrows() if r['Project Name'] == name), None)
        final_val = proj_res['NPV'] if proj_res is not None else 0
        
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 5, safe_txt(f"   Resulting NPV: ${final_val:,.2f}"), 0, 1)
        pdf.ln(3)

    pdf.ln(5)

    # --- SECTION 4: EXECUTIVE SUMMARY ---
    pdf.add_page() # Start results on new page if needed
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "4. Executive Summary & Recommendation", 0, 1)

    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, safe_txt(f"  Recommended Option: {winner_name}"), 0, 1, 'L', fill=True)
    
    pdf.set_font("Arial", size=10)
    pdf.ln(2)
    pdf.multi_cell(0, 6, safe_txt(
        f"Based on the analysis, {winner_name} yields the highest Net Present Value (NPV) of ${winner_npv:,.2f}. "
        "This indicates it is the most capital-efficient choice given the constraints."
    ))
    pdf.ln(5)

    # Comparison Table
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "NPV Comparison Table", 0, 1)
    
    col_w = [70, 40, 50]
    pdf.cell(col_w[0], 8, "Project Name", 1)
    pdf.cell(col_w[1], 8, "Life Span", 1)
    pdf.cell(col_w[2], 8, "NPV", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for index, row in results_df.iterrows():
        name = safe_txt(row['Project Name'])
        life = str(row['Life Span'])
        npv = row['NPV']
        
        # Highlight winner row logic if desired, simplified here
        pdf.cell(col_w[0], 8, name, 1)
        pdf.cell(col_w[1], 8, f"{life} Years", 1)
        pdf.cell(col_w[2], 8, f"${npv:,.2f}", 1)
        pdf.ln()
    
    pdf.ln(10)

    # --- SECTION 5: VISUALIZATION ---
    if chart_image_path and os.path.exists(chart_image_path):
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, safe_txt(f"5. Cash Flow Diagram ({winner_name})"), 0, 1)
        try:
            pdf.image(chart_image_path, x=15, w=180)
        except Exception:
            pdf.cell(0, 10, "Chart image unavailable.", 0, 1)

    return pdf.output(dest='S').encode('latin-1')