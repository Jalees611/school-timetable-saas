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

    # Makes the engine immune to Excel's weird text encoding
    def safe_read_csv(file_path):
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding='windows-1252')

    # Find the main data file
    data_file = next((f for f in os.listdir('.') if ('school' in f.lower() or 'workload' in f.lower()) and f.endswith('.csv')), 'school_data.csv')
    if not os.path.exists(data_file): return
    
    df = normalize_cols(safe_read_csv(data_file))
    
    restrictions = []
    rest_file = next((f for f in os.listdir('.') if 'restrict' in f.lower() and f.endswith('.csv')), None)
    if rest_file:
        rest_df = normalize_cols(safe_read_csv(rest_file))
        restrictions = rest_df.to_dict('records')

    resources = []
    res_file = next((f for f in os.listdir('.') if 'resource' in f.lower() and f.endswith('.csv')), None)
    if res_file:
        res_df = normalize_cols(safe_read_csv(res_file))
        resources = res_df.to_dict('records')

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

    # --- 2. VARIABLES & ROOM MATCHING ---
    for i, row in df.iterrows():
        inst_type = get_val(row, 'institutiontype', 'school').lower()
        req_type = get_val(row, 'requiredresourcetype', 'none').lower()
        teacher_name = get_val(row, 'teachername', '').lower()
        
        is_college = 'college' in inst_type
        is_lab = 'lab' in req_type or 'pract' in req_type

        # ---> THE UPDATE: NOW DYNAMICALLY ASSIGNS BOTH LABS AND THEORY ROOMS <---
        rooms = ["Standard Room"]
        if is_college and resources:
            if is_lab:
                lab_rooms = [get_val(r, 'resourcename') for r in resources if 'lab' in get_val(r, 'resourcetype').lower()]
                if lab_rooms: rooms = lab_rooms
            else:
                theory_rooms = [get_val(r, 'resourcename') for r in resources if 'classroom' in get_val(r, 'resourcetype').lower()]
                if theory_rooms: rooms = theory_rooms

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

    # --- 4. EXPLICIT LOGIC (SCHOOL VS COLLEGE) ---
    for i, row in df.iterrows():
        try: target = int(float(get_val(row, 'weeklyperiod', 1)))
        except ValueError: target = 1
            
        inst_type = get_val(row, 'institutiontype', 'school').lower()
        req_type = get_val(row, 'requiredresourcetype', 'none').lower()
        
        is_college = 'college' in inst_type
        is_lab = 'lab' in req_type or 'pract' in req_type

        sub_rooms = list(set(k[3] for k in lessons if k[0] == i))

        for d in days:
            daily_p_vars = []
            for p in periods:
                p_sum = []
                for r in sub_rooms:
                    p_sum.append(lessons[(i, d, p, r)])
                daily_p_vars.append(sum(p_sum))
            
            daily_sum = sum(daily_p_vars)
            day_active = model.NewBoolVar(f'day_act_{i}_{d}')
            model.Add(daily_sum > 0).OnlyEnforceIf(day_active)
            model.Add(daily_sum == 0).OnlyEnforceIf(day_active.Not())

            # ---------------------------------------------------------
            # THE RULES
            # ---------------------------------------------------------
            if is_college and is_lab:
                # COLLEGE LAB: Force exactly 3 periods per day. 
                model.Add(daily_sum == 3 * day_active)
                
                # Anti-Room Hopping: Stay in one physical lab all 3 periods
                if len(sub_rooms) > 1:
                    r_actives = {r: model.NewBoolVar(f'ract_{i}_{d}_{r}') for r in sub_rooms}
                    model.Add(sum(r_actives.values()) == day_active)
                    for p in periods:
                        for r in sub_rooms:
                            model.Add(lessons[(i, d, p, r)] <= r_actives[r])

            elif is_college and not is_lab:
                # COLLEGE THEORY: Max 2 periods per day
                model.Add(daily_sum <= 2)

                # ---> THE UPDATE: Anti-Room Hopping for Theory Classes <---
                if len(sub_rooms) > 1 and "Standard Room" not in sub_rooms:
                    r_actives = {r: model.NewBoolVar(f'ract_{i}_{d}_{r}') for r in sub_rooms}
                    model.Add(sum(r_actives.values()) == day_active)
                    for p in periods:
                        for r in sub_rooms:
                            model.Add(lessons[(i, d, p, r)] <= r_actives[r])

            else:
                # SCHOOL LOGIC: 1 per day, unless > 5
                max_per_day = 2 if target > 5 else 1
                model.Add(daily_sum <= max_per_day)

            # ---------------------------------------------------------
            # GAPLESS GUARANTEE: No matter the rule, periods must be consecutive
            # ---------------------------------------------------------
            starts = []
            s0 = model.NewIntVar(0, 1, f's0_{i}_{d}')
            model.Add(s0 == daily_p_vars[0])
            starts.append(s0)
            
            for p_idx in range(1, len(periods)):
                s = model.NewIntVar(0, 1, f'start_{i}_{d}_{p_idx}')
                model.Add(s >= daily_p_vars[p_idx] - daily_p_vars[p_idx-1])
                model.Add(s <= daily_p_vars[p_idx])
                model.Add(s <= 1 - daily_p_vars[p_idx-1])
                starts.append(s)
            
            model.Add(sum(starts) <= 1)

        all_l = [lessons[k] for k in lessons if k[0] == i]
        model.Add(sum(all_l) == target)

    # --- 5. OVERLAPS & CONFLICTS ---
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
            
            # ---> THE UPDATE: Prevent double-booking for ALL physical rooms <---
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