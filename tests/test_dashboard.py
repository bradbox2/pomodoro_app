"""
Simple script to generate and open the dashboard for testing.
"""
import os
from pomodoro_data_manager import PomodoroDataManager
from analysis_manager import AnalysisManager

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")

# Initialize managers
data_manager = PomodoroDataManager(data_dir, "pomodoro_data.db")
analysis_manager = AnalysisManager(data_manager, base_dir)

# Generate dashboard
print("Generating dashboard...")
analysis_manager.generate_and_show_report()
print("Dashboard opened in browser!")

data_manager.close()
