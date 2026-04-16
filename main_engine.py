import pandas as pd
from ortools.sat.python import cp_model
import os

def solve_timetable(num_periods=8, num_working_days=5):
    if not os.path.exists('school_data.csv'): return
    
    # 1. Load Data
    df = pd.read_csv('school_data.csv')
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    # Fallback to prevent crashes if columns are missing
    if 'institution_type' not in df.columns: df['institution_type'] = 'school'
    if 'required_resource_type' not in df.columns: df['required_resource_type'] = 'none'

    restrictions = []
    if os.path.exists('restrictions_data.csv'):
        rest_df = pd.read_csv('restrictions_data.csv')
        rest_df.columns = [str(c).strip().lower() for c in rest_df.columns]
        restrictions = rest_df.to_dict('records')

    resources = []
    if os.path.exists('resource_data.csv'):
        res_df = pd.read_csv('resource_data.csv')
        res_df.columns = [str(c).strip().lower() for c in res_df.columns]
        resources = res_df.to_dict('records')

    all_possible_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    days = all_possible_days[:num_working_days]
    periods = [f'Period {i}' for i in range(1, num_periods + 1)]
    
    model = cp_model.CpModel()
    lessons = {}

    # 2. Create Variables & Robust Room Matching
    for i, row in df.iterrows():
        # ULTRA-ROBUST PARSING: Removes ALL spaces to prevent Excel formatting errors
        req_type = str(row.get('required_resource_type', 'none')).lower().replace(' ', '')
        inst_type = str(row.get('institution_type', 'school')).lower().replace(' ', '')
        teacher_name = str(row.get('teacher_name', '')).strip().lower()
        
        is_lab = 'lab' in req_type
        is_theory = 'classroom' in req_type

        rooms = ["Standard Room"]
        if inst_type == 'college' and resources:
            if is_lab:
                rooms = [r['resource_name'] for r in resources if 'lab' in str(r.get('resource_type', '')).lower()]
            elif is_theory:
                rooms = [r['resource_name'] for r in resources if 'classroom' in str(r.get('resource_type', '')).lower()]
            if not rooms: rooms = ["Standard Room"]

        for d in days:
            for p in periods:
                rest_type = None
                for rest in restrictions:
                    if str(rest.get('teacher_name', '')).lower() in teacher_name:
                        if str(rest.get('day', '')).lower() == d.lower() and str(rest.get('period', '')).lower() == p.lower():
                            rest_type = str(rest.get('restriction_type', '')).lower()
                            break
                
                for r in rooms:
                    lessons[(i, d, p, r)] = model.NewBoolVar(f'L_{i}_{d}_{p}_{r}')
                    if rest_type == "unavailable":
                        model.Add(lessons[(i, d, p, r)] == 0)

    # 3. MUST TEACH LOGIC
    for rest in restrictions:
        if "must teach" in str(rest.get('restriction_type', '')).lower():
            r_teacher = str(rest.get('teacher_name', '')).lower()
            r_day = str(rest.get('day', ''))
            r_period = str(rest.get('period', ''))
            
            if r_day in days:
                must_teach_vars = [
                    lessons[k] for k in lessons 
                    if k[1] == r_day and k[2] == r_period and r_teacher in str(df.loc[k[0], 'teacher_name']).lower()
                ]
                if must_teach_vars:
                    model.Add(sum(must_teach_vars) == 1)

    # 4. STRICT BLOCK LOGIC & TARGETS
    for i, row in df.iterrows():
        target = int(row['weekly_period'])
        req_type = str(row.get('required_resource_type', 'none')).lower().replace(' ', '')
        inst_type = str(row.get('institution_type', 'school')).lower().replace(' ', '')
        
        is_lab = 'lab' in req_type

        block_size = 1
        if inst_type == 'college':
            if is_lab:
                block_size = 3
            elif target >= 2:
                block_size = 2
        elif inst_type == 'school':
            if target >= 6:
                block_size = 2
            else:
                block_size = 1
        
        if block_size > 1 and target >= block_size:
            all_starts = []
            for d in days:
                daily_starts = []
                for p_idx in range(len(periods) - block_size + 1):
                    # Grab available rooms for this row logic
                    r_keys = list(set([k[3] for k in lessons if k[0] == i]))
                    for r in r_keys: 
                        s_var = model.NewBoolVar(f's_{i}_{d}_{p_idx}_{r}')
                        daily_starts.append(s_var)
                        all_starts.append(s_var)

                        for b in range(block_size):
                            p_name = periods[p_idx + b]
                            if (i, d, p_name, r) in lessons:
                                model.Add(lessons[(i, d, p_name, r)] == 1).OnlyEnforceIf(s_var)
                
                model.Add(sum(daily_starts) <= 1)
            
            num_blocks = target // block_size
            model.Add(sum(all_starts) == num_blocks)

        # STRICT DAILY MAXIMUMS (Forces NO clumping of leftover periods)
        for d in days:
            daily_lessons = [lessons[k] for k in lessons if k[0] == i and k[1] == d]
            if block_size == 3:
                model.Add(sum(daily_lessons) <= 3)
            elif block_size == 2:
                model.Add(sum(daily_lessons) <= 2)
            else:
                if target <= len(days):
                    model.Add(sum(daily_lessons) <= 1)
                else:
                    model.Add(sum(daily_lessons) <= 2)

        # Total weekly target
        all_l = [lessons[k] for k in lessons if k[0] == i]
        model.Add(sum(all_l) == target)

    # 5. OVERLAPS
    for d in days:
        for p in periods:
            for teacher in df['teacher_name'].unique():
                t_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and teacher == df.loc[k[0], 'teacher_name']]
                if t_vars: model.Add(sum(t_vars) <= 1)
            for cls in df['class_name'].unique():
                c_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and cls == df.loc[k[0], 'class_name']]
                if c_vars: model.Add(sum(c_vars) <= 1)

    # 6. SOLVE
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0 
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        output = []
        for (i, d, p, r), var in lessons.items():
            if solver.Value(var):
                output.append({"Day": d, "Period": p, "Teacher": df.loc[i, 'teacher_name'], "Class": df.loc[i, 'class_name'], "Subject": df.loc[i, 'subject_name'], "Room": r})
        pd.DataFrame(output).to_csv('final_timetable_result.csv', index=False)