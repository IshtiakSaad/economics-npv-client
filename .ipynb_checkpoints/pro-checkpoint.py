import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Industrial Economics Pro",
    page_icon="🏭",
    layout="wide"
)

# -----------------------------------------------------------------------------
# STATE MANAGEMENT (DEFAULT DATA)
# -----------------------------------------------------------------------------
if 'project_data' not in st.session_state:
    # Default starting data for demonstration
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
# LOGIC FUNCTIONS
# -----------------------------------------------------------------------------
def calculate_lcm(numbers):
    """Calculates LCM for a list of integers."""
    if not numbers:
        return 0
    # math.lcm requires integers
    integers = [int(n) for n in numbers]
    return math.lcm(*integers)

def generate_cash_flows(row, study_period):
    """
    Generates a list of cash flows for a single project over the study_period.
    """
    life = int(row["Life Span (Years)"])
    if life <= 0: return np.zeros(study_period + 1)
    
    investment = row["Initial Investment"]
    revenue = row["Annual Revenue"]
    cost = row["Annual Op. Cost"]
    savings = row["Annual Savings"]
    salvage = row["Salvage Value"]
    replacement = row["Replacement Cost"]
    
    # Calculate Net Annual Flow
    net_annual = revenue - cost + savings
    
    # Initialize array (Year 0 to N)
    flows = np.zeros(study_period + 1)
    
    # Year 0: Initial Investment
    flows[0] = -investment
    
    for t in range(1, study_period + 1):
        # 1. Regular Operation
        flows[t] += net_annual
        
        # 2. End of Life Cycle Events
        if t % life == 0:
            # Always get salvage value at end of life
            flows[t] += salvage
            
            # If it's NOT the end of the study period, we must replace the asset
            if t != study_period:
                flows[t] -= replacement
                
    return flows

def calculate_npv(flows, marr_percent):
    r = marr_percent / 100.0
    npv = 0.0
    for t, cf in enumerate(flows):
        npv += cf / ((1 + r) ** t)
    return npv

# -----------------------------------------------------------------------------
# SIDEBAR UI
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Global Parameters")
    marr = st.number_input("MARR / Discount Rate (%)", min_value=0.0, value=10.0, step=0.5)
    
    st.divider()
    st.info(
        "**Instructions:**\n"
        "1. Edit the table in the main view to add/modify projects.\n"
        "2. The app automatically calculates the LCM study period.\n"
        "3. Review the Detailed Analysis tab for year-by-year breakdowns."
    )

# -----------------------------------------------------------------------------
# MAIN UI
# -----------------------------------------------------------------------------
st.title("🏭 Industrial Economics Analyzer Pro")
st.markdown("### 1. Project Inputs")
st.caption("Edit values directly below. Add new rows for more projects.")

# EDITABLE DATAFRAME
# We use st.data_editor to allow full control over variables
edited_df = st.data_editor(
    st.session_state.project_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Initial Investment": st.column_config.NumberColumn(format="$%.2f"),
        "Annual Revenue": st.column_config.NumberColumn(format="$%.2f"),
        "Annual Op. Cost": st.column_config.NumberColumn(format="$%.2f"),
        "Annual Savings": st.column_config.NumberColumn(format="$%.2f"),
        "Salvage Value": st.column_config.NumberColumn(format="$%.2f"),
        "Replacement Cost": st.column_config.NumberColumn(format="$%.2f", help="Cost to replace machine. Usually same as Investment."),
    }
)

# Update session state with edits
st.session_state.project_data = edited_df

if len(edited_df) > 0:
    # -------------------------------------------------------------------------
    # CALCULATIONS
    # -------------------------------------------------------------------------
    
    # 1. Determine Study Period (LCM)
    lives = edited_df["Life Span (Years)"].tolist()
    # Filter out zeros or invalid inputs
    valid_lives = [x for x in lives if x > 0]
    
    if valid_lives:
        study_period = calculate_lcm(valid_lives)
    else:
        study_period = 0
        
    st.divider()
    
    if study_period > 0:
        col_summary, col_lcm = st.columns([3, 1])
        with col_lcm:
            st.metric("Study Period (LCM)", f"{study_period} Years")
            
        # 2. Process Data
        results = []
        detailed_flows = {} # Dictionary to hold flow arrays for the big table
        
        for index, row in edited_df.iterrows():
            name = row["Project Name"] if row["Project Name"] else f"Project {index+1}"
            
            # Generate Flows
            flows = generate_cash_flows(row, study_period)
            detailed_flows[name] = flows
            
            # Calculate NPV
            npv = calculate_npv(flows, marr)
            
            results.append({
                "Project Name": name,
                "NPV": npv,
                "IRR": np.nan, # Internal Rate of Return (Complex to solve robustly in simple script, skipping for stability)
                "Life Span": row["Life Span (Years)"]
            })
            
        results_df = pd.DataFrame(results)
        
        # Find Winner
        if not results_df.empty:
            winner = results_df.loc[results_df['NPV'].idxmax()]
            
            with col_summary:
                st.subheader(f"🏆 Best Choice: {winner['Project Name']}")
                st.write(f"This project provides the highest Net Present Value of **${winner['NPV']:,.2f}** over the {study_period}-year cycle.")

        # ---------------------------------------------------------------------
        # TABS FOR DETAILS
        # ---------------------------------------------------------------------
        tab1, tab2, tab3 = st.tabs(["📊 Charts & Summary", "📋 Detailed Cash Flow Table", "🧮 Formulas"])
        
        # TAB 1: VISUALS
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**NPV Comparison**")
                st.dataframe(
                    results_df.style.format({"NPV": "${:,.2f}"}).highlight_max(subset=["NPV"], color="#d4edda"),
                    use_container_width=True,
                    hide_index=True
                )
            
            with col2:
                # Plotting specific to the winner
                winner_name = winner["Project Name"]
                winner_flows = detailed_flows[winner_name]
                
                fig, ax = plt.subplots(figsize=(6, 4))
                colors = ['green' if x >= 0 else 'red' for x in winner_flows]
                ax.bar(range(len(winner_flows)), winner_flows, color=colors, alpha=0.7)
                ax.axhline(0, color='black', linewidth=0.8)
                ax.set_title(f"Cash Flow Diagram: {winner_name}")
                ax.set_xlabel("Year")
                ax.set_ylabel("Amount ($)")
                ax.grid(axis='y', linestyle='--', alpha=0.3)
                st.pyplot(fig)

        # TAB 2: DETAILED TABLE
        with tab2:
            st.markdown("### Year-by-Year Cash Flow Matrix")
            st.markdown("This table shows exactly how money moves every year, including operating costs, replacements, and salvage.")
            
            # Create a DataFrame where Index = Year, Columns = Projects
            matrix_df = pd.DataFrame(detailed_flows)
            matrix_df.index.name = "Year (t)"
            
            # Format and display
            st.dataframe(
                matrix_df.style.format("${:,.0f}").background_gradient(cmap="RdYlGn", axis=None),
                use_container_width=True,
                height=500
            )

        # TAB 3: MATH FORMULAS
        with tab3:
            st.markdown("### Mathematical Mechanics")
            
            st.markdown("#### 1. Least Common Multiple (LCM)")
            st.latex(r"N_{study} = \text{LCM}(n_A, n_B, ...)")
            st.write("We compare projects over a common time horizon to ensure fairness. Shorter projects are repeated until they match the study period.")

            st.markdown("#### 2. Net Present Value (NPV)")
            st.write("We discount future cash flows back to Year 0 to account for the time value of money.")
            st.latex(r"NPV = \sum_{t=0}^{N} \frac{CF_t}{(1 + i)^t}")
            st.markdown("""
            Where:
            * $CF_t$ = Net Cash Flow at year $t$
            * $i$ = MARR (Minimum Attractive Rate of Return)
            * $N$ = Total Study Period
            """)
            
            st.markdown("#### 3. Cash Flow Calculation Logic")
            st.latex(r"CF_t = \text{Revenue} - \text{OpCost} + \text{Savings}")
            st.write("**Special Years:**")
            st.markdown("""
            * **Year 0:** $- \text{Initial Investment}$
            * **Year } n, 2n, ... :** $+ \text{Salvage Value}$ (End of life cycle)
            * **Year } n, 2n, ... :** $- \text{Replacement Cost}$ (If $t \neq N$)
            """)
            
    else:
        st.warning("Please enter valid Life Span values > 0 to calculate.")
else:
    st.info("Please add projects to the table above.")