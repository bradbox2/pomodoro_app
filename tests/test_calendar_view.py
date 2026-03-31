# test_calendar_view.py
"""
Test script to verify calendar view functionality and database data.
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from pomodoro_data_manager import PomodoroDataManager

def test_calendar_data():
    """Test if calendar view has data to display."""
    
    # Setup paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    db_name = "pomodoro_data.db"
    
    print("=" * 60)
    print("CALENDAR VIEW DATA VERIFICATION")
    print("=" * 60)
    print(f"\nDatabase Path: {os.path.join(data_dir, db_name)}")
    
    # Initialize data manager
    data_manager = PomodoroDataManager(data_dir, db_name)
    
    # Get all sessions
    df = data_manager.get_all_sessions_for_analysis()
    
    if df.empty:
        print("\n❌ NO DATA FOUND IN DATABASE")
        print("   The calendar view will be empty because there are no sessions recorded.")
        data_manager.close()
        return
    
    print(f"\n✅ Total Sessions in Database: {len(df)}")
    
    # Process data like the calendar view does
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['date'] = df['start_time'].dt.date
    
    # Filter for completed work sessions
    work_df = df[df['session_type'] == 'Work'].copy()
    completed_work_df = work_df[work_df['status'] == 'Completed'].copy()
    
    print(f"   - Work Sessions: {len(work_df)}")
    print(f"   - Completed Work Sessions: {len(completed_work_df)}")
    
    if completed_work_df.empty:
        print("\n❌ NO COMPLETED WORK SESSIONS")
        print("   The calendar view requires 'Completed' work sessions to display counts.")
        data_manager.close()
        return
    
    # Group by date to get daily counts
    daily_counts = completed_work_df.groupby('date')['duration_minutes'].count().reset_index(name='pomodoro_count')
    daily_counts['date'] = pd.to_datetime(daily_counts['date'])
    
    print(f"\n✅ Days with Completed Pomodoros: {len(daily_counts)}")
    print("\n" + "=" * 60)
    print("DAILY POMODORO COUNTS (Last 30 Days)")
    print("=" * 60)
    
    # Show last 30 days
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    recent_counts = daily_counts[daily_counts['date'] >= thirty_days_ago].sort_values('date', ascending=False)
    
    if recent_counts.empty:
        print("\n⚠️  NO DATA IN LAST 30 DAYS")
        print("   All completed sessions are older than 30 days.")
    else:
        print(f"\n{'Date':<15} {'Day':<12} {'Pomodoros':<10} {'Visual'}")
        print("-" * 60)
        for _, row in recent_counts.iterrows():
            date = row['date']
            count = int(row['pomodoro_count'])
            day_name = date.strftime('%A')
            visual = '🍅 ' * count
            
            # Highlight today
            date_str = date.strftime('%Y-%m-%d')
            if date.date() == today.date():
                date_str += " (TODAY)"
            
            print(f"{date_str:<15} {day_name:<12} {count:<10} {visual}")
    
    # Check calendar view months
    print("\n" + "=" * 60)
    print("CALENDAR VIEW MONTH RANGE")
    print("=" * 60)
    
    current_month_start = today.replace(day=1)
    
    # Calculate previous month
    if current_month_start.month == 1:
        previous_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
    else:
        previous_month_start = current_month_start.replace(month=current_month_start.month - 1)
    
    # Calculate end of current month
    if current_month_start.month == 12:
        current_month_end = current_month_start.replace(year=current_month_start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        current_month_end = current_month_start.replace(month=current_month_start.month + 1, day=1) - timedelta(days=1)
    
    print(f"\nCalendar displays: {previous_month_start.strftime('%B %Y')} + {current_month_start.strftime('%B %Y')}")
    print(f"Date Range: {previous_month_start.strftime('%Y-%m-%d')} to {current_month_end.strftime('%Y-%m-%d')}")
    
    # Check if there's data in this range
    calendar_range_data = daily_counts[
        (daily_counts['date'] >= previous_month_start) & 
        (daily_counts['date'] <= current_month_end)
    ]
    
    if calendar_range_data.empty:
        print(f"\n❌ NO DATA IN CALENDAR RANGE")
        print(f"   All completed sessions are outside the {previous_month_start.strftime('%B %Y')} - {current_month_start.strftime('%B %Y')} range.")
    else:
        print(f"\n✅ Days with data in calendar range: {len(calendar_range_data)}")
        total_pomodoros = calendar_range_data['pomodoro_count'].sum()
        print(f"   Total Pomodoros in this range: {int(total_pomodoros)}")
    
    # Show all dates with data
    print("\n" + "=" * 60)
    print("ALL DATES WITH COMPLETED POMODOROS")
    print("=" * 60)
    print(f"\nEarliest: {daily_counts['date'].min().strftime('%Y-%m-%d')}")
    print(f"Latest:   {daily_counts['date'].max().strftime('%Y-%m-%d')}")
    
    data_manager.close()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print("\nTo see the calendar view:")
    print("1. Run the Pomodoro app (main.py)")
    print("2. Click the 'Dashboard' button")
    print("3. The Summary tab will show the calendar at the top")
    print("\nIf the calendar appears empty, check the date ranges above.")
    print("=" * 60)

if __name__ == "__main__":
    test_calendar_data()
