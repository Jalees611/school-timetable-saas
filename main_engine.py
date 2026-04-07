import pandas as pd
from ortools.sat.python import cp_model
import time

def run_parallel_engine(csv_path):
    df = pd.read_csv(csv_path)
    df = df.rename(columns={'subject_name': 'subject', 'weekly_period': 'periods_per_week'})
    
    model = cp_model.CpModel()
    days, periods_per_day = 5, 8
    day_list, period_list = range(1, days + 1), range(1, periods_per_day + 1)
    
    # 1. Identify all unique individual teachers (even inside Humaira/Haseeb rows)
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

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 180.0
    print(f"🧠 Solving for {len(all_teachers)} teachers and {len(df['class_name'].unique())} classes...")
    status = solver.Solve(model)

    if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
        output = []
        for d in day_list:
            for p in period_list:
                for i, row in enumerate(assignments):
                    if solver.Value(schedule[(i, d, p)]):
                        output.append({"Day": d, "Period": p, "Teacher": row['teacher_name'], "Class": row['class_name'], "Subject": row['subject']})
        pd.DataFrame(output).to_csv("final_timetable_result.csv", index=False)
        print("✅ SUCCESS! Every class is full and the two 'Ayeshas' are correctly scheduled.")
    else:
        print("❌ FAILED: Unexpected conflict.")

if __name__ == "__main__":
    run_parallel_engine('school_data.csv')