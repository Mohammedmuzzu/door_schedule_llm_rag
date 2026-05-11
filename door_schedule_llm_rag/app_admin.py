import streamlit as st
import pandas as pd
from db import SessionLocal
from models import MasterComponent
from sqlalchemy.orm import Session

def render_master_data_manager():
    st.subheader("⚙️ Master Data Manager")
    st.markdown("Upload the **Installation Master Sheet** to map component descriptions to their base labor install times and default unit prices.")
    
    db: Session = SessionLocal()
    
    # Show existing data
    existing = db.query(MasterComponent).all()
    if existing:
        st.write("### Current Master Components")
        df = pd.DataFrame([{
            "ID": m.id,
            "Description": m.description,
            "Category": m.category,
            "Install Time (Mins)": m.install_time_mins,
            "Unit Price ($)": m.default_unit_price
        } for m in existing])
        
        # Make the grid editable
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="master_data_editor")
        
        if st.button("💾 Save Grid Changes"):
            # A more robust sync could be written, but for now we update matching IDs
            for _, row in edited_df.iterrows():
                if pd.notna(row.get("ID")):
                    comp = db.query(MasterComponent).filter(MasterComponent.id == row["ID"]).first()
                    if comp:
                        comp.description = row["Description"]
                        comp.category = row["Category"]
                        comp.install_time_mins = float(row["Install Time (Mins)"]) if pd.notna(row["Install Time (Mins)"]) else 0.0
                        comp.default_unit_price = float(row["Unit Price ($)"]) if pd.notna(row["Unit Price ($)"]) else 0.0
            db.commit()
            st.success("Master data updated successfully!")
            st.rerun()
    else:
        st.info("No master data found. Please upload an Excel sheet.")

    st.divider()

    # Upload new data
    st.write("### Bulk Upload / Seed")
    uploaded_file = st.file_uploader("Upload Master Excel or CSV", type=["xlsx", "csv"])
    if uploaded_file and st.button("Process & Merge to Database"):
        if uploaded_file.name.endswith(".csv"):
            df_upload = pd.read_csv(uploaded_file)
        else:
            df_upload = pd.read_excel(uploaded_file)
            
        # Expected columns (fuzzy match)
        col_desc = next((c for c in df_upload.columns if 'desc' in c.lower()), None)
        col_cat = next((c for c in df_upload.columns if 'cat' in c.lower()), None)
        col_time = next((c for c in df_upload.columns if 'time' in c.lower() or 'min' in c.lower()), None)
        col_price = next((c for c in df_upload.columns if 'price' in c.lower() or 'cost' in c.lower() or 'base rate' in c.lower()), None)
        
        if not col_desc:
            st.error("Could not find a 'Description' column in the uploaded file.")
        else:
            new_count = 0
            for _, row in df_upload.iterrows():
                desc = str(row[col_desc]).strip()
                if not desc or desc.lower() == 'nan':
                    continue
                
                # Check if exists
                comp = db.query(MasterComponent).filter(MasterComponent.description == desc).first()
                if not comp:
                    comp = MasterComponent(description=desc)
                    db.add(comp)
                    new_count += 1
                    
                if col_cat and pd.notna(row[col_cat]):
                    comp.category = str(row[col_cat])
                if col_time and pd.notna(row[col_time]):
                    try: comp.install_time_mins = float(row[col_time])
                    except: pass
                if col_price and pd.notna(row[col_price]):
                    try: comp.default_unit_price = float(row[col_price])
                    except: pass
                    
            db.commit()
            st.success(f"Successfully processed master sheet. Added {new_count} new components and updated existing ones.")
            st.rerun()

    db.close()
