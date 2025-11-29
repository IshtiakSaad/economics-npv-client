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
    if st.button("🗑️ Clear All Projects"):
        st.session_state.projects = []
        st.session_state.show_results = False
        st.rerun()

st.title("Industrial Economics Project Analyzer")

# -----------------------------------------------------------------------------
# 1. INPUT & PROJECT MANAGEMENT
# -----------------------------------------------------------------------------
st.markdown("### 1. Project Management")
st.caption("Add projects to the candidate list.")

# Form to add
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

    submitted = st.form_submit_button("➕ Add Project")
    
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
        st.session_state.show_results = False 
        st.rerun()

# List & Delete
if st.session_state.projects:
    st.divider()
    st.markdown(f"**Current Candidates ({len(st.session_state.projects)})**")
    
    # Show list
    display_df = pd.DataFrame(st.session_state.projects)
    st.dataframe(
        display_df, 
        use_container_width=True,
        column_config={
            "Initial Investment": st.column_config.NumberColumn(format="$%.2f"),
            "Annual Revenue": st.column_config.NumberColumn(format="$%.2f"),
        }
    )
    
    # Delete Functionality
    col_d1, col_d2 = st.columns([3, 1])
    with col_d1:
        project_names = [p['Project Name'] for p in st.session_state.projects]
        to_delete = st.selectbox("Select project to remove:", ["Select..."] + project_names, label_visibility="collapsed")
    with col_d2:
        if st.button("Delete Selected"):
            if to_delete and to_delete != "Select...":
                st.session_state.projects = [p for p in st.session_state.projects if p['Project Name'] != to_delete]
                st.session_state.show_results = False
                st.rerun()

    if st.button("🚀 Calculate Analysis", type="primary"):
        st.session_state.show_results = True

# -----------------------------------------------------------------------------
# 2. MATHEMATICAL FORMULATION
# -----------------------------------------------------------------------------
st.divider()
st.markdown("### 2. Mathematical Framework")
st.markdown("The analysis uses the **LCM Method** to compare projects with unequal lives over a common study period.")

mf_col1, mf_col2 = st.columns(2)

with mf_col1:
    st.info("**Net Present Value (NPV)**")
    st.latex(r"NPV = \sum_{t=0}^{N} \frac{CF_t}{(1 + i)^t}")
    st.markdown(f"""
    * **$N$**: Study Period (LCM of all life spans)
    * **$i$**: MARR ({marr}%)
    * **$CF_t$**: Net Cash Flow at year $t$
    """)

with mf_col2:
    st.info("**Annual Cash Flow Logic**")
    st.latex(r"CF_t = (R - C + S_{av}) + S_{al} - Rep")
    st.markdown("""
    * **$R$**: Revenue, **$C$**: Op. Cost, **$S_{av}$**: Savings
    * **$S_{al}$**: Salvage Value (added at end of life cycle)
    * **$Rep$**: Replacement Cost (subtracted at end of life cycle, if not end of study)
    """)

# -----------------------------------------------------------------------------
# 3. ANALYSIS RESULTS
# -----------------------------------------------------------------------------
if st.session_state.show_results and st.session_state.projects:
    st.divider()
    
    # Run Analysis (Cached)
    study_period, results_df, detailed_flows, winner = run_full_analysis(st.session_state.projects, marr)
    
    if study_period > 0 and winner is not None:
        st.markdown("### 3. Analysis Results")

        # Winner Card
        st.markdown(f"""
        <div class="rec-card">
            <h3 class="rec-title">🏆 Recommendation: {winner['Project Name']}</h3>
            <div class="rec-metric">${winner['NPV']:,.2f}</div>
            <p>Highest NPV over the <b>{study_period}-year</b> common study period.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Cash Flow Comparison")
        st.caption("Visualizing the cash flow streams for all candidates.")

        # --- ALL CHARTS COMPARISON ---
        # We'll display them in a grid (2 columns)
        chart_cols = st.columns(2)
        
        for idx, (p_name, flows) in enumerate(detailed_flows.items()):
            # Determine which column to place chart in
            with chart_cols[idx % 2]:
                is_winner = (p_name == winner['Project Name'])
                border_color = '#27ae60' if is_winner else '#bdc3c7'
                bg_color = '#f0fff4' if is_winner else '#ffffff'
                
                # Plot
                fig, ax = plt.subplots(figsize=(6, 3), facecolor=bg_color)
                colors = ['#4682B4' if x >= 0 else '#C0392B' for x in flows]
                ax.bar(range(len(flows)), flows, color=colors)
                ax.axhline(0, color='black', linewidth=0.8)
                
                # Styling
                title_prefix = "🏆 WINNER: " if is_winner else ""
                ax.set_title(f"{title_prefix}{p_name}", fontsize=10, fontweight='bold', color='black')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_visible(False)
                ax.spines['bottom'].set_visible(False)
                ax.get_yaxis().set_visible(False) # Hide Y axis values to reduce clutter
                ax.set_facecolor(bg_color)
                
                st.pyplot(fig)
                
        st.divider()

        # --- TABLE & PDF ---
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("#### Comparison Table")
            st.dataframe(results_df.style.format({"NPV": "${:,.2f}"}).highlight_max(subset=["NPV"], color="#d4edda"), use_container_width=True)
            
        with col2:
            st.markdown("#### Export Report")
            if st.button("Generate PDF Report", type="primary", use_container_width=True):
                try:
                    # Generate temp image of just the winner for the PDF
                    winner_flows = detailed_flows[winner['Project Name']]
                    fig, ax = plt.subplots(figsize=(8, 4), facecolor='white')
                    colors = ['#4682B4' if x >= 0 else '#800000' for x in winner_flows]
                    ax.bar(range(len(winner_flows)), winner_flows, color=colors)
                    ax.set_title(f"Cash Flow: {winner['Project Name']}")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                        fig.savefig(tmp_img.name, dpi=300, bbox_inches='tight')
                        tmp_img_path = tmp_img.name
                    
                    pdf_bytes = reports.create_pdf_bytes(
                        winner_name=winner['Project Name'],
                        winner_npv=winner['NPV'],
                        study_period=study_period,
                        marr=marr,
                        results_df=results_df,
                        project_list=st.session_state.projects,
                        detailed_flows=detailed_flows,
                        chart_image_path=tmp_img_path
                    )
                    
                    if os.path.exists(tmp_img_path): os.remove(tmp_img_path)

                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name="econ_report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")

        # Detailed Matrix
        with st.expander("View Detailed Year-by-Year Matrix", expanded=False):
            matrix_df = pd.DataFrame(detailed_flows)
            st.table(matrix_df.style.format("${:,.0f}"))

        # --- NEW SECTION: STEP BY STEP CALCULATION ---
        st.divider()
        st.markdown("### 4. Step-by-Step Math Calculations")
        st.caption(f"Showing how the NPV was derived for each project over the {study_period}-year study period.")

        for p_name, flows in detailed_flows.items():
            # Get project inputs safely
            proj_data = next(p for p in st.session_state.projects if p["Project Name"] == p_name)
            
            with st.expander(f"🧮 See Calculations for: {p_name}"):
                
                # 1. Net Annual Flow
                net_annual = proj_data['Annual Revenue'] - proj_data['Annual Op. Cost'] + proj_data['Annual Savings']
                st.markdown("**1. Calculate Net Annual Flow:**")
                st.latex(r"Net = \text{Revenue} - \text{Cost} + \text{Savings}")
                st.latex(f"Net = {proj_data['Annual Revenue']:,.0f} - {proj_data['Annual Op. Cost']:,.0f} + {proj_data['Annual Savings']:,.0f} = \mathbf{{\${net_annual:,.0f}}}")

                # 2. Key Timeline Events
                st.markdown("**2. Timeline Events:**")
                st.markdown(f"""
                * **Year 0:** Initial Investment = $\mathbf{{-{proj_data['Initial Investment']:,.0f}}}$
                * **Every Year:** Net Annual Flow = $\mathbf{{+{net_annual:,.0f}}}$
                * **Every {proj_data['Life Span (Years)']} Years:** Add Salvage ($\mathbf{{+{proj_data['Salvage Value']:,.0f}}}$) and Subtract Replacement Cost ($\mathbf{{-{proj_data['Replacement Cost']:,.0f}}}$)
                """)

                # 3. NPV Equation Construction
                st.markdown("**3. NPV Summation:**")
                
                # Build the equation string dynamically
                terms = []
                # Year 0
                terms.append(f"-{proj_data['Initial Investment']:,.0f}")
                
                # Show first 3 years
                limit = min(3, len(flows)-1)
                for t in range(1, limit + 1):
                    # Format as fraction
                    terms.append(f"\\frac{{{flows[t]:,.0f}}}{{(1 + {marr/100})^{{{t}}}}}")
                
                # If study period is long, add dots and then the last term
                if len(flows) > 5:
                    terms.append("...")
                    last_t = len(flows) - 1
                    terms.append(f"\\frac{{{flows[last_t]:,.0f}}}{{(1 + {marr/100})^{{{last_t}}}}}")
                elif len(flows) > limit:
                     for t in range(limit + 1, len(flows)):
                        terms.append(f"\\frac{{{flows[t]:,.0f}}}{{(1 + {marr/100})^{{{t}}}}}")

                # Join terms with + sign
                latex_eq = " + ".join(terms)
                # Clean up double signs (e.g. "+ -")
                latex_eq = latex_eq.replace("+ -", "- ")
                
                st.latex(f"NPV = {latex_eq}")
                
                # Final Result
                final_npv = next(r['NPV'] for r in results_df.to_dict('records') if r['Project Name'] == p_name)
                st.markdown(f"**Result:** $NPV = \mathbf{{\${final_npv:,.2f}}}$")