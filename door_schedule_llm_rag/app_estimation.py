import streamlit as st
import pandas as pd
from db import SessionLocal
from models import Project, HardwareEstimation, MasterComponent
from calculations import calculate_bid
from sqlalchemy.orm import Session

def render_estimation_dashboard():
    st.subheader("🧮 Project Estimation Dashboard")
    
    db: Session = SessionLocal()
    
    projects = db.query(Project).all()
    if not projects:
        st.info("No projects found. Please process a PDF in the extraction tabs first to generate a project.")
        db.close()
        return

    project_options = {p.id: p.name or p.id for p in projects}
    selected_proj_id = st.selectbox("Select Project", options=list(project_options.keys()), format_func=lambda x: project_options[x])
    
    proj = db.query(Project).filter(Project.id == selected_proj_id).first()
    estimations = db.query(HardwareEstimation).filter(HardwareEstimation.project_id == selected_proj_id).all()
    
    if not estimations:
        st.warning("No hardware estimations found for this project.")
        db.close()
        return

    # Layout: left column for Log sheet, right column for bid summary
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📋 Log Sheet Inputs")
        with st.expander("Site & Cost Parameters", expanded=True):
            job_address = st.text_input("Job Site Address", value=proj.job_address or "")
            distance = st.number_input("Distance (Miles)", value=float(proj.distance_miles), min_value=0.0)
            
            w_drywall = st.number_input("Wage Scale Drywall Hanger", value=float(proj.wage_scale_drywall))
            w_carpenter = st.number_input("Wage Scale Carpenter", value=float(proj.wage_scale_carpenter))
            
            gas = st.number_input("Gas Allowance ($ per mile)", value=float(proj.gas_allowance_per_mile))
            hotel = st.number_input("Hotel Allowance (Per Day)", value=float(proj.hotel_allowance_per_day))
            meal = st.number_input("Meal Allowance (Per Day)", value=float(proj.meal_allowance_per_day))
            parking = st.number_input("Parking Allowance (Per Day)", value=float(proj.parking_allowance_per_day))
            tool_mob = st.number_input("Tool / Mobilization Allowance ($)", value=float(proj.tool_mobilization_allowance))
            
            drug = st.checkbox("Drug Testing", value=proj.drug_testing)
            park_req = st.checkbox("Parking Required", value=proj.parking_required)
            outstation = st.checkbox("Outstation Stay", value=proj.outstation_stay)
            leed = st.checkbox("LEED Material", value=proj.leed_material)
            
        with st.expander("Proposal & Client Details"):
            client_name = st.text_input("Client Name", value=proj.client_name or "")
            
            uploaded_logo = st.file_uploader("Upload Client Logo", type=["png", "jpg", "jpeg"])
            client_logo = proj.client_logo_path
            if uploaded_logo is not None:
                import os
                os.makedirs("logos", exist_ok=True)
                logo_path = os.path.join("logos", uploaded_logo.name)
                with open(logo_path, "wb") as f:
                    f.write(uploaded_logo.getbuffer())
                client_logo = logo_path
                st.success(f"Logo uploaded: {uploaded_logo.name}")
            elif client_logo:
                st.info(f"Current logo: {client_logo}")
                
            notes = st.text_area("Proposal Notes", value=proj.proposal_notes or "")
            exclusions = st.text_area("Exclusions", value=proj.proposal_exclusions or "")
            limitations = st.text_area("Limitations", value=proj.proposal_limitations or "")
            clarifications = st.text_area("Clarifications", value=proj.proposal_clarifications or "")
            
            
        with st.expander("Margins & Markups"):
            burden = st.number_input("Labor Burden %", value=float(proj.labor_burden_pct))
            overhead = st.number_input("Overhead %", value=float(proj.overhead_pct))
            profit = st.number_input("Profit / Labor Markup %", value=float(proj.profit_markup_pct))
            mat_markup = st.number_input("Material Markup %", value=float(proj.material_markup_pct))
            tax = st.number_input("Sales Tax %", value=float(proj.sales_tax_pct))
            tax_equip = st.checkbox("Apply Sales Tax to Equipment", value=proj.apply_tax_to_equipment)

        if st.button("Update Project Context"):
            proj.job_address = job_address
            proj.distance_miles = distance
            proj.wage_scale_drywall = w_drywall
            proj.wage_scale_carpenter = w_carpenter
            proj.gas_allowance_per_mile = gas
            proj.hotel_allowance_per_day = hotel
            proj.meal_allowance_per_day = meal
            proj.parking_allowance_per_day = parking
            proj.tool_mobilization_allowance = tool_mob
            proj.drug_testing = drug
            proj.parking_required = park_req
            proj.outstation_stay = outstation
            proj.leed_material = leed
            proj.labor_burden_pct = burden
            proj.overhead_pct = overhead
            proj.profit_markup_pct = profit
            proj.material_markup_pct = mat_markup
            proj.sales_tax_pct = tax
            proj.apply_tax_to_equipment = tax_equip
            proj.client_name = client_name
            proj.client_logo_path = client_logo
            proj.proposal_notes = notes
            proj.proposal_exclusions = exclusions
            proj.proposal_limitations = limitations
            proj.proposal_clarifications = clarifications
            db.commit()
            st.success("Project settings saved!")
            st.rerun()

    # Calculate Bid
    bid_results = calculate_bid(proj, estimations)
    
    with col2:
        st.markdown("#### 💰 Bid Summary")
        st.metric("Total Labor Bid", f"${bid_results['total_labor_bid']:,.2f}", f"{bid_results['total_man_hours']} hrs (inc. Off-load: ${bid_results.get('offload_cost', 0):,.2f})")
        st.metric("Total Material Bid", f"${bid_results['total_material_bid']:,.2f}")
        st.metric("Total Doors and Hardware - Base Bid", f"${bid_results['total_bid']:,.2f}", delta_color="off")
        
        with st.expander("Detailed Breakdown"):
            st.json(bid_results)
            
        st.markdown("#### 📄 Generate Proposal")
        if st.button("Download Split Proposals (Excel)", type="primary"):
            from proposal_export import generate_proposals_excel
            excel_bytes = generate_proposals_excel(proj, estimations, bid_results)
            st.download_button(
                label="⬇️ Download Proposals.xlsx",
                data=excel_bytes,
                file_name=f"Proposal_{proj.id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    st.divider()
    
    st.markdown("#### ⚙️ Hardware Components (Bill of Materials)")
    
    # Prepare Data Editor
    df_data = []
    for est in estimations:
        master_desc = est.master_component.description if est.master_component else "Not Mapped"
        def_time = est.master_component.install_time_mins if est.master_component else 0.0
        def_price = est.master_component.default_unit_price if est.master_component else 0.0
        
        eff_time = est.override_install_time_mins if est.override_install_time_mins is not None else def_time
        eff_price = est.override_unit_price if est.override_unit_price is not None else def_price
        
        df_data.append({
            "Estimation ID": est.id,
            "Hardware Set": est.hardware_set_id,
            "Extracted Description": est.extracted_description,
            "Total Qty": est.total_qty_project,
            "Master Mapping": master_desc,
            "Install Time (Mins)": eff_time,
            "Unit Price ($)": eff_price
        })
        
    df_est = pd.DataFrame(df_data)
    
    # Configure columns
    column_config = {
        "Estimation ID": st.column_config.NumberColumn(disabled=True),
        "Hardware Set": st.column_config.TextColumn(disabled=True),
        "Extracted Description": st.column_config.TextColumn(disabled=True),
        "Total Qty": st.column_config.NumberColumn(disabled=True),
        "Master Mapping": st.column_config.TextColumn(disabled=True),
        "Install Time (Mins)": st.column_config.NumberColumn(help="Override default time"),
        "Unit Price ($)": st.column_config.NumberColumn(help="Override default price")
    }
    
    edited_df = st.data_editor(df_est, column_config=column_config, use_container_width=True, hide_index=True)
    
    if st.button("💾 Save Grid Overrides"):
        for _, row in edited_df.iterrows():
            est_id = row["Estimation ID"]
            est = db.query(HardwareEstimation).filter(HardwareEstimation.id == est_id).first()
            if est:
                # Compare against defaults, if different save as override
                def_time = est.master_component.install_time_mins if est.master_component else 0.0
                def_price = est.master_component.default_unit_price if est.master_component else 0.0
                
                new_time = float(row["Install Time (Mins)"])
                new_price = float(row["Unit Price ($)"])
                
                est.override_install_time_mins = new_time if new_time != def_time else None
                est.override_unit_price = new_price if new_price != def_price else None
                
        db.commit()
        st.success("Overrides saved!")
        st.rerun()

    db.close()
