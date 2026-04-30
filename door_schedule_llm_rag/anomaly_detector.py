import os
import glob
import pandas as pd

out_dir = 'c:\\Users\\muzaf\\my_lab\\sushmita_proj\\door_schedule_llm_rag\\scratch_qa_full'
chunk_dirs = glob.glob(os.path.join(out_dir, 'chunk_*'))

all_doors = []
all_hw = []

for cd in chunk_dirs:
    door_csv = os.path.join(cd, 'door_schedule_llm.csv')
    hw_csv = os.path.join(cd, 'hardware_components_llm.csv')
    
    if os.path.exists(door_csv):
        all_doors.append(pd.read_csv(door_csv))
    if os.path.exists(hw_csv):
        all_hw.append(pd.read_csv(hw_csv))

if not all_doors:
    print("No door data found yet.")
    exit(0)

df_doors = pd.concat(all_doors, ignore_index=True)
df_hw = pd.concat(all_hw, ignore_index=True)

print(f"Total Doors Extracted: {len(df_doors)}")
print(f"Total HW Extracted: {len(df_hw)}\\n")

print("--- ANOMALY REPORT ---")

# 1. Zero Extractions (0 doors AND 0 hw)
all_files = set(df_doors['source_file'].unique()).union(set(df_hw['source_file'].unique()))
print(f"Total Files Processed: {len(all_files)}")

# 2. Blank dimensions with hardware (Potential hallucination)
if 'door_width' in df_doors.columns and 'door_height' in df_doors.columns:
    blank_doors = df_doors[df_doors['door_width'].isna() & df_doors['door_height'].isna()]
    if not blank_doors.empty:
        print(f"\\nWARNING: Found {len(blank_doors)} doors with no dimensions.")
        print(blank_doors[['source_file', 'door_number', 'hardware_set']].head())

# 3. HW Hallucination check (Empty Table hallucinated 10+ items)
hw_counts = df_hw.groupby(['source_file', 'hardware_set_id']).size().reset_index(name='count')
hallucinated = hw_counts[hw_counts['count'] >= 15]
if not hallucinated.empty:
    print(f"\\nWARNING: Found {len(hallucinated)} hardware sets with 15+ items (possible hallucination for empty tables).")
    print(hallucinated)

print("\\nAnalysis Complete.")
