import pandas as pd
from db import SessionLocal
from models import Project, HardwareEstimation, MasterComponent
from sqlalchemy.orm import Session

def save_estimations_to_db(milestone1_df: pd.DataFrame, df_doors_out: pd.DataFrame = None):
    """
    Saves the Milestone 1 aggregation dataframe to the database.
    Handles multiple projects in the dataframe.
    """
    if milestone1_df.empty:
        return

    db: Session = SessionLocal()
    try:
        # Group by project to handle them separately
        for project_id, group_df in milestone1_df.groupby("project_id"):
            pid_str = str(project_id)
            # Create project if not exists
            proj = db.query(Project).filter(Project.id == pid_str).first()
            # Calculate off-load doors
            level_1_count = 0
            above_level_1_count = 0
            
            if df_doors_out is not None and not df_doors_out.empty:
                proj_doors = df_doors_out[df_doors_out["project_id"] == project_id]
                for _, row in proj_doors.iterrows():
                    level = str(row.get("level_area", "")).lower()
                    # Simple heuristic for level 1
                    if "1" in level and "11" not in level and "12" not in level and "10" not in level:
                        level_1_count += 1
                    elif level and level != "nan":
                        above_level_1_count += 1

            if not proj:
                proj = Project(
                    id=pid_str, 
                    name=f"Project {pid_str}",
                    doors_level_1=level_1_count,
                    doors_above_level_1=above_level_1_count
                )
                db.add(proj)
            else:
                proj.doors_level_1 = level_1_count
                proj.doors_above_level_1 = above_level_1_count
                
            db.commit()

            # Delete existing estimations for this project to avoid duplicates on re-run
            db.query(HardwareEstimation).filter(HardwareEstimation.project_id == pid_str).delete()
            
            # Load all master components for quick mapping
            masters = db.query(MasterComponent).all()
            # Create a simple lookup dict by lowercase description
            master_lookup = {m.description.lower().strip(): m.id for m in masters if m.description}

            new_estimations = []
            for _, row in group_df.iterrows():
                desc = str(row.get("description", "")).strip()
                # Try to find a master component mapping
                mapped_id = master_lookup.get(desc.lower())
                
                est = HardwareEstimation(
                    project_id=pid_str,
                    hardware_set_id=str(row.get("hardware_set_id", "")),
                    extracted_description=desc,
                    catalog_number=str(row.get("catalog_number", "")) if pd.notna(row.get("catalog_number")) else None,
                    manufacturer=str(row.get("manufacturer_code", "")) if pd.notna(row.get("manufacturer_code")) else None,
                    finish_code=str(row.get("finish_code", "")) if pd.notna(row.get("finish_code")) else None,
                    qty_per_set=int(row.get("qty_per_set", 1)),
                    total_doors=int(row.get("total_doors", 1)),
                    total_qty_project=int(row.get("total_qty_project", 1)),
                    mapped_master_id=mapped_id
                )
                new_estimations.append(est)

            db.add_all(new_estimations)
        db.commit()
    finally:
        db.close()
