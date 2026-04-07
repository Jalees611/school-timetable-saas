import pandas as pd

df = pd.read_csv('teacher load count.csv')
df = df.rename(columns={'subject_name': 'subject', 'weekly_period': 'periods_per_week'})

print("--- 📋 DATA DIAGNOSTICS ---")

# 1. Check for Class Overload (> 40 periods)
class_totals = df.groupby('class_name')['periods_per_week'].sum()
overloaded_classes = class_totals[class_totals > 40]
if not overloaded_classes.empty:
    print("\n❌ OVERLOADED CLASSES (Must be 40 or less):")
    print(overloaded_classes)

# 2. Check for Teacher Overload (> 40 periods)
teacher_totals = df.groupby('teacher_name')['periods_per_week'].sum()
overloaded_teachers = teacher_totals[teacher_totals > 40]
if not overloaded_teachers.empty:
    print("\n❌ OVERLOADED TEACHERS (Must be 40 or less):")
    print(overloaded_teachers)

# 3. Check Capacity
total_needed = df['periods_per_week'].sum()
# We subtract the 'split' periods (Bio/Comp) because they share a slot
# For now, let's look at the raw total
print(f"\nTotal Periods Requested: {total_needed}")
print(f"Max Possible Slots (24 classes x 40 periods): 960")