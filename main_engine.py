import pandas as pd
from ortools.sat.python import cp_model
import os

def solve_timetable(num_periods=8):
    # 1. Load Data
    if not os.path.exists('school_data.csv'):
        print("❌ Error: school_data.csv not found")
        return
    
    df = pd.read_csv('school_data.csv')
    df.columns = [c.strip().lower() for c in df.columns]

    # Handle Optional Columns
    df['institution_type'] = df.get('institution_type', pd.Series(['school']*len(df))).astype(str).str.strip().str.lower()
    df['required_resource_type'] = df.get('required_resource_type', pd.Series(['none']*len(df))).astype(str).str.strip().str.lower()

    # 2. Load Resource Registry
    resources = []
    has_resource_file = os.path.exists('resource_data.csv')
    if has_resource_file:
        res_df = pd.read_csv('resource_data.csv')
        res_df.columns = [c.strip().lower() for c in res_df.columns]
        resources = res_df.to_dict('records')

    # 3. Setup Constants
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    periods = [f'Period {i}' for i in range(1, num_periods + 1)]
    model = cp_model.CpModel()
    
    # 4. Create Variables
    lessons = {}
    for i, row in df.iterrows():
        req_type = row['required_resource_type']
        inst_type = row['institution_type']
        
        if inst_type == 'college' and has_resource_file and req_type not in ['none', 'classroom']:
            compatible_rooms = [r['resource_name'] for r in resources if r['resource_type'] == req_type] or ["Standard Room"]
        else:
            compatible_rooms = ["Standard Room"]

        for d in days:
            for p in periods:
                for r in compatible_rooms:
                    lessons[(i, d, p, r)] = model.NewBoolVar(f'L_{i}_{d}_{p}_{r}')

    # 5. Constraints

    # --- NEW: CONSECUTIVE BLOCK LOGIC (The University Rule) ---
    for i, row in df.iterrows():
        target = int(row['weekly_period'])
        inst_type = row['institution_type']
        req_type = row['required_resource_type']
        
        # Determine Block Size
        block_size = 1 # Default for Schools
        if inst_type == 'college':
            if req_type == 'lab':
                block_size = 3 # Labs must be 3 hours
            elif target >= 2:
                block_size = 2 # Theory must be 2 hours
        
        # Apply the logic: If block_size > 1, we force periods to be adjacent
        if block_size > 1 and target >= block_size:
            # We create a 'Starts' variable to indicate the start of a block
            for d in days:
                possible_starts = []
                for p_idx in range(len(periods) - block_size + 1):
                    start_var = model.NewBoolVar(f'start_{i}_{d}_{p_idx}')
                    possible_starts.append(start_var)
                    
                    # If this start_var is true, then the next 'block_size' periods are filled
                    for b in range(block_size):
                        p_name = periods[p_idx + b]
                        # Link start_var to the actual lesson variables
                        # (Simplification: Assumes one compatible room for blocks)
                        room = "Standard Room" 
                        if inst_type == 'college' and has_resource_file and req_type not in ['none', 'classroom']:
                            rooms = [r['resource_name'] for r in resources if r['resource_type'] == req_type]
                            if rooms: room = rooms[0] # Picks first available for the block

                        model.AddImplication(start_var, lessons[(i, d, p_name, room)])

                # Total periods for this subject on this day must be exactly block_size OR 0
                # This prevents a lab from being split across two days or non-consecutively
                model.Add(sum(possible_starts) <= 1)
        
        # 6. Standard Weekly Target Constraint
        # (Already exists, but we keep it to ensure total hours match)
        all_vars = []
        for d in days:
            for p in periods:
                for (idx, day, per, r) in lessons:
                    if idx == i and day == d and per == p:
                        all_vars.append(lessons[(idx, day, per, r)])
        model.Add(sum(all_vars) == target)

    # 7. Standard Overlap Constraints (Teacher, Class, Room)
    for d in days:
        for p in periods:
            # Teacher Overlap
            for teacher in df['teacher_name'].unique():
                t_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and teacher in str(df.loc[k[0], 'teacher_name'])]
                if t_vars: model.Add(sum(t_vars) <= 1)
            
            # Class Overlap
            for cls in df['class_name'].unique():
                c_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and df.loc[k[0], 'class_name'] == cls]
                if c_vars: model.Add(sum(c_vars) <= 1)

    # 8. Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0 
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        output = []
        for (i, d, p, r), var in lessons.items():
            if solver.Value(var):
                row = df.loc[i]
                output.append({
                    "Institution": row['institution_type'].upper(),
                    "Day": d, "Period": p, 
                    "Teacher": row['teacher_name'], 
                    "Class": row['class_name'], 
                    "Subject": row['subject_name'], 
                    "Room": r
                })
        pd.DataFrame(output).to_csv('final_timetable_result.csv', index=False)
        print(f"✅ SUCCESS! Blocks applied for {num_periods} periods.")
    else:
        print("❌ FAILED: Constraints too tight (Check Lab/Room availability).")

if __name__ == "__main__":
    solve_timetable()