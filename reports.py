import os
from fpdf import FPDF
import pandas as pd

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Industrial Economics Analyzer Report', 0, 1, 'C')
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
    chart_image_path: str
) -> bytes:
    """
    Generates a PDF report and returns the binary data.
    """
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Helper to safely encode text (fix for Latin-1 crashes)
    def safe_txt(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')
    
    # 1. Executive Summary
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 12, safe_txt(f"Recommendation: {winner_name}"), 0, 1, 'L', fill=True)
    
    pdf.set_font("Arial", size=11)
    pdf.ln(5)
    pdf.multi_cell(0, 6, f"Based on the Net Present Value (NPV) analysis using the LCM method over a {study_period}-year horizon, this project represents the most economically viable option.")
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(50, 8, f"NPV: ${winner_npv:,.2f}", 0, 1)
    pdf.set_font("Arial", size=10)
    pdf.cell(50, 5, f"(Calculated at MARR: {marr}%)", 0, 1)
    
    pdf.ln(10)

    # 2. Comparison Table
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Comparison Table", 0, 1)
    
    # Table Header
    pdf.set_font("Arial", 'B', 10)
    col_w = [70, 40, 50]
    pdf.cell(col_w[0], 8, "Project Name", 1)
    pdf.cell(col_w[1], 8, "Life Span", 1)
    pdf.cell(col_w[2], 8, "NPV", 1)
    pdf.ln()
    
    # Table Rows
    pdf.set_font("Arial", size=10)
    for _, row in results_df.iterrows():
        name = safe_txt(row.get('Project Name', 'Unknown'))
        life = str(row.get('Life Span', row.get('Life Span (Years)', 0)))
        npv = row.get('NPV', 0.0)
        
        pdf.cell(col_w[0], 8, name, 1)
        pdf.cell(col_w[1], 8, f"{life} Years", 1)
        pdf.cell(col_w[2], 8, f"${npv:,.2f}", 1)
        pdf.ln()
        
    pdf.ln(10)
    
    # 3. Chart
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, safe_txt(f"Cash Flow Diagram: {winner_name}"), 0, 1)
    
    if chart_image_path and os.path.exists(chart_image_path):
        try:
            pdf.image(chart_image_path, x=15, w=180)
        except Exception:
            pdf.cell(0, 10, "Error loading chart image", 0, 1)
            
    # Return binary
    return pdf.output(dest='S').encode('latin-1')