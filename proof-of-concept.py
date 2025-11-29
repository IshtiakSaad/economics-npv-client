import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Industrial Economics Project Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# CSS FOR PROFESSIONAL UI
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    /* Spacing adjustments */
    .block-container { padding-top: 2rem; }
    
    /* Executive Summary Card Style */
    .rec-card {
        background-color: #f8f9fa;
        border-left: 6px solid #2c3e50;
        padding: 20px;
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .rec-title {
        color: #2c3e50;
        margin-top: 0;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 1.4rem;
        font-weight: 600;
    }
    .rec-metric {
        font-size: 2rem;
        font-weight: bold;
        color: #27ae60;
        margin: 10px 0;
    }
    .rec-text {
        color: #555;
        font-size: 1rem;
        line-height: 1.5;
    }
    
    /* Print Styles: Hide sidebar and unnecessary elements when printing */
    @media print {
        [data-testid="stSidebar"] { display: none; }
        header { display: none; }
        footer { display: none; }
        .block-container { padding-top: 0 !important; }
        .stApp { background-color: white !important; }
        /* Ensure tables don't get cut off */
        .stTable { overflow: visible !important; }
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# STATE MANAGEMENT
# -----------------------------------------------------------------------------
if 'project_data' not in st.session_state:
    default_data = {
        "Project Name": ["Project A", "Project B"],
        "Initial Investment": [50000.0, 85000.0],
        "Life Span (Years)": [3, 4],
        "Annual Revenue": [25000.0, 35000.0],
        "Annual Op. Cost": [6000.0, 4000.0],
        "Annual Savings": [0.0, 1000.0],
        "Salvage Value": [4000.0, 6000.0],
        "Replacement Cost": [50000.0, 85000.0],
    }
    st.session_state.project_data = pd.DataFrame(default_data)

# -----------------------------------------------------------------------------
# CORE LOGIC FUNCTIONS
# -----------------------------------------------------------------------------
def calculate_lcm(numbers):
    """Calculates Least Common Multiple for a list of integers."""
    if not numbers:
        return 0
    integers = [int(n) for n in numbers]
    return math.lcm(*integers)

def generate_cash_flows(row, study_period):
    """Generates the cash flow array for the full LCM study period."""
    life = int(row["Life Span (Years)"])
    if life <= 0: return np.zeros(study_period + 1)
    
    investment = row["Initial Investment"]
    revenue = row["Annual Revenue"]
    cost = row["Annual Op. Cost"]
    savings = row["Annual Savings"]
    salvage = row["Salvage Value"]
    replacement = row["Replacement Cost"]
    
    net_annual = revenue - cost + savings
    flows = np.zeros(study_period + 1)
    
    # Year 0: Initial Investment
    flows[0] = -investment
    
    for t in range(1, study_period + 1):
        # 1. Regular Operation
        flows[t] += net_annual
        
        # 2. End of Life Cycle Events
        if t % life == 0:
            # Add Salvage Value
            flows[t] += salvage
            
            # Subtract Replacement Cost (unless it's the very end of study)
            if t != study_period:
                flows[t] -= replacement
                
    return flows

def calculate_npv(flows, marr_percent):
    """Calculates Net Present Value."""
    r = marr_percent / 100.0
    npv = 0.0
    for t, cf in enumerate(flows):
        npv += cf / ((1 + r) ** t)
    return npv

# -----------------------------------------------------------------------------
# PDF REPORT GENERATOR
# -----------------------------------------------------------------------------
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Industrial Economics Analyzer Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(winner, study_period, marr, results_df, chart_image_path):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. Executive Summary Box
    pdf.set_fill_color(240, 240, 240) # Light gray background
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 12, f"Recommendation: {winner['Project Name']}", 0, 1, 'L', fill=True)
    
    pdf.set_font("Arial", size=11)
    pdf.ln(5)
    pdf.multi_cell(0, 6, f"Based on the Net Present Value (NPV) analysis using the LCM method over a {study_period}-year horizon, this project represents the most economically viable option.")
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(50, 8, f"NPV: ${winner['NPV']:,.2f}", 0, 1)
    pdf.set_font("Arial", size=10)
    pdf.cell(50, 5, f"(Calculated at MARR: {marr}%)", 0, 1)
    
    pdf.ln(10)

    # 2. Comparison Table
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Comparison Table", 0, 1)
    
    # Table Header
    pdf.set_font("Arial", 'B', 10)
    col_w = [70, 40, 50] # Column widths
    pdf.cell(col_w[0], 8, "Project Name", 1)
    pdf.cell(col_w[1], 8, "Life Span", 1)
    pdf.cell(col_w[2], 8, "NPV", 1)
    pdf.ln()
    
    # Table Rows
    pdf.set_font("Arial", size=10)
    for index, row in results_df.iterrows():
        pdf.cell(col_w[0], 8, str(row['Project Name']), 1)
        # Note: Accessing 'Life Span' here, not 'Life Span (Years)' based on result_df structure
        pdf.cell(col_w[1], 8, f"{row['Life Span']} Years", 1)
        pdf.cell(col_w[2], 8, f"${row['NPV']:,.2f}", 1)
        pdf.ln()
        
    pdf.ln(10)
    
    # 3. Chart Embed
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Cash Flow Diagram: {winner['Project Name']}", 0, 1)
    
    if chart_image_path and os.path.exists(chart_image_path):
        # Image width roughly fits the page (A4 width is ~210mm)
        pdf.image(chart_image_path, x=15, w=180)
    else:
        pdf.cell(0, 10, "Chart image unavailable.", 0, 1)

    return pdf.output(dest='S').encode('latin-1')

# -----------------------------------------------------------------------------
# UI LAYOUT: SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Global Parameters")
    marr = st.number_input("MARR / Discount Rate (%)", min_value=0.0, value=10.0, step=0.5)
    
    st.divider()
    st.markdown("### User Guide")
    st.info(
        "1. Define the MARR (Interest Rate).\n"
        "2. Input project data in the editable table.\n"
        "3. Review the Analysis and download the PDF report."
    )

# -----------------------------------------------------------------------------
# UI LAYOUT: MAIN CONTENT
# -----------------------------------------------------------------------------
st.title("Industrial Economics Project Analyzer")

# --- SECTION 1: FORMULAS ---
st.markdown("### 1. Mathematical Formulation")
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.markdown("**Net Present Value (NPV)**")
    st.latex(r"NPV = \sum_{t=0}^{N} \frac{CF_t}{(1 + i)^t}")
    st.caption(f"Calculated using MARR (i) = {marr}%")
with col_f2:
    st.markdown("**Cash Flow Calculation (Year t)**")
    st.latex(r"CF_t = (Rev - Cost + Sav) + S - Rep")

st.divider()

# --- SECTION 2: INPUTS ---
st.markdown("### 2. Project Inputs")
edited_df = st.data_editor(
    st.session_state.project_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Initial Investment": st.column_config.NumberColumn(format="$%.2f", required=True),
        "Annual Revenue": st.column_config.NumberColumn(format="$%.2f", required=True),
        "Annual Op. Cost": st.column_config.NumberColumn(format="$%.2f", required=True),
        "Annual Savings": st.column_config.NumberColumn(format="$%.2f"),
        "Salvage Value": st.column_config.NumberColumn(format="$%.2f"),
        "Replacement Cost": st.column_config.NumberColumn(format="$%.2f"),
    }
)
st.session_state.project_data = edited_df

if len(edited_df) > 0:
    # -------------------------------------------------------------------------
    # CALCULATIONS
    # -------------------------------------------------------------------------
    lives = edited_df["Life Span (Years)"].tolist()
    valid_lives = [x for x in lives if x > 0]
    
    if valid_lives:
        study_period = calculate_lcm(valid_lives)
    else:
        study_period = 0
        
    st.divider()
    
    if study_period > 0:
        # Process Data
        results = []
        detailed_flows = {} 
        
        for index, row in edited_df.iterrows():
            name = row["Project Name"] if row["Project Name"] else f"Project {index+1}"
            flows = generate_cash_flows(row, study_period)
            detailed_flows[name] = flows
            npv = calculate_npv(flows, marr)
            results.append({
                "Project Name": name,
                "NPV": npv,
                "Life Span": row["Life Span (Years)"]
            })
            
        results_df = pd.DataFrame(results)
        
        if not results_df.empty:
            winner = results_df.loc[results_df['NPV'].idxmax()]
            winner_name = winner["Project Name"]
            winner_flows = detailed_flows[winner_name]

            # -----------------------------------------------------------------
            # SECTION 3: ANALYSIS RESULTS
            # -----------------------------------------------------------------
            st.markdown("### 3. Analysis Results")
            
            # --- Executive Summary Card (HTML/CSS) ---
            st.markdown(f"""
            <div class="rec-card">
                <h3 class="rec-title">Executive Recommendation: {winner['Project Name']}</h3>
                <p class="rec-text">
                    Based on the Net Present Value (NPV) analysis using the LCM method over a <b>{study_period}-year</b> horizon, 
                    this project represents the most economically viable option.
                </p>
                <div class="rec-metric">${winner['NPV']:,.2f}</div>
                <p class="rec-text" style="font-size: 0.9em; color: #7f8c8d;">
                    Net Present Value at MARR {marr}%
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # --- Chart Generation (Matplotlib) ---
            # Create chart with white background for cleaner PDF/Print
            fig, ax = plt.subplots(figsize=(8, 4), facecolor='white')
            colors = ['#4682B4' if x >= 0 else '#800000' for x in winner_flows] # SteelBlue & Maroon
            
            ax.bar(range(len(winner_flows)), winner_flows, color=colors, edgecolor='black', linewidth=0.5)
            ax.axhline(0, color='black', linewidth=1)
            
            ax.set_title(f"Cash Flow Diagram: {winner_name}", fontsize=10, fontweight='bold')
            ax.set_xlabel("Year (t)", fontsize=9)
            ax.set_ylabel("Cash Flow ($)", fontsize=9)
            ax.grid(axis='y', linestyle=':', alpha=0.5, color='gray')
            
            # Remove top and right borders
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # Save chart to temp file for PDF inclusion
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                fig.savefig(tmp_file.name, dpi=300, bbox_inches='tight')
                chart_path = tmp_file.name

            # --- PDF Button ---
            try:
                pdf_data = create_pdf(winner, study_period, marr, results_df, chart_path)
                st.download_button(
                    label="📄 Download Official PDF Report",
                    data=pdf_data,
                    file_name="industrial_econ_report.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")

            # --- Results Layout ---
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**NPV Comparison Table**")
                formatted_results = results_df.copy()
                formatted_results['NPV'] = formatted_results['NPV'].apply(lambda x: f"${x:,.2f}")
                st.table(formatted_results)
            with col2:
                st.pyplot(fig)

        st.divider()

        # ---------------------------------------------------------------------
        # SECTION 4: DETAILED MATRIX
        # ---------------------------------------------------------------------
        st.markdown("### 4. Detailed Cash Flow Matrix")
        st.write("This table details the net cash flow for every year of the study period.")
        
        matrix_df = pd.DataFrame(detailed_flows)
        matrix_df.index.name = "Year"
        
        # Format currency (no decimals for cleaner table)
        display_matrix = matrix_df.applymap(lambda x: f"${x:,.0f}")
        
        # Use st.table for a full static view that prints well
        st.table(display_matrix)

    else:
        st.warning("Invalid Life Span entered.")
else:
    st.write("Please add projects to the input table to begin analysis.")