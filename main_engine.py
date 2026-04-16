import pandas as pd
from ortools.sat.python import cp_model
import os

def solve_timetable(num_periods=8, num_working_days=5):
    if not os.path.exists('school_data.csv'): return
    
    # 1. Load Data
    df = pd.read_csv('school_data.csv')
    df.columns = [c.strip().lower() for c in df.columns]
    df['institution_type'] = df.get('institution_type', pd.Series(['school']*len(df))).astype(str).str.lower()
    df['required_resource_type'] = df.get('required_resource_type', pd.Series(['none']*len(df))).astype(str).str.lower()

    restrictions = []
    if os.path.exists('restrictions_data.csv'):
        rest_df = pd.read_csv('restrictions_data.csv')
        rest_df.columns = [c.strip().lower() for c in rest_df.columns]
        restrictions = rest_df.to_dict('records')

    resources = []
    if os.path.exists('resource_data.csv'):
        res_df = pd.read_csv('resource_data.csv')
        res_df.columns = [c.strip().lower() for c in res_df.columns]
        resources = res_df.to_dict('records')

    # DYNAMIC DAYS LIST BASED ON SLIDER
    all_possible_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    days = all_possible_days[:num_working_days]
    periods = [f'Period {i}' for i in range(1, num_periods + 1)]
    
    model = cp_model.CpModel()
    lessons = {}

    # 2. Create Variables with Restrictions
    for i, row in df.iterrows():
        req_type = row['required_resource_type']
        inst_type = row['institution_type']
        teacher_name = str(row['teacher_name']).lower()
        
        rooms = ["Standard Room"]
        if inst_type == 'college' and resources and req_type not in ['none', 'classroom']:
            rooms = [r['resource_name'] for r in resources if r['resource_type'] == req_type] or ["Standard Room"]

        for d in days:
            for p in periods:
                rest_type = None
                for rest in restrictions:
                    if str(rest['teacher_name']).lower() in teacher_name:
                        if str(rest['day']).lower() == d.lower() and str(rest['period']).lower() == p.lower():
                            rest_type = str(rest['restriction_type']).lower()
                            break
                
                for r in rooms:
                    lessons[(i, d, p, r)] = model.NewBoolVar(f'L_{i}_{d}_{p}_{r}')
                    # UNVAILABLE LOGIC
                    if rest_type == "unavailable":
                        model.Add(lessons[(i, d, p, r)] == 0)

    # 3. MUST TEACH LOGIC
    for rest in restrictions:
        if "must teach" in str(rest['restriction_type']).lower():
            r_teacher = str(rest['teacher_name']).lower()
            r_day = str(rest['day'])
            r_period = str(rest['period'])
            
            if r_day in days:
                must_teach_vars = [
                    lessons[k] for k in lessons 
                    if k[1] == r_day and k[2] == r_period and r_teacher in str(df.loc[k[0], 'teacher_name']).lower()
                ]
                if must_teach_vars:
                    model.Add(sum(must_teach_vars) == 1)

    # 4. BLOCK LOGIC & TARGETS
    for i, row in df.iterrows():
        target = int(row['weekly_period'])
        inst_type = row['institution_type']
        req_type = row['required_resource_type']
        
        block_size = 1
        if inst_type == 'college':
            if req_type == 'lab': block_size = 3
            elif target >= 2: block_size = 2
        
        if block_size > 1 and target >= block_size:
            for d in days:
                starts = []
                for p_idx in range(len(periods) - block_size + 1):
                    s_var = model.NewBoolVar(f's_{i}_{d}_{p_idx}')
                    starts.append(s_var)
                    for b in range(block_size):
                        p_name = periods[p_idx + b]
                        room = "Standard Room"
                        if inst_type == 'college' and resources and req_type not in ['none', 'classroom']:
                            comp_rooms = [r['resource_name'] for r in resources if r['resource_type'] == req_type]
                            if comp_rooms: room = comp_rooms[0]
                        model.AddImplication(s_var, lessons[(i, d, p_name, room)])
                model.Add(sum(starts) <= 1)
        
        all_l = [lessons[k] for k in lessons if k[0] == i]
        model.Add(sum(all_l) == target)

    # 5. OVERLAPS
    for d in days:
        for p in periods:
            for teacher in df['teacher_name'].unique():
                t_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and teacher in str(df.loc[k[0], 'teacher_name'])]
                if t_vars: model.Add(sum(t_vars) <= 1)
            for cls in df['class_name'].unique():
                c_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and df.loc[k[0], 'class_name'] == cls]
                if c_vars: model.Add(sum(c_vars) <= 1)

    # 6. SOLVE
    solver = cp_model.CpSolver()
    # Increased time limit to 60s for handling complex blocks and restrictions safely
    solver.parameters.max_time_in_seconds = 60.0 
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        output = []
        for (i, d, p, r), var in lessons.items():
            if solver.Value(var):
                output.append({"Day": d, "Period": p, "Teacher": df.loc[i, 'teacher_name'], "Class": df.loc[i, 'class_name'], "Subject": df.loc[i, 'subject_name'], "Room": r})
        pd.DataFrame(output).to_csv('final_timetable_result.csv', index=False)