import pandas as pd
from ortools.sat.python import cp_model
import os
import re

def solve_timetable(num_periods=8, num_working_days=5):
    if not os.path.exists('school_data.csv'): return
    
    # --- 1. BULLETPROOF DATA PARSER ---
    def normalize_cols(dataframe):
        dataframe.columns = [re.sub(r'[^a-z0-9]', '', str(c).lower()) for c in dataframe.columns]
        return dataframe

    def get_val(item, col, default=''):
        val = item.get(col, default)
        if pd.isna(val): return default
        return str(val).strip()

    df = normalize_cols(pd.read_csv('school_data.csv'))
    
    restrictions = []
    if os.path.exists('restrictions_data.csv'):
        rest_df = normalize_cols(pd.read_csv('restrictions_data.csv'))
        restrictions = rest_df.to_dict('records')
    elif os.path.exists('restrictions-school.csv'):
        rest_df = normalize_cols(pd.read_csv('restrictions-school.csv'))
        restrictions = rest_df.to_dict('records')

    resources = []
    if os.path.exists('resource_data.csv'):
        res_df = normalize_cols(pd.read_csv('resource_data.csv'))
        resources = res_df.to_dict('records')

    all_possible_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    days = all_possible_days[:num_working_days]
    periods = [f'Period {i}' for i in range(1, num_periods + 1)]
    
    # --- 1.5 BULLETPROOF RESTRICTION FORMATTER ---
    # This guarantees that typos like "Monday" or "6" never break the rules
    def parse_period(p_str):
        nums = re.findall(r'\d+', str(p_str))
        return f"Period {nums[0]}" if nums else str(p_str).strip()

    def parse_day(d_str):
        d_str = str(d_str).lower().strip()
        if d_str.startswith('mo'): return 'Mon'
        if d_str.startswith('tu'): return 'Tue'
        if d_str.startswith('we'): return 'Wed'
        if d_str.startswith('th'): return 'Thu'
        if d_str.startswith('fr'): return 'Fri'
        if d_str.startswith('sa'): return 'Sat'
        if d_str.startswith('su'): return 'Sun'
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

    # --- 2. CREATE VARIABLES & ROOM MATCHING ---
    for i, row in df.iterrows():
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
                for rest in normalized_restrictions:
                    if rest['teachername'] in teacher_name:
                        if rest['day'] == d and rest['period'] == p:
                            rest_type = rest['restrictiontype']
                            break
                
                for r in rooms:
                    lessons[(i, d, p, r)] = model.NewBoolVar(f'L_{i}_{d}_{p}_{r}')
                    if rest_type == "unavailable":
                        model.Add(lessons[(i, d, p, r)] == 0)

    # --- 3. MUST TEACH LOGIC ---
    for rest in normalized_restrictions:
        if "must teach" in rest['restrictiontype']:
            r_teacher = rest['teachername']
            r_day = rest['day']
            r_period = rest['period']
            
            if r_day in days and r_period in periods:
                must_teach_vars = [
                    lessons[k] for k in lessons 
                    if k[1] == r_day and k[2] == r_period and r_teacher in get_val(df.loc[k[0]], 'teachername').lower()
                ]
                if must_teach_vars:
                    model.Add(sum(must_teach_vars) == 1)

    # --- 4. DAILY MAXIMUMS & CONSECUTIVE DOUBLE PERIODS ---
    for i, row in df.iterrows():
        try:
            target = int(float(get_val(row, 'weeklyperiod', 1)))
        except ValueError:
            target = 1
            
        req_type = get_val(row, 'requiredresourcetype', 'none').lower()
        inst_type = get_val(row, 'institutiontype', 'school').lower()
        is_lab = 'lab' in req_type or 'pract' in req_type

        if target > 5:
            max_per_day = 2
        else:
            max_per_day = 1 
            
        if 'college' in inst_type and is_lab:
            max_per_day = 3

        for d in days:
            daily_lessons_vars = []
            for p in periods:
                p_vars = [lessons[k] for k in lessons if k[0] == i and k[1] == d and k[2] == p]
                daily_lessons_vars.append(sum(p_vars))
                
            model.Add(sum(daily_lessons_vars) <= max_per_day)

            if max_per_day == 2:
                num_p = len(periods)
                for a in range(num_p):
                    for b in range(a + 2, num_p):
                        model.Add(daily_lessons_vars[a] + daily_lessons_vars[b] <= 1)

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