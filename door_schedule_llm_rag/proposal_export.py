import io
import pandas as pd
from datetime import datetime

def generate_proposals_excel(proj, estimations, bid_results):
    """
    Generates a split Excel proposal based on presence of installation minutes vs unit prices.
    Returns bytes of the Excel file.
    """
    output = io.BytesIO()
    
    labor_data = []
    material_data = []
    
    for est in estimations:
        def_time = est.master_component.install_time_mins if est.master_component else 0.0
        def_price = est.master_component.default_unit_price if est.master_component else 0.0
        
        eff_time = est.override_install_time_mins if est.override_install_time_mins is not None else def_time
        eff_price = est.override_unit_price if est.override_unit_price is not None else def_price
        
        # Route to Labor Proposal if it takes time
        if eff_time > 0:
            labor_data.append({
                "Hardware Set": est.hardware_set_id,
                "Description": est.extracted_description,
                "Total Qty": est.total_qty_project,
                "Unit Time (Mins)": eff_time,
                "Total Time (Hrs)": round((eff_time * est.total_qty_project) / 60.0, 2)
            })
            
        # Route to Supply Proposal if it has a material cost
        if eff_price > 0:
            material_data.append({
                "Hardware Set": est.hardware_set_id,
                "Component Description": est.extracted_description,
                "Catalog No.": est.catalog_number or "",
                "Finish": est.finish_code or "",
                "Manufacturer": est.manufacturer or "",
                "Total Qty": est.total_qty_project,
                "Unit Price (Input)": eff_price,
                "Total Cost": round(eff_price * est.total_qty_project, 2)
            })

    # Add Off-load to labor proposal explicitly
    if bid_results.get("offload_cost", 0) > 0:
        labor_data.append({
            "Hardware Set": "OFF-LOAD",
            "Description": f"Equipment off-load (Lvl 1 doors: {proj.doors_level_1}, Above Lvl 1 doors: {proj.doors_above_level_1})",
            "Total Qty": 1,
            "Unit Time (Mins)": "-",
            "Total Time (Hrs)": "-"
        })

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Cover / Summary Sheet
        summary_data = {
            "Field": [
                "Client Name", 
                "Date", 
                "Project Name", 
                "Job Address", 
                "Notes", 
                "Exclusions", 
                "Limitations",
                "Clarifications",
                "", 
                "Total Labor Bid (Inc. Offload & Margins)", 
                "Total Material Bid (Inc. Taxes & Margins)", 
                "Combined Total Bid"
            ],
            "Value": [
                proj.client_name or "",
                datetime.now().strftime("%Y-%m-%d"),
                proj.name or "",
                proj.job_address or "",
                proj.proposal_notes or "",
                proj.proposal_exclusions or "",
                proj.proposal_limitations or "",
                proj.proposal_clarifications or "",
                "",
                f"${bid_results['total_labor_bid']:,.2f}",
                f"${bid_results['total_material_bid']:,.2f}",
                f"${bid_results['total_bid']:,.2f}"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Proposal Summary", index=False)
        
        if proj.client_logo_path:
            import os
            if os.path.exists(proj.client_logo_path):
                from openpyxl.drawing.image import Image
                ws = writer.sheets["Proposal Summary"]
                try:
                    img = Image(proj.client_logo_path)
                    img.width, img.height = 150, 150
                    ws.add_image(img, "D2")
                except Exception as e:
                    pass
        
        
        # Labor Tab
        if labor_data:
            pd.DataFrame(labor_data).to_excel(writer, sheet_name="Labor Proposal", index=False)
        else:
            pd.DataFrame([{"Message": "No labor minutes mapped"}]).to_excel(writer, sheet_name="Labor Proposal", index=False)
            
        # Supply Tab
        if material_data:
            pd.DataFrame(material_data).to_excel(writer, sheet_name="Supply Proposal", index=False)
        else:
            pd.DataFrame([{"Message": "No hardware prices mapped"}]).to_excel(writer, sheet_name="Supply Proposal", index=False)

    return output.getvalue()
