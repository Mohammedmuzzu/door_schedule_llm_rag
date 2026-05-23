import pandas as pd
import glob, os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

out_dir = 'scratch_qa_full'
all_doors = []
all_hw = []

for cd in sorted(glob.glob(os.path.join(out_dir, 'chunk_*'))):
    door_csv = os.path.join(cd, 'door_schedule_llm.csv')
    hw_csv = os.path.join(cd, 'hardware_components_llm.csv')
    if os.path.exists(door_csv):
        all_doors.append(pd.read_csv(door_csv))
    if os.path.exists(hw_csv):
        all_hw.append(pd.read_csv(hw_csv))

df_doors = pd.concat(all_doors, ignore_index=True) if all_doors else pd.DataFrame()
df_hw = pd.concat(all_hw, ignore_index=True) if all_hw else pd.DataFrame()

# Apply Ghost Door Filter
if not df_doors.empty:
    cols_to_check = ['door_width', 'door_height', 'door_thickness', 'door_material', 'door_type']
    existing_cols = [c for c in cols_to_check if c in df_doors.columns]
    if existing_cols:
        valid_mask = df_doors[existing_cols].notna().any(axis=1) | (df_doors["door_number"].astype(str).str.strip() == "")
        df_doors = df_doors[valid_mask].reset_index(drop=True)

print('='*60)
print('FULL BENCHMARK QA REPORT (140 PDFs) - POST-IMPROVEMENTS')
print('='*60)

total_pdfs = len(set(list(df_doors['source_file'].unique()) + list(df_hw['source_file'].unique())))
total_projects = len(set(list(df_doors['project_id'].unique()) + list(df_hw['project_id'].unique())))
print(f'\nTotal Unique Source Files: {total_pdfs}')
print(f'Total Unique Projects: {total_projects}')
print(f'Total Doors Extracted: {len(df_doors)}')
print(f'Total HW Components Extracted: {len(df_hw)}')

print('\n--- DOOR DATA QUALITY ---')
if not df_doors.empty:
    no_number = df_doors['door_number'].isna().sum()
    no_width = df_doors['door_width'].isna().sum() if 'door_width' in df_doors.columns else 0
    no_height = df_doors['door_height'].isna().sum() if 'door_height' in df_doors.columns else 0
    no_hw_set = df_doors['hardware_set'].isna().sum() if 'hardware_set' in df_doors.columns else 0
    no_type = df_doors['door_type'].isna().sum() if 'door_type' in df_doors.columns else 0
    
    print(f'  Missing door_number: {no_number} / {len(df_doors)} ({no_number/len(df_doors)*100:.1f}%)')
    print(f'  Missing door_width:  {no_width} / {len(df_doors)} ({no_width/len(df_doors)*100:.1f}%)')
    print(f'  Missing door_height: {no_height} / {len(df_doors)} ({no_height/len(df_doors)*100:.1f}%)')
    print(f'  Missing hardware_set:{no_hw_set} / {len(df_doors)} ({no_hw_set/len(df_doors)*100:.1f}%)')

print('\n--- OVERALL CORE COMPLETENESS SCORE ---')
total = len(df_doors)
core_complete = df_doors[
    df_doors['door_number'].notna() & 
    df_doors['door_width'].notna() & 
    df_doors['door_height'].notna() &
    df_doors['hardware_set'].notna()
] if all(c in df_doors.columns for c in ['door_number','door_width','door_height','hardware_set']) else pd.DataFrame()

print(f'Doors with ALL 4 core fields (number+width+height+hw_set): {len(core_complete)} / {total} ({len(core_complete)/total*100:.1f}%)')

# Compare with previous baseline
prev_core = 52.4
improvement = (len(core_complete)/total*100) - prev_core
print(f'\nImprovement from baseline: +{improvement:.1f}%')

print('\n=== PROJECTS WITH 0% HARDWARE_SET LINKAGE (Previously 8) ===')
zero_hw_set = df_doors.groupby('project_id').apply(lambda g: g['hardware_set'].isna().all()).reset_index(name='all_missing')
zero_hw_set = zero_hw_set[zero_hw_set['all_missing']]
print(f'Remaining projects with 0% linkage: {len(zero_hw_set)}')
for _, row in zero_hw_set.iterrows():
    print(f'  {row["project_id"]}')

# Duplicate detection check
print('\n=== DUPLICATE DOOR DETECTION (Previously 10 groups) ===')
dupes = df_doors[df_doors.duplicated(subset=['project_id','door_number'], keep=False)]
if not dupes.empty:
    dupe_groups = dupes.groupby(['project_id','door_number']).size().reset_index(name='count')
    dupe_groups = dupe_groups[dupe_groups['count'] > 1]
    print(f'Remaining Duplicate door entries: {len(dupe_groups)} groups')
else:
    print('No duplicate doors found! Deduplication fix successful.')
