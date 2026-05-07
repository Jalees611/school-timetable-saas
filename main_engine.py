import pandas as pd
from ortools.sat.python import cp_model
import os
import re

def solve_timetable(num_periods=8, num_working_days=5):
    if not os.path.exists('school_data.csv'): return
    
    # --- 1. BULLETPROOF DATA PARSER ---
    # This strips ALL spaces, underscores, and dashes from column names 
    # so Excel formatting can never break the engine again.
    def normalize_cols(dataframe):
        dataframe.columns = [re.sub(r'[^a-z0-9]', '', str(c).lower()) for c in dataframe.columns]
        return dataframe

    # Helper to safely extract data without "NaN" errors
    def get_val(item, col, default=''):
        val = item.get(col, default)
        if pd.isna(val): return default
        return str(val).strip()

    df = normalize_cols(pd.read_csv('school_data.csv'))
    
    restrictions = []
    if os.path.exists('restrictions_data.csv'):
        rest_df = normalize_cols(pd.read_csv('restrictions_data.csv'))
        restrictions = rest_df.to_dict('records')

    resources = []
    if os.path.exists('resource_data.csv'):
        res_df = normalize_cols(pd.read_csv('resource_data.csv'))
        resources = res_df.to_dict('records')

    all_possible_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    days = all_possible_days[:num_working_days]
    periods = [f'Period {i}' for i in range(1, num_periods + 1)]
    
    model = cp_model.CpModel()
    lessons = {}

    # --- 2. CREATE VARIABLES & ROOM MATCHING ---
    for i, row in df.iterrows():
        # Uses the normalized column names
        req_type = get_val(row, 'requiredresourcetype', 'none').lower()
        inst_type = get_val(row, 'institutiontype', 'school').lower()
        teacher_name = get_val(row, 'teachername', '').lower()
        
        is_lab = 'lab' in req_type or 'pract' in req_type
        is_theory = 'classroom' in req_type

        rooms = ["Standard Room"]
        if 'college' in inst_type and resources:
            if is_lab:
                rooms = [get_val(r, 'resourcename') for r in resources if 'lab' in get_val(r, 'resourcetype').lower()]
            elif is_theory:
                rooms = [get_val(r, 'resourcename') for r in resources if 'classroom' in get_val(r, 'resourcetype').lower()]
            if not rooms: rooms = ["Standard Room"]

        for d in days:
            for p in periods:
                rest_type = None
                for rest in restrictions:
                    if get_val(rest, 'teachername').lower() in teacher_name:
                        if get_val(rest, 'day').lower() == d.lower() and get_val(rest, 'period').lower() == p.lower():
                            rest_type = get_val(rest, 'restrictiontype').lower()
                            break
                
                for r in rooms:
                    lessons[(i, d, p, r)] = model.NewBoolVar(f'L_{i}_{d}_{p}_{r}')
                    if rest_type == "unavailable":
                        model.Add(lessons[(i, d, p, r)] == 0)

    # --- 3. MUST TEACH LOGIC ---
    for rest in restrictions:
        if "must teach" in get_val(rest, 'restrictiontype').lower():
            r_teacher = get_val(rest, 'teachername').lower()
            r_day = get_val(rest, 'day')
            r_period = get_val(rest, 'period')
            
            if r_day in days:
                must_teach_vars = [
                    lessons[k] for k in lessons 
                    if k[1] == r_day and k[2] == r_period and r_teacher in get_val(df.loc[k[0]], 'teachername').lower()
                ]
                if must_teach_vars:
                    model.Add(sum(must_teach_vars) == 1)

    # --- 4. STRICT BLOCK LOGIC & TARGETS ---
    for i, row in df.iterrows():
        try:
            target = int(float(get_val(row, 'weeklyperiod', 1)))
        except ValueError:
            target = 1
            
        req_type = get_val(row, 'requiredresourcetype', 'none').lower()
        inst_type = get_val(row, 'institutiontype', 'school').lower()
        is_lab = 'lab' in req_type or 'pract' in req_type

        # -------------------------------------------------------------
        # USER RULE: Double periods ONLY if weekly periods are > 5
        # -------------------------------------------------------------
        if target > 5:
            block_size = 2
            max_per_day = 2
        else:
            block_size = 1
            max_per_day = 1 # Strictly 1 per day for 5 or fewer periods
            
        # (Preserve college/lab overrides just in case you use them later)
        if 'college' in inst_type:
            if is_lab:
                block_size = 3
                max_per_day = 3
            elif target >= 2:
                block_size = 2
                max_per_day = 2

        # -------------------------------------------------------------
        # BLOCK SEQUENCE LOGIC
        # -------------------------------------------------------------
        if block_size > 1 and target >= block_size:
            all_starts = []
            for d in days:
                daily_starts = []
                for p_idx in range(len(periods) - block_size + 1):
                    # Find available rooms for this specific subject
                    r_keys = list(set([k[3] for k in lessons if k[0] == i]))
                    for r in r_keys: 
                        s_var = model.NewBoolVar(f's_{i}_{d}_{p_idx}_{r}')
                        daily_starts.append(s_var)
                        all_starts.append(s_var)

                        # Force block sequence in same room
                        for b in range(block_size):
                            p_name = periods[p_idx + b]
                            if (i, d, p_name, r) in lessons:
                                model.Add(lessons[(i, d, p_name, r)] == 1).OnlyEnforceIf(s_var)
                
                model.Add(sum(daily_starts) <= 1)
            
            num_blocks = target // block_size
            model.Add(sum(all_starts) == num_blocks)

        # -------------------------------------------------------------
        # APPLY DAILY MAXIMUMS
        # -------------------------------------------------------------
        for d in days:
            daily_lessons = [lessons[k] for k in lessons if k[0] == i and k[1] == d]
            model.Add(sum(daily_lessons) <= max_per_day)

        all_l = [lessons[k] for k in lessons if k[0] == i]
        model.Add(sum(all_l) == target)

    # --- 5. OVERLAPS ---
    teachers = set([get_val(row, 'teachername') for _, row in df.iterrows() if get_val(row, 'teachername')])
    classes = set([get_val(row, 'classname') for _, row in df.iterrows() if get_val(row, 'classname')])
    
    for d in days:
        for p in periods:
            for t in teachers:
                t_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and t == get_val(df.loc[k[0]], 'teachername')]
                if t_vars: model.Add(sum(t_vars) <= 1)
            for c in classes:
                c_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and c == get_val(df.loc[k[0]], 'classname')]
                if c_vars: model.Add(sum(c_vars) <= 1)

    # --- 6. SOLVE ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0 
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        output = []
        for (i, d, p, r), var in lessons.items():
            if solver.Value(var):
                output.append({
                    "Day": d, 
                    "Period": p, 
                    "Teacher": get_val(df.loc[i], 'teachername'), 
                    "Class": get_val(df.loc[i], 'classname'), 
                    "Subject": get_val(df.loc[i], 'subjectname'), 
                    "Room": r
                })
        pd.DataFrame(output).to_csv('final_timetable_result.csv', index=False)