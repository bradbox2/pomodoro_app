# analysis_manager.py
import os
import webbrowser
from tkinter import messagebox
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pomodoro_data_manager import PomodoroDataManager
from app_config_manager import AppConfigManager

class AnalysisManager:
    """
    Generates a sophisticated, multi-tabbed interactive HTML report (Dashboard).
    """

    def __init__(self, data_manager: PomodoroDataManager, exports_dir: str, config_path: str | None = None):
        self.data_manager = data_manager
        self.exports_dir = str(exports_dir)
        self.config_path = config_path
        self.report_path = os.path.join(self.exports_dir, 'pomodoro_dashboard.html')

    def generate_and_show_report(self, start_date=None, end_date=None):
        """Fetches data, generates the complete dashboard, and opens it."""
        df = self.data_manager.get_all_sessions_for_analysis()
        
        # --- Create Unique Report Path with Timestamp ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_path = os.path.join(self.exports_dir, f'pomodoro_dashboard_{timestamp}.html')
        
        # --- DEBUG MESSAGEBOX ---
        # messagebox.showinfo("Debug Info", f"Total Sessions in DB: {len(df)}\nDate Range: {start_date} to {end_date}")
        
        if df.empty:
            messagebox.showinfo("No Data", "There is no session data to analyze yet.")
            return

        # --- Data Preprocessing ---
        df['start_time'] = pd.to_datetime(df['start_time'])
        
        # --- Date Filtering ---
        if start_date:
            df = df[df['start_time'] >= start_date]
        if end_date:
            # Ensure correct type comparison
            if df['start_time'].dtype == object:
                 df['start_time'] = pd.to_datetime(df['start_time'])
            df = df[df['start_time'] <= end_date]
            
            
        if df.empty:
             messagebox.showinfo("No Data", "No session data found for the selected period.")
             return

        df['day_of_week'] = df['start_time'].dt.day_name()
        df['hour'] = df['start_time'].dt.hour
        df['date'] = df['start_time'].dt.date
        
        # Define time of day
        bins = [0, 12, 18, 24]
        labels = ['Morning (0-12)', 'Afternoon (12-18)', 'Evening (18-24)']
        # Use pd.Categorical to avoid warning with pd.cut
        df['time_of_day'] = pd.cut(df['hour'], bins=bins, labels=labels, right=False, ordered=True)

        work_df = df[df['session_type'] == 'Work'].copy()
        completed_work_df = work_df[work_df['status'] == 'Completed'].copy()
        interrupted_df = work_df[work_df['status'] == 'Interrupted'].copy()

        # --- Generate Charts for Each Tab ---
        # --- Generate Charts for Each Tab ---
        chart1_html = self._create_summary_chart(completed_work_df)
        chart2_html = self._create_time_distribution_chart(completed_work_df)
        chart3_html = self._create_interruption_analysis_chart(interrupted_df)
        chart4_html = self._create_focus_mood_analysis_chart(completed_work_df)
        
        # --- Build the Final HTML Dashboard ---
        self._create_html_dashboard(chart1_html, chart2_html, chart3_html, chart4_html)

        webbrowser.open('file://' + os.path.realpath(self.report_path))

    def _create_summary_chart(self, df):
        """Creates a stacked bar chart showing total time per project and task, plus calendar view."""
        html_output = ""
        
        # Add Calendar View at the top
        html_output += self._generate_calendar_view(df)
        
        if df.empty: return html_output + "<p>No completed work sessions to summarize.</p>"
        
        # Group by Project AND Task
        task_time = df.groupby(['project_name', 'task_name'], observed=True)['duration_minutes'].sum().reset_index()
        
        fig = px.bar(task_time, y='project_name', x='duration_minutes', color='task_name', orientation='h',
                     title='Total Focus Time by Project & Task', 
                     labels={'duration_minutes': 'Total Minutes', 'project_name': 'Project', 'task_name': 'Task'},
                     text='task_name')
        
        fig.update_traces(textposition='inside', insidetextanchor='middle')
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, uniformtext_minsize=8, uniformtext_mode='hide')
        html_output += fig.to_html(full_html=False, include_plotlyjs=False)
        return html_output

    def _generate_calendar_view(self, df):
        """Generate calendar view showing previous month + current month with heatmap effect."""
        if df.empty:
            return "<p>No data available for calendar view.</p>"
        
        html_output = ""
        
        # Group by Date to get pomodoro counts
        # Convert date column to datetime and normalize to remove time component
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        daily_counts = df.groupby('date')['duration_minutes'].count().reset_index(name='pomodoro_count')
        
        # Determine the 2-month period: previous month + current month
        today = datetime.now()
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
        
        # Create a complete date range for both months (normalized to midnight)
        all_dates = pd.date_range(start=previous_month_start, end=current_month_end, freq='D').normalize()
        
        # Merge with actual data, filling missing dates with 0
        date_df = pd.DataFrame({'date': all_dates})
        date_df = date_df.merge(daily_counts, on='date', how='left')
        date_df['pomodoro_count'] = date_df['pomodoro_count'].fillna(0).astype(int)
        
        # Generate calendar HTML for both months
        def generate_calendar_html(year, month, data_df):
            """Generate HTML calendar table for a given month"""
            import calendar
            
            # Set Monday as first day of week
            calendar.setfirstweekday(0)  # 0 = Monday
            
            month_name = calendar.month_name[month]
            cal = calendar.monthcalendar(year, month)
            
            # Create data lookup dictionary
            data_lookup = {}
            for _, row in data_df.iterrows():
                if row['date'].year == year and row['date'].month == month:
                    data_lookup[row['date'].day] = int(row['pomodoro_count'])
            
            # Build HTML table
            html = f'<div style="margin: 20px; display: inline-block; vertical-align: top;">'
            html += f'<h3 style="text-align: center; margin-bottom: 10px; color: #264653;">{month_name} {year}</h3>'
            html += '<table style="border-collapse: collapse; border: 2px solid #264653; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">'
            
            # Header row with day names
            html += '<tr>'
            for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
                html += f'<th style="border: 1px solid #ccc; padding: 10px; background-color: #264653; color: white; font-weight: bold; min-width: 65px;">{day}</th>'
            html += '</tr>'
            
            # Calendar rows
            for week in cal:
                html += '<tr>'
                for day in week:
                    if day == 0:
                        # Empty cell for days outside the month
                        html += '<td style="border: 1px solid #e0e0e0; padding: 10px; background-color: #fafafa;"></td>'
                    else:
                        count = data_lookup.get(day, 0)
                        # Simplified 3-level high-contrast color scheme
                        if count == 0:
                            bg_color = '#f5f5f5'
                            border_color = '#e0e0e0'
                        elif count <= 3:
                            bg_color = '#a8e6cf'  # Light green
                            border_color = '#7ed6a8'
                        elif count <= 6:
                            bg_color = '#56ab91'  # Medium green
                            border_color = '#3d9373'
                        else:  # 7+
                            bg_color = '#2d6a4f'  # Dark green
                            border_color = '#1b4332'
                        
                        text_color = '#000000' if count <= 6 else '#ffffff'
                        font_weight = 'bold' if count > 0 else 'normal'
                        
                        html += f'<td style="border: 2px solid {border_color}; padding: 10px; background-color: {bg_color}; color: {text_color}; text-align: center; vertical-align: middle; transition: all 0.3s;">'
                        html += f'<div style="font-weight: {font_weight}; font-size: 16px;">{day}</div>'
                        if count > 0:
                            html += f'<div style="font-size: 11px; margin-top: 4px; opacity: 0.9;">🍅 {count}</div>'
                        html += '</td>'
                html += '</tr>'
            
            html += '</table></div>'
            return html
        
        # Generate calendars for both months (previous first, then current)
        cal1_html = generate_calendar_html(previous_month_start.year, previous_month_start.month, date_df)
        cal2_html = generate_calendar_html(current_month_start.year, current_month_start.month, date_df)
        
        # Combine both calendars side by side with title
        html_output += '<div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">'
        html_output += '<h2 style="text-align: center; color: #264653; margin-bottom: 20px;">📅 Pomodoro Activity Calendar</h2>'
        html_output += '<div style="text-align: center;">'
        html_output += cal1_html + cal2_html
        html_output += '</div></div>'
        
        return html_output
    
    def _create_time_distribution_chart(self, df):
        """Creates charts for analyzing productivity by time."""
        if df.empty: return "<p>No completed work sessions for time analysis.</p>"
        
        html_output = ""
        
        # 2. By Day of Week
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        # Ensure we capture all days, filling missing with 0
        grouped_day = df.groupby('day_of_week', observed=True)['duration_minutes'].sum()
        day_time = grouped_day.reindex(day_order).fillna(0).reset_index()
        
        fig_day = px.bar(day_time, x='day_of_week', y='duration_minutes',
                      title='Focus Time by Day of the Week', 
                      labels={'duration_minutes': 'Total Minutes', 'day_of_week': 'Day'})
        # Force correct order on X axis
        fig_day.update_xaxes(categoryorder='array', categoryarray=day_order)
        html_output += fig_day.to_html(full_html=False, include_plotlyjs=False)

        # 3. Weekly Trend
        df['week_period'] = df['start_time'].dt.to_period('W-SUN').astype(str)
        weekly_data = df.groupby('week_period', observed=True)['duration_minutes'].sum().reset_index()
        # Ensure chronological order
        weekly_data = weekly_data.sort_values('week_period')
        
        fig_week = px.bar(weekly_data, x='week_period', y='duration_minutes',
                          title='Total Focus Time by Week',
                          labels={'duration_minutes': 'Total Minutes', 'week_period': 'Week'})
        html_output += fig_week.to_html(full_html=False, include_plotlyjs=False)
                      
        # 4. By Time of Day
        tod_order = ['Morning (0-12)', 'Afternoon (12-18)', 'Evening (18-24)']
        tod_time = df.groupby('time_of_day', observed=True)['duration_minutes'].sum().reset_index()
        
        fig_tod = px.bar(tod_time, x='time_of_day', y='duration_minutes',
                      title='Focus Time by Time of Day', 
                      labels={'duration_minutes': 'Total Minutes', 'time_of_day': 'Time of Day'})
        # Force correct order on X axis
        fig_tod.update_xaxes(categoryorder='array', categoryarray=tod_order)
        html_output += fig_tod.to_html(full_html=False, include_plotlyjs=False)

        return html_output
        
    def _create_interruption_analysis_chart(self, df):
        """Creates pie charts showing reasons for interruption (Internal vs External)."""
        if df.empty or df['interruption_reason'].isnull().all():
            return "<p>No interruptions recorded yet.</p>"
        
        # Reason Category Mapping
        # We need a category map, but AppConfigManager doesn't have it yet.
        # Let's infer it from the structure.
        config_manager = AppConfigManager(self.config_path)
        reasons = config_manager.get_interruption_reasons()
        category_map = {}
        
        # Build map with alias support
        for category, items in reasons.items():
            for item in items:
                # Handle dict vs string
                name = item['name'] if isinstance(item, dict) else item
                category_map[name] = category
                
                # Check for aliases
                aliases = config_manager.get_aliases_for_name(name)
                for alias in aliases:
                    category_map[alias] = category
                
                # Robustness: Map prefix if contains ':' (e.g. "Task Switching:..." -> "Task Switching")
                if ":" in name:
                    prefix = name.split(":")[0].strip()
                    category_map[prefix] = category
        
        # --- Legacy & Fallback Mapping ---
        # Map known legacy/simple strings to their categories
        legacy_map = {
            "Distraction": "Internal",
            "Phone/Message": "External",
            "Colleague/Family": "External",
            "Noise": "External",
            "Fatigue": "Internal",
            "Task Switching": "Internal" # Explicitly ensure this if prefix logic misses
        }
        category_map.update(legacy_map)

        # Apply mapping - fill unknowns with 'Other'
        df = df.copy() # Avoid SettingWithCopyWarning
        df['category'] = df['interruption_reason'].map(category_map).fillna("Other")
        
            # 1. External Chart
        external_df = df[df['category'] == 'External']
        if not external_df.empty:
            # Map aliases to canonical names for display aggregation
            # We need a reverse map: Alias -> Canonical
            canonical_map = {}
            for item in reasons.get('External', []):
                name = item['name'] if isinstance(item, dict) else item
                canonical_map[name] = name
                for alias in config_manager.get_aliases_for_name(name):
                    canonical_map[alias] = name
                # Robustness: Map prefix
                if ":" in name:
                    prefix = name.split(":")[0].strip()
                    canonical_map[prefix] = name
            
            # Legacy Canonical Mapping
            legacy_canonical_map = {
                "Phone/Message": "Communication:电话/邮件/警报",
                "Colleague/Family": "Social:同事/朋友/会议",
                "Noise": "Environment:光线/噪音/空气"
            }
            canonical_map.update(legacy_canonical_map)

            external_df['display_reason'] = external_df['interruption_reason'].map(canonical_map).fillna(external_df['interruption_reason'])
            
            ext_counts = external_df['display_reason'].value_counts().reset_index()
            ext_counts.columns = ['reason', 'count']
            fig_ext = px.pie(ext_counts, names='reason', values='count', 
                            title='External Interruptions', hole=.3)
            html_ext = fig_ext.to_html(full_html=False, include_plotlyjs=False)
        else:
            html_ext = "<p>No External interruptions recorded.</p>"

        # 2. Internal Chart
        internal_df = df[df['category'] == 'Internal']
        if not internal_df.empty:
            canonical_map = {}
            for item in reasons.get('Internal', []):
                name = item['name'] if isinstance(item, dict) else item
                canonical_map[name] = name
                for alias in config_manager.get_aliases_for_name(name):
                    canonical_map[alias] = name
                # Robustness: Map prefix
                if ":" in name:
                    prefix = name.split(":")[0].strip()
                    canonical_map[prefix] = name

            # Legacy Canonical Mapping
            legacy_canonical_map = {
                "Distraction": "Psychological:思维跳跃/焦虑/压力",
                "Fatigue": "Physiological:饥饿/口渴/疲劳",
                "Task Switching": "Task Switching:任务切换/优先级判断"
            }
            canonical_map.update(legacy_canonical_map)

            internal_df['display_reason'] = internal_df['interruption_reason'].map(canonical_map).fillna(internal_df['interruption_reason'])

            int_counts = internal_df['display_reason'].value_counts().reset_index()
            int_counts.columns = ['reason', 'count']
            fig_int = px.pie(int_counts, names='reason', values='count', 
                            title='Internal Interruptions', hole=.3)
            html_int = fig_int.to_html(full_html=False, include_plotlyjs=False)
        else:
             html_int = "<p>No Internal interruptions recorded.</p>"

        return f'<div style="display: flex; flex-wrap: wrap; gap: 20px;">' \
               f'<div style="flex: 1; min-width: 400px;">{html_ext}</div>' \
               f'<div style="flex: 1; min-width: 400px;">{html_int}</div></div>'

    def _create_focus_mood_analysis_chart(self, df):
        """Creates charts analyzing focus score and mood."""
        if df.empty or df['focus_score'].isnull().all():
            return "<p>No session feedback recorded yet.</p>"

        # Average Focus Score by Project
        avg_focus = df.groupby('project_name', observed=True)['focus_score'].mean().reset_index()
        fig1 = px.bar(avg_focus, x='project_name', y='focus_score',
                      title='Average Focus Score by Project', labels={'focus_score': 'Average Score (1-10)', 'project_name': 'Project'})
        fig1.update_yaxes(range=[0, 10])

        # Mood Distribution
        # Use aliases to group moods
        config_manager = AppConfigManager(self.config_path)
        moods = config_manager.get_feedback_moods()
        canonical_map = {}
        for mood in moods:
            name = mood['name'] if isinstance(mood, dict) else mood
            canonical_map[name] = name
            for alias in config_manager.get_aliases_for_name(name):
                canonical_map[alias] = name
        
        df['display_mood'] = df['end_mood'].map(canonical_map).fillna(df['end_mood'])
        
        mood_counts = df['display_mood'].value_counts().reset_index()
        mood_counts.columns = ['mood', 'count']
        fig2 = px.pie(mood_counts, names='mood', values='count',
                      title='Post-Session Mood Distribution', hole=.3)
        
        return fig1.to_html(full_html=False, include_plotlyjs=False) + fig2.to_html(full_html=False, include_plotlyjs=False)

    def _create_html_dashboard(self, chart1, chart2, chart3, chart4):
        """Combines all chart HTML into a single dashboard file with tabs."""
        import plotly
        plotly_js = plotly.offline.get_plotlyjs()
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Pomodoro Dashboard</title>
            <script>{plotly_js}</script>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f4f9; margin: 0; }}
                .header {{ background-color: #264653; color: white; padding: 20px; text-align: center; }}
                .tab-container {{ overflow: hidden; border-bottom: 1px solid #ccc; background-color: #fff; }}
                .tab-container button {{ background-color: inherit; float: left; border: none; outline: none; cursor: pointer; padding: 14px 16px; transition: 0.3s; font-size: 17px; }}
                .tab-container button:hover {{ background-color: #e9c46a; color: #264653; }}
                .tab-container button.active {{ background-color: #2a9d8f; color: white; }}
                .tab-content {{ display: none; padding: 20px; }}
                .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
                .chart-box {{ background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); padding: 15px; }}
            </style>
        </head>
        <body>

            <div class="header"><h1>Pomodoro Productivity Dashboard</h1></div>

            <div class="tab-container">
                <button class="tab-link active" onclick="openTab(event, 'Summary')">Summary</button>
                <button class="tab-link" onclick="openTab(event, 'TimeAnalysis')">Time Analysis</button>
                <button class="tab-link" onclick="openTab(event, 'Interruptions')">Interruptions</button>
                <button class="tab-link" onclick="openTab(event, 'FocusMood')">Focus & Mood</button>
            </div>

            <div id="Summary" class="tab-content" style="display: block;">
                <div class="chart-box">{chart1}</div>
            </div>

            <div id="TimeAnalysis" class="tab-content">
                <div class="chart-grid">{chart2}</div>
            </div>

            <div id="Interruptions" class="tab-content">
                <div class="chart-box">{chart3}</div>
            </div>

            <div id="FocusMood" class="tab-content">
                <div class="chart-grid">{chart4}</div>
            </div>

            <script>
                function openTab(evt, tabName) {{
                    var i, tabcontent, tablinks;
                    tabcontent = document.getElementsByClassName("tab-content");
                    for (i = 0; i < tabcontent.length; i++) {{
                        tabcontent[i].style.display = "none";
                    }}
                    tablinks = document.getElementsByClassName("tab-link");
                    for (i = 0; i < tablinks.length; i++) {{
                        tablinks[i].className = tablinks[i].className.replace(" active", "");
                    }}
                    document.getElementById(tabName).style.display = "block";
                    evt.currentTarget.className += " active";
                }}
            </script>

        </body>
        </html>
        """
        try:
            with open(self.report_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            print(f"Dashboard generated at: {self.report_path}")
        except IOError as e:
            messagebox.showerror("File Error", f"Could not write the dashboard file.\\n{e}")

