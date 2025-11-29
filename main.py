import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import os

# Import our custom modules
import logic
import reports

# -----------------------------------------------------------------------------
# CONFIG & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Industrial Economics Pro", layout="wide")

st.markdown("""
    <style>
    .rec-card { background-color: #f8f9fa; border-left: 6px solid #2c3e50; padding: 20px; border-radius: 4px; margin-bottom: 20px; }
    .rec-title { color: #2c3e50; margin: 0; font-size: 1.4rem; font-weight: 600; }
    .rec-metric { font-size: 2rem; font-weight: bold; color: #27ae60; margin: 10px 0; }
    @media print { [data-testid="stSidebar"], header, footer { display: none; } }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------
if 'projects' not in st.session_state:
    st.session_state.projects = []

if 'show_results' not in st.session_state:
    st.session_state.show_results = False

# -----------------------------------------------------------------------------
# HELPER: CACHED ANALYSIS
# -----------------------------------------------------------------------------
@st.cache_data
def run_full_analysis(project_list, marr):
    """
    Runs the math logic on a list of project dictionaries.
    """
    if not project_list:
        return 0, pd.DataFrame(), {}, None

    df = pd.DataFrame(project_list)
    
    # Sanitize: Ensure Life Span > 0
    df = df[df["Life Span (Years)"] > 0]
    
    if df.empty:
        return 0, pd.DataFrame(), {}, None

    lives = df["Life Span (Years)"].tolist()
    study_period = logic.calculate_lcm(lives)
    
    if study_period == 0:
        return 0, pd.DataFrame(), {}, None

    results = []
    detailed_flows = {}
    
    for _, row in df.iterrows():
        name = row.get("Project Name") or "Unnamed Project"
        
        life_span_val = int(row["Life Span (Years)"])
        inv_val = float(row["Initial Investment"])
            
        # Call logic module
        flows = logic.generate_cash_flows(
            investment=inv_val,
            revenue=float(row.get("Annual Revenue", 0)),
            cost=float(row.get("Annual Op. Cost", 0)),
            savings=float(row.get("Annual Savings", 0)),
            salvage=float(row.get("Salvage Value", 0)),
            replacement=float(row.get("Replacement Cost", 0)),
            life_span=life_span_val,
            study_period=study_period
        )
        
        npv = logic.calculate_npv(flows, marr)
        
        detailed_flows[name] = flows
        results.append({
            "Project Name": name,
            "NPV": npv,
            "Life Span": life_span_val
        })
        
    results_df = pd.DataFrame(results)
    winner = results_df.loc[results_df['NPV'].idxmax()] if not results_df.empty else None
    
    return study_period, results_df, detailed_flows, winner

# -----------------------------------------------------------------------------
# UI RENDERING
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Global Parameters")
    marr = st.number_input("MARR (%)", min_value=0.0, value=10.0, step=0.5)
    
    st.divider()
    if st.button("Clear All Projects"):
        st.session_state.projects = []
        st.session_state.show_results = False
        st.rerun()

st.title("Industrial Economics Project Analyzer")

# -----------------------------------------------------------------------------
# 1. INPUT SECTION
# -----------------------------------------------------------------------------
st.markdown("### 1. Add Projects")
st.markdown("Add projects one by one below. Once you have added all candidates, click 'Calculate Analysis'.")

with st.form("add_project_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        p_name = st.text_input("Project Name", value=f"Project {len(st.session_state.projects) + 1}")
        p_life = st.number_input("Life Span (Years)", min_value=1, value=5, step=1)
    
    with col2:
        p_invest = st.number_input("Initial Investment ($)", min_value=0.0, value=50000.0, step=1000.0)
        p_replace = st.number_input("Replacement Cost ($)", min_value=0.0, value=50000.0, step=1000.0)
        
    with col3:
        p_rev = st.number_input("Annual Revenue ($)", min_value=0.0, value=20000.0, step=1000.0)
        p_salvage = st.number_input("Salvage Value ($)", min_value=0.0, value=5000.0, step=500.0)
        
    with col4:
        p_cost = st.number_input("Annual Op. Cost ($)", min_value=0.0, value=5000.0, step=500.0)
        p_savings = st.number_input("Annual Savings ($)", min_value=0.0, value=0.0, step=500.0)

    submitted = st.form_submit_button("➕ Add Project to List")
    
    if submitted:
        new_project = {
            "Project Name": p_name,
            "Life Span (Years)": int(p_life),
            "Initial Investment": float(p_invest),
            "Replacement Cost": float(p_replace),
            "Annual Revenue": float(p_rev),
            "Salvage Value": float(p_salvage),
            "Annual Op. Cost": float(p_cost),
            "Annual Savings": float(p_savings)
        }
        st.session_state.projects.append(new_project)
        st.session_state.show_results = False # Reset results if new data added
        st.toast(f"Added {p_name}!")

# -----------------------------------------------------------------------------
# 2. PROJECT LIST & ACTIONS
# -----------------------------------------------------------------------------
if st.session_state.projects:
    st.divider()
    st.markdown(f"### 2. Project List ({len(st.session_state.projects)} candidates)")
    
    # Display simple table of added projects
    display_df = pd.DataFrame(st.session_state.projects)
    st.dataframe(
        display_df, 
        use_container_width=True,
        column_config={
            "Initial Investment": st.column_config.NumberColumn(format="$%.2f"),
            "Annual Revenue": st.column_config.NumberColumn(format="$%.2f"),
        }
    )
    
    if st.button("🚀 Calculate Analysis", type="primary"):
        st.session_state.show_results = True

# -----------------------------------------------------------------------------
# 3. ANALYSIS RESULTS
# -----------------------------------------------------------------------------
if st.session_state.show_results and st.session_state.projects:
    # Run Analysis (Cached)
    study_period, results_df, detailed_flows, winner = run_full_analysis(st.session_state.projects, marr)
    
    if study_period > 0 and winner is not None:
        st.divider()
        st.markdown("### 3. Analysis Results")

        # Winner Card
        st.markdown(f"""
        <div class="rec-card">
            <h3 class="rec-title">Recommendation: {winner['Project Name']}</h3>
            <div class="rec-metric">${winner['NPV']:,.2f}</div>
            <p>Highest NPV over {study_period} years at {marr}% MARR.</p>
        </div>
        """, unsafe_allow_html=True)

        # Generate Chart (On the fly)
        winner_flows = detailed_flows[winner['Project Name']]
        fig, ax = plt.subplots(figsize=(8, 4), facecolor='white')
        colors = ['#4682B4' if x >= 0 else '#800000' for x in winner_flows]
        ax.bar(range(len(winner_flows)), winner_flows, color=colors)
        ax.set_title(f"Cash Flow: {winner['Project Name']}")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Comparison Table**")
            st.dataframe(results_df.style.format({"NPV": "${:,.2f}"}), use_container_width=True)
        with col2:
            st.pyplot(fig)

        # PDF Generation
        if st.button("Generate PDF Report"):
            try:
                # 1. Save temp image
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                    fig.savefig(tmp_img.name, dpi=300, bbox_inches='tight')
                    tmp_img_path = tmp_img.name
                
                # 2. Generate PDF using report module
                pdf_bytes = reports.create_pdf_bytes(
                    winner_name=winner['Project Name'],
                    winner_npv=winner['NPV'],
                    study_period=study_period,
                    marr=marr,
                    results_df=results_df,
                    chart_image_path=tmp_img_path
                )
                
                # 3. Cleanup temp image
                if os.path.exists(tmp_img_path):
                    os.remove(tmp_img_path)

                # 4. Download
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name="econ_report.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")

        # Detailed Matrix
        st.divider()
        st.markdown("### Detailed Matrix")
        matrix_df = pd.DataFrame(detailed_flows)
        st.table(matrix_df.style.format("${:,.0f}"))