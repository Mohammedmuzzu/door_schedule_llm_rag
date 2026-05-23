def calculate_bid(project, estimations):
    """
    Calculate the total labor and material bid for a project based on its estimations
    and cost parameters.
    
    Args:
        project (models.Project): The project containing cost parameters.
        estimations (List[models.HardwareEstimation]): The list of hardware estimations for the project.
        
    Returns:
        dict: A dictionary containing the detailed breakdown of costs.
    """
    total_man_mins = 0.0
    total_material_cost = 0.0
    
    for est in estimations:
        # Determine install time (override > master > 0)
        install_time = est.override_install_time_mins
        if install_time is None:
            install_time = est.master_component.install_time_mins if est.master_component else 0.0
            
        # Determine unit price (override > master > 0)
        unit_price = est.override_unit_price
        if unit_price is None:
            unit_price = est.master_component.default_unit_price if est.master_component else 0.0
            
        # Add to totals
        total_man_mins += (est.total_qty_project * install_time)
        total_material_cost += (est.total_qty_project * unit_price)

    # Ensure safe fallbacks if DB fields are None
    wage_carpenter = project.wage_scale_carpenter or 0.0
    dist = project.distance_miles or 0.0
    gas_allow_mile = project.gas_allowance_per_mile or 0.0
    hotel_allow_day = project.hotel_allowance_per_day or 0.0
    meal_allow_day = project.meal_allowance_per_day or 0.0
    parking_allow_day = project.parking_allowance_per_day or 0.0
    tool_allowance = project.tool_mobilization_allowance or 0.0
    burden_pct = project.labor_burden_pct or 0.0
    oh_pct = project.overhead_pct or 0.0
    profit_pct = project.profit_markup_pct or 0.0
    mat_pct = project.material_markup_pct or 0.0
    tax_pct = project.sales_tax_pct or 0.0

    # 1. Base Labor Cost
    total_man_hours = total_man_mins / 60.0
    base_labor_cost = total_man_hours * wage_carpenter  # Assuming carpenter for hardware by default
    
    # 2. Allowances
    # Gas Allowance is applied if distance > 40
    gas_allowance = (dist * gas_allow_mile) if dist > 40 else 0.0
    hotel_allowance = hotel_allow_day if project.outstation_stay else 0.0
    meal_allowance = meal_allow_day if project.outstation_stay else 0.0
    parking_allowance = parking_allow_day if project.parking_required else 0.0
    drug_testing_fee = 150.0 if project.drug_testing else 0.0 # Example flat fee
    
    total_allowances = gas_allowance + hotel_allowance + meal_allowance + parking_allowance + drug_testing_fee
    
    subtotal_labor = base_labor_cost + total_allowances
    
    # 3. Labor Margins (Burden, Overhead, Markup)
    labor_burden = subtotal_labor * (burden_pct / 100.0)
    overhead = (subtotal_labor + labor_burden) * (oh_pct / 100.0)
    labor_markup = (subtotal_labor + labor_burden + overhead) * (profit_pct / 100.0)
    
    preliminary_labor_bid = subtotal_labor + labor_burden + overhead + labor_markup
    
    # 4. Off-load Equipment & Mobilization Costs
    eff_cost_per_hour = (preliminary_labor_bid / total_man_hours) if total_man_hours > 0 else wage_carpenter
    offload_mins_level_1 = (project.doors_level_1 or 0) * 25
    offload_mins_above_1 = (project.doors_above_level_1 or 0) * 35
    offload_labor_cost = ((offload_mins_level_1 + offload_mins_above_1) / 60.0) * eff_cost_per_hour
    
    total_equipment_mobilization = offload_labor_cost + tool_allowance
    
    equipment_tax = total_equipment_mobilization * (tax_pct / 100.0) if project.apply_tax_to_equipment else 0.0
    
    total_labor_bid = preliminary_labor_bid + total_equipment_mobilization + equipment_tax
    
    # 5. Material Margins
    material_markup = total_material_cost * (mat_pct / 100.0)
    subtotal_material = total_material_cost + material_markup
    sales_tax = subtotal_material * (tax_pct / 100.0)
    
    total_material_bid = subtotal_material + sales_tax
    
    # 5. Final Bid
    total_bid = total_labor_bid + total_material_bid
    
    return {
        "total_man_hours": round(total_man_hours, 2),
        "base_labor_cost": round(base_labor_cost, 2),
        "allowances": round(total_allowances, 2),
        "labor_burden": round(labor_burden, 2),
        "overhead": round(overhead, 2),
        "labor_markup": round(labor_markup, 2),
        "offload_cost": round(total_equipment_mobilization, 2),
        "equipment_tax": round(equipment_tax, 2),
        "total_labor_bid": round(total_labor_bid, 2),
        
        "raw_material_cost": round(total_material_cost, 2),
        "material_markup": round(material_markup, 2),
        "sales_tax": round(sales_tax, 2),
        "total_material_bid": round(total_material_bid, 2),
        
        "total_bid": round(total_bid, 2)
    }
