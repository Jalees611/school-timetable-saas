import pandas as pd
from ortools.sat.python import cp_model
import os

def solve_timetable():
    # 1. Load Data
    if not os.path.exists('school_data.csv'):
        print("❌ Error: school_data.csv not found")
        return
    
    df = pd.read_csv('school_data.csv')
    df.columns = [c.strip().lower() for c in df.columns]

    # Handle Optional Columns (Institution Type and Resource Type)
    if 'institution_type' not in df.columns:
        # Default to School if column is missing
        df['institution_type'] = 'school'
    else:
        df['institution_type'] = df['institution_type'].astype(str).str.strip().str.lower()

    if 'required_resource_type' not in df.columns:
        df['required_resource_type'] = 'none'
    else:
        df['required_resource_type'] = df['required_resource_type'].astype(str).str.strip().str.lower()

    # 2. Load Resource Registry (Mandatory for Colleges, Optional for Schools)
    resources = []
    has_resource_file = os.path.exists('resource_data.csv')
    
    if has_resource_file:
        res_df = pd.read_csv('resource_data.csv')
        res_df.columns = [c.strip().lower() for c in res_df.columns]
        res_df['resource_type'] = res_df['resource_type'].astype(str).str.strip().str.lower()
        res_df['resource_name'] = res_df['resource_name'].astype(str).str.strip()
        resources = res_df.to_dict('records')
        print("📂 Resource file detected.")

    # 3. Setup Constants
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    periods = [f'Period {i}' for i in range(1, 9)]
    model = cp_model.CpModel()
    
    # 4. Create Variables
    lessons = {}
    for i, row in df.iterrows():
        req_type = row['required_resource_type']
        inst_type = row['institution_type']
        
        # Logic: Only find specific rooms if it's a College AND a resource type is specified
        if inst_type == 'college' and has_resource_file and req_type != 'none' and req_type != 'classroom':
            compatible_rooms = [r['resource_name'] for r in resources if r['resource_type'] == req_type]
            if not compatible_rooms:
                print(f"⚠️ Warning: No rooms of type '{req_type}' found for {row['subject_name']}")
                compatible_rooms = ["Unassigned Room"]
        else:
            # Schools or general College lectures get a virtual "Standard" room
            compatible_rooms = ["Standard Room"]

        for d in days:
            for p in periods:
                for r in compatible_rooms:
                    lessons[(i, d, p, r)] = model.NewBoolVar(f'L_{i}_{d}_{p}_{r}')

    # 5. Constraints

    # Weekly Period Target
    for i, row in df.iterrows():
        target = int(row['weekly_period'])
        req_type = row['required_resource_type']
        inst_type = row['institution_type']
        
        if inst_type == 'college' and has_resource_file and req_type != 'none' and req_type != 'classroom':
            rooms = [r['resource_name'] for r in resources if r['resource_type'] == req_type] or ["Unassigned Room"]
        else:
            rooms = ["Standard Room"]
            
        model.Add(sum(lessons[(i, d, p, r)] for d in days for p in periods for r in rooms) == target)

    # Teacher & Class Overlap Constraints (Always enforced)
    for d in days:
        for p in periods:
            # One lesson per Class
            for class_name in df['class_name'].unique():
                relevant_indices = df[df['class_name'] == class_name].index
                class_vars = []
                for i in relevant_indices:
                    # Collect all possible room assignments for this index
                    # Note: We must check which rooms were actually created for this index
                    for (idx, day, per, r) in lessons:
                        if idx == i and day == d and per == p:
                            class_vars.append(lessons[(idx, day, per, r)])
                if class_vars:
                    model.Add(sum(class_vars) <= 1)

            # One lesson per Teacher
            for teacher in df['teacher_name'].unique():
                relevant_indices = [idx for idx, row in df.iterrows() if teacher in str(row['teacher_name']).split('/')]
                teacher_vars = []
                for i in relevant_indices:
                    for (idx, day, per, r) in lessons:
                        if idx == i and day == d and per == p:
                            teacher_vars.append(lessons[(idx, day, per, r)])
                if teacher_vars:
                    model.Add(sum(teacher_vars) <= 1)

    # Room Collision Constraint (Only for Colleges + Labs/Halls)
    if has_resource_file:
        for d in days:
            for p in periods:
                for res in resources:
                    if res['resource_type'] == 'classroom': continue # Schools skip this
                    
                    r_name = res['resource_name']
                    r_type = res['resource_type']
                    room_vars = []
                    for (idx, day, per, room) in lessons:
                        if day == d and per == p and room == r_name:
                            room_vars.append(lessons[(idx, day, per, room)])
                    if room_vars:
                        model.Add(sum(room_vars) <= 1)

    # 6. Solve
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
        print(f"✅ SUCCESS! Timetable generated.")
    else:
        print("❌ FAILED: Potential causes: Teacher overload or Lab capacity reached.")

if __name__ == "__main__":
    solve_timetable()