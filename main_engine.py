import pandas as pd
from ortools.sat.python import cp_model
import time
import os
import sys

def run_parallel_engine(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    df = df.rename(columns={'subject_name': 'subject', 'weekly_period': 'periods_per_week'})
    
    model = cp_model.CpModel()
    days, periods_per_day = 5, 8
    day_list, period_list = range(1, days + 1), range(1, periods_per_day + 1)
    
    # 1. Identify all unique individual teachers (handles shared rows like Humaira/Haseeb)
    all_teachers = set()
    for t_string in df['teacher_name'].unique():
        for name in str(t_string).split('/'):
            all_teachers.add(name.strip())
    
    assignments = df.to_dict('records')
    schedule = {}
    for i in range(len(assignments)):
        for d in day_list:
            for p in period_list:
                schedule[(i, d, p)] = model.NewBoolVar(f'idx{i}_d{d}_p{p}')

    # 2. WEEKLY LOAD RULE
    for i, row in enumerate(assignments):
        model.Add(sum(schedule[(i, d, p)] for d in day_list for p in period_list) == int(row['periods_per_week']))

    # 3. UNIVERSAL CONSTRAINTS
    for d in day_list:
        for p in period_list:
            # --- TEACHER RULE: Individual name cannot be in 2 rows at once ---
            for teacher in all_teachers:
                involved_idxs = [i for i, r in enumerate(assignments) if teacher in str(r['teacher_name'])]
                if involved_idxs:
                    model.AddAtMostOne(schedule[(i, d, p)] for i in involved_idxs)

            # --- CLASS RULE: Every slot must have exactly 1 assignment ---
            for c in df['class_name'].unique():
                c_idxs = [i for i, r in enumerate(assignments) if r['class_name'] == c]
                model.Add(sum(schedule[(i, d, p)] for i in c_idxs) == 1)

    # 4. SPREAD RULE (Max 2 periods of the same assignment per day)
    for i in range(len(assignments)):
        for d in day_list:
            model.Add(sum(schedule[(i, d, p)] for p in period_list) <= 2)

    # ==========================================
    # 5. NEW: CUSTOM RESTRICTIONS INJECTION
    # ==========================================
    if os.path.exists("restrictions_data.csv"):
        try:
            res_df = pd.read_csv("restrictions_data.csv")
            # Map text days to your engine's 1-5 integer system
            day_map = {'Mon': 1, 'Tue': 2, 'Wed': 3, 'Thu': 4, 'Fri': 5}
            
            for _, r_row in res_df.iterrows():
                t_rest = str(r_row['teacher_name']).strip()
                d_rest_text = str(r_row['day']).strip()
                p_rest_text = str(r_row['period']).strip()
                r_type = str(r_row['restriction_type']).strip()
                
                # Convert day and period text to integers
                d_val = day_map.get(d_rest_text, -1)
                try:
                    p_val = int(p_rest_text.replace('Period ', '').strip())
                except ValueError:
                    continue # Skip invalid period formatting
                
                if d_val != -1 and 1 <= p_val <= periods_per_day:
                    # Find all assignment indices where this teacher is involved
                    involved_idxs = [i for i, row in enumerate(assignments) if t_rest in str(row['teacher_name'])]
                    
                    if not involved_idxs:
                        continue # Teacher not found in main data, skip
                        
                    if r_type == "Unavailable":
                        # Lock all variables for this teacher at this specific day/time to False (0)
                        for i in involved_idxs:
                            model.Add(schedule[(i, d_val, p_val)] == 0)
                            
                    elif r_type == "Must Teach":
                        # Force exactly one of this teacher's classes to be True (1) at this specific day/time
                        model.Add(sum(schedule[(i, d_val, p_val)] for i in involved_idxs) == 1)
                        
            print("🔒 Successfully applied custom teacher restrictions.")
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to process restrictions: {e}\n")
    # ==========================================

    # 6. SOLVE & OUTPUT
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 180.0
    print(f"🧠 Solving for {len(all_teachers)} teachers and {len(df['class_name'].unique())} classes...")
    status = solver.Solve(model)

    if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
        output = []
        # Mapping for clean output so app.py doesn't have to guess
        output_day_map = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri'}
        
        for d in day_list:
            for p in period_list:
                for i, row in enumerate(assignments):
                    if solver.Value(schedule[(i, d, p)]):
                        output.append({
                            "Day": output_day_map[d], 
                            "Period": f"Period {p}", 
                            "Teacher": row['teacher_name'], 
                            "Class": row['class_name'], 
                            "Subject": row['subject']
                        })
        pd.DataFrame(output).to_csv("final_timetable_result.csv", index=False)
        print("✅ SUCCESS! Timetable generated honoring all rules and restrictions.")
    else:
        print("❌ FAILED: The engine could not find a solution. The restrictions might be too tight (infeasible).")
        sys.exit(1)

if __name__ == "__main__":
    run_parallel_engine('school_data.csv')