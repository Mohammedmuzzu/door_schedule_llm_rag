from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True) # project_id
    name = Column(String, nullable=True)
    job_address = Column(String, nullable=True)
    distance_miles = Column(Float, default=0.0)
    
    # Proposal Details
    client_name = Column(String, nullable=True)
    client_logo_path = Column(String, nullable=True)
    proposal_notes = Column(String, nullable=True)
    proposal_exclusions = Column(String, nullable=True)
    proposal_limitations = Column(String, nullable=True)
    proposal_clarifications = Column(String, nullable=True)
    
    # Off-load Door Counts
    doors_level_1 = Column(Integer, default=0)
    doors_above_level_1 = Column(Integer, default=0)
    
    # Cost Parameters
    wage_scale_drywall = Column(Float, default=19.90)
    wage_scale_carpenter = Column(Float, default=21.48)
    
    # Allowances & Mobilization
    gas_allowance_per_mile = Column(Float, default=0.55)
    hotel_allowance_per_day = Column(Float, default=0.0)
    meal_allowance_per_day = Column(Float, default=0.0)
    parking_allowance_per_day = Column(Float, default=0.0)
    tool_mobilization_allowance = Column(Float, default=0.0)
    
    # Flags
    drug_testing = Column(Boolean, default=True)
    parking_required = Column(Boolean, default=False)
    outstation_stay = Column(Boolean, default=False)
    leed_material = Column(Boolean, default=False)
    apply_tax_to_equipment = Column(Boolean, default=True)

    # Margins
    labor_burden_pct = Column(Float, default=25.0)
    overhead_pct = Column(Float, default=32.0)
    profit_markup_pct = Column(Float, default=25.0)
    sales_tax_pct = Column(Float, default=8.25)
    material_markup_pct = Column(Float, default=15.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    estimations = relationship("HardwareEstimation", back_populates="project")

class MasterComponent(Base):
    __tablename__ = "master_components"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    description = Column(String, unique=True, index=True) # E.g., "NRP / Butt or Anchor Hinge"
    category = Column(String, nullable=True) # e.g., "Hardware", "Wood"
    install_time_mins = Column(Float, default=0.0)
    default_unit_price = Column(Float, default=0.0)

class HardwareEstimation(Base):
    __tablename__ = "hardware_estimations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"))
    hardware_set_id = Column(String)
    extracted_description = Column(String)
    catalog_number = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    finish_code = Column(String, nullable=True)
    
    # Aggregated quantities from Milestone 1
    qty_per_set = Column(Integer, default=1)
    total_doors = Column(Integer, default=1)
    total_qty_project = Column(Integer, default=1)
    
    # Milestone 2 & 3 mapped data
    mapped_master_id = Column(Integer, ForeignKey("master_components.id"), nullable=True)
    
    # Overrides (if user wants to override default master values)
    override_unit_price = Column(Float, nullable=True)
    override_install_time_mins = Column(Float, nullable=True)

    project = relationship("Project", back_populates="estimations")
    master_component = relationship("MasterComponent")
