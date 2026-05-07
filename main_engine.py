import pandas as pd
from ortools.sat.python import cp_model
import os
import re

def solve_timetable(num_periods=8, num_working_days=5):
    # --- 1. BULLETPROOF DATA PARSER ---
    def normalize_cols(dataframe):
        dataframe.columns = [re.sub(r'[^a-z0-9]', '', str(c).lower()) for c in dataframe.columns]
        return dataframe

    def get_val(item, col, default=''):
        val = item.get(col, default)
        if pd.isna(val): return default
        return str(val).strip()

    # Locate files dynamically
    school_file = next((f for f in os.listdir('.') if ('school' in f.lower() or 'workload' in f.lower()) and f.endswith('.csv')), 'school_data.csv')
    if not os.path.exists(school_file): return
    
    df = normalize_cols(pd.read_csv(school_file))
    
    restrictions = []
    rest_file = next((f for f in os.listdir('.') if 'restrict' in f.lower() and f.endswith('.csv')), None)
    if rest_file:
        rest_df = normalize_cols(pd.read_csv(rest_file))
        restrictions = rest_df.to_dict('records')

    resources = []
    res_file = next((f for f in os.listdir('.') if 'resource' in f.lower() and f.endswith('.csv')), None)
    if res_file:
        res_df = normalize_cols(pd.read_csv(res_file))
        resources = res_df.to_dict('records')

    # THE BREAKTHROUGH: Reliably detect College vs School without relying on hidden columns
    is_college_mode = len(resources) > 0

    all_possible_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    days = all_possible_days[:num_working_days]
    periods = [f'Period {i}' for i in range(1, num_periods + 1)]
    
    # --- 1.5 FORMATTER ---
    def parse_period(p_str):
        nums = re.findall(r'\d+', str(p_str))
        return f"Period {nums[0]}" if nums else str(p_str).strip()

    def parse_day(d_str):
        d_str = str(d_str).lower().strip()
        for prefix, full in zip(['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su'], all_possible_days):
            if d_str.startswith(prefix): return full
        return str(d_str).strip()

    normalized_restrictions = []
    for rest in restrictions:
        normalized_restrictions.append({
            'teachername': get_val(rest, 'teachername').lower(),
            'day': parse_day(get_val(rest, 'day')),
            'period': parse_period(get_val(rest, 'period')),
            'restrictiontype': get_val(rest, 'restrictiontype').lower()
        })
    
    model = cp_model.CpModel()
    lessons = {}

    # --- 2. VARIABLES & SMART ROOM MATCHING ---
    for i, row in df.iterrows():
        req_type = get_val(row, 'requiredresourcetype', 'none').lower()
        teacher_name = get_val(row, 'teachername', '').lower()
        is_lab = 'lab' in req_type or 'pract' in req_type

        # STRICT LAB ROOM LOGIC
        rooms = ["Standard Room"]
        if is_college_mode and is_lab:
            lab_rooms = [get_val(r, 'resourcename') for r in resources if 'lab' in get_val(r, 'resourcetype').lower()]
            if lab_rooms: rooms = lab_rooms

        for d in days:
            for p in periods:
                rest_type = None
                for rest in normalized_restrictions:
                    if rest['teachername'] in teacher_name and rest['day'] == d and rest['period'] == p:
                        rest_type = rest['restrictiontype']
                        break
                
                for r in rooms:
                    lessons[(i, d, p, r)] = model.NewBoolVar(f'L_{i}_{d}_{p}_{r}')
                    if rest_type == "unavailable": model.Add(lessons[(i, d, p, r)] == 0)

    # --- 3. MUST TEACH LOGIC ---
    for rest in normalized_restrictions:
        if "must teach" in rest['restrictiontype']:
            r_teacher = rest['teachername']
            r_day = rest['day']
            r_period = rest['period']
            
            if r_day in days and r_period in periods:
                must_teach_vars = [lessons[k] for k in lessons if k[1] == r_day and k[2] == r_period and r_teacher in get_val(df.loc[k[0]], 'teachername').lower()]
                if must_teach_vars: model.Add(sum(must_teach_vars) == 1)

    # --- 4. EXPLICIT BLOCKS & DYNAMIC LIMITS ---
    for i, row in df.iterrows():
        try: target = int(float(get_val(row, 'weeklyperiod', 1)))
        except ValueError: target = 1
            
        req_type = get_val(row, 'requiredresourcetype', 'none').lower()
        is_lab = 'lab' in req_type or 'pract' in req_type

        # STRICT COLLEGE LABS: Force mathematically explicit 3-period blocks
        if is_college_mode and is_lab and target % 3 == 0:
            num_blocks = target // 3
            block_vars = []
            b_dict = {}

            sub_rooms = list(set(k[3] for k in lessons if k[0] == i))

            for d in days:
                daily_blocks = []
                for p_idx in range(len(periods) - 2): # Fits exactly up to Period 6,7,8
                    for r in sub_rooms:
                        b_var = model.NewBoolVar(f'B3_{i}_{d}_{p_idx}_{r}')
                        block_vars.append(b_var)
                        daily_blocks.append(b_var)
                        b_dict[(d, p_idx, r)] = b_var
                
                # Max 1 block per day (Guarantees exactly 3 periods per day for labs)
                model.Add(sum(daily_blocks) <= 1)

            model.Add(sum(block_vars) == num_blocks)

            # Tie the individual periods perfectly to the 3-period block
            for d in days:
                for p_idx, p in enumerate(periods):
                    for r in sub_rooms:
                        covering = []
                        for start_offset in [0, 1, 2]:
                            s_idx = p_idx - start_offset
                            if 0 <= s_idx <= len(periods) - 3:
                                covering.append(b_dict[(d, s_idx, r)])
                        model.Add(lessons[(i, d, p, r)] == sum(covering))

        else:
            # THEORY OR SCHOOL LOGIC
            if is_college_mode:
                max_per_day = 2
            else:
                max_per_day = 2 if target > 5 else 1

            for d in days:
                daily_p_vars = []
                for p in periods:
                    p_vars = [lessons[k] for k in lessons if k[0] == i and k[1] == d and k[2] == p]
                    daily_p_vars.append(sum(p_vars))
                
                model.Add(sum(daily_p_vars) <= max_per_day)

                # Forbid gaps if max_per_day == 2 (Forces them to be strictly back-to-back)
                if max_per_day == 2:
                    for a in range(len(periods)):
                        for b in range(a + 2, len(periods)):
                            model.Add(daily_p_vars[a] + daily_p_vars[b] <= 1)

            all_l = [lessons[k] for k in lessons if k[0] == i]
            model.Add(sum(all_l) == target)

    # --- 5. OVERLAPS & ROOM CONFLICTS ---
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
            
            # Prevent physical lab double-booking
            r_keys = set(k[3] for k in lessons)
            for r in r_keys:
                if r != "Standard Room":
                    r_vars = [lessons[k] for k in lessons if k[1]==d and k[2]==p and k[3]==r]
                    if r_vars: model.Add(sum(r_vars) <= 1)

    # --- 6. SOLVE ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0 
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        output = []
        for (i, d, p, r), var in lessons.items():
            if solver.Value(var):
                output.append({
                    "Day": d, "Period": p, 
                    "Teacher": get_val(df.loc[i], 'teachername'), 
                    "Class": get_val(df.loc[i], 'classname'), 
                    "Subject": get_val(df.loc[i], 'subjectname'), 
                    "Room": r
                })
        pd.DataFrame(output).to_csv('final_timetable_result.csv', index=False)