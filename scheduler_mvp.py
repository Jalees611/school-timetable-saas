from ortools.sat.python import cp_model
import time

def run_ultimate_engine():
    model = cp_model.CpModel()
    
    # 1. SETUP DATA
    num_teachers = 50 
    num_classes = 25   
    days = 5
    periods_per_day = 8
    
    teachers = [f"T_{i}" for i in range(num_teachers)]
    classes = [f"C_{j}" for j in range(num_classes)]
    day_list = range(1, days + 1)
    period_list = range(1, periods_per_day + 1)

    # --- SHARED FACULTY DATA ---
    # Let's block Teacher_0 from working on Mondays (Day 1)
    # and Teacher_1 from working the first 4 periods of Tuesday (Day 2)
    blocked_slots = {
        "T_0": [(1, p) for p in period_list], # All of Day 1
        "T_1": [(2, 1), (2, 2), (2, 3), (2, 4)] # Tue Morning
    }

    schedule = {}
    for t in teachers:
        for c in classes:
            for d in day_list:
                for p in period_list:
                    schedule[(t, c, d, p)] = model.NewBoolVar(f't{t}_c{c}_d{d}_p{p}')

    # 2. APPLY SHARED FACULTY RESTRICTIONS
    for t, slots in blocked_slots.items():
        for (d_block, p_block) in slots:
            for c in classes:
                # Physically lock these slots to ZERO
                model.Add(schedule[(t, c, d_block, p_block)] == 0)

    # 3. STANDARD RULES
    for c in classes:
        model.Add(sum(schedule[(t, c, d, p)] for t in teachers for d in day_list for p in period_list) == 5)

    for t in teachers:
        for d in day_list:
            for p in period_list:
                model.AddAtMostOne(schedule[(t, c, d, p)] for c in classes)

    for c in classes:
        for d in day_list:
            for p in period_list:
                model.AddAtMostOne(schedule[(t, c, d, p)] for t in teachers)

    # SPREAD RULE (Max 2 per day)
    for t in teachers:
        for c in classes:
            for d in day_list:
                model.Add(sum(schedule[(t, c, d, p)] for p in period_list) <= 2)

    # 4. SOLVE
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    
    print("Solving with Shared Faculty constraints...")
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"✅ SUCCESS! Shared faculty slots respected.")
        # Verify Teacher_0 (Should be empty on Day 1)
        print("\nVerification for T_0 on Day 1:")
        day1_work = [p for p in period_list for c in classes if solver.Value(schedule[('T_0', c, 1, p)])]
        if not day1_work:
            print("Confirmed: T_0 has no classes on Day 1 (Monday).")
    else:
        print("❌ FAILED: Constraints too tight.")

run_ultimate_engine()