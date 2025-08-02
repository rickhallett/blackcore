"""Task Management Kanban Board for Nassau Campaign Intelligence."""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import uuid

# Page config
st.set_page_config(
    page_title="Task Board - Nassau Intelligence",
    page_icon="✅",
    layout="wide"
)

# Custom CSS for Kanban board
st.markdown("""
<style>
    .kanban-column {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        min-height: 500px;
    }
    .kanban-header {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #dee2e6;
    }
    .task-card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 6px;
        padding: 0.75rem;
        margin-bottom: 0.75rem;
        cursor: move;
        transition: all 0.2s ease;
    }
    .task-card:hover {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .priority-high {
        border-left: 4px solid #dc3545;
    }
    .priority-medium {
        border-left: 4px solid #ffc107;
    }
    .priority-low {
        border-left: 4px solid #28a745;
    }
    .assignee-badge {
        background: #e3f2fd;
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        display: inline-block;
        margin-top: 0.5rem;
    }
    .due-date {
        font-size: 0.8rem;
        color: #6c757d;
        margin-top: 0.25rem;
    }
    .overdue {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


class TaskManager:
    """Manage campaign tasks with Kanban board functionality."""
    
    def __init__(self):
        self.data_path = Path("blackcore/models/json")
        self.tasks_file = self.data_path / "campaign_tasks.json"
        self.tasks = []
        self.team_members = ["John (Campaign Lead)", "Sarah (Intelligence)", "AI Assistant"]
        self.load_tasks()
    
    def load_tasks(self):
        """Load tasks from file or create defaults."""
        if self.tasks_file.exists():
            with open(self.tasks_file, 'r') as f:
                data = json.load(f)
                self.tasks = data.get('tasks', [])
        else:
            # Create default tasks from actionable_tasks.json
            actionable_file = self.data_path / "actionable_tasks.json"
            if actionable_file.exists():
                with open(actionable_file, 'r') as f:
                    data = json.load(f)
                    key = list(data.keys())[0]
                    for task in data.get(key, []):
                        self.tasks.append({
                            'id': task.get('id', str(uuid.uuid4())),
                            'title': task.get('title', 'Unknown Task'),
                            'description': task.get('description', ''),
                            'status': 'todo',
                            'priority': 'medium',
                            'assignee': self.team_members[0],
                            'due_date': (datetime.now() + timedelta(days=7)).isoformat(),
                            'created_date': datetime.now().isoformat(),
                            'tags': [],
                            'dependencies': [],
                            'progress': 0
                        })
            
            # Add some campaign-specific tasks
            campaign_tasks = [
                {
                    'id': str(uuid.uuid4()),
                    'title': 'Analyze Mayor\'s Planning Committee Connections',
                    'description': 'Deep dive into relationships between mayor and planning committee members',
                    'status': 'in_progress',
                    'priority': 'high',
                    'assignee': self.team_members[1],
                    'due_date': (datetime.now() + timedelta(days=3)).isoformat(),
                    'created_date': datetime.now().isoformat(),
                    'tags': ['investigation', 'priority'],
                    'dependencies': [],
                    'progress': 45
                },
                {
                    'id': str(uuid.uuid4()),
                    'title': 'Prepare Purdah Violation Report',
                    'description': 'Compile evidence of pre-election period violations',
                    'status': 'todo',
                    'priority': 'high',
                    'assignee': self.team_members[0],
                    'due_date': (datetime.now() + timedelta(days=5)).isoformat(),
                    'created_date': datetime.now().isoformat(),
                    'tags': ['report', 'legal'],
                    'dependencies': [],
                    'progress': 0
                },
                {
                    'id': str(uuid.uuid4()),
                    'title': 'Community Outreach - High Street',
                    'description': 'Door-to-door campaign on traffic concerns',
                    'status': 'done',
                    'priority': 'medium',
                    'assignee': self.team_members[0],
                    'due_date': (datetime.now() - timedelta(days=2)).isoformat(),
                    'created_date': (datetime.now() - timedelta(days=7)).isoformat(),
                    'tags': ['outreach', 'field'],
                    'dependencies': [],
                    'progress': 100
                }
            ]
            
            self.tasks.extend(campaign_tasks)
            self.save_tasks()
    
    def save_tasks(self):
        """Save tasks to file."""
        data = {'tasks': self.tasks}
        with open(self.tasks_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_task(self, task_data: Dict) -> str:
        """Add a new task."""
        task = {
            'id': str(uuid.uuid4()),
            'created_date': datetime.now().isoformat(),
            'progress': 0,
            'dependencies': [],
            'tags': [],
            **task_data
        }
        self.tasks.append(task)
        self.save_tasks()
        return task['id']
    
    def update_task(self, task_id: str, updates: Dict):
        """Update an existing task."""
        for task in self.tasks:
            if task['id'] == task_id:
                task.update(updates)
                self.save_tasks()
                return True
        return False
    
    def delete_task(self, task_id: str):
        """Delete a task."""
        self.tasks = [t for t in self.tasks if t['id'] != task_id]
        self.save_tasks()
    
    def get_tasks_by_status(self, status: str) -> List[Dict]:
        """Get tasks filtered by status."""
        return [t for t in self.tasks if t['status'] == status]
    
    def get_task_stats(self) -> Dict:
        """Get task statistics."""
        stats = {
            'total': len(self.tasks),
            'by_status': {'todo': 0, 'in_progress': 0, 'done': 0},
            'by_priority': {'high': 0, 'medium': 0, 'low': 0},
            'overdue': 0,
            'due_this_week': 0
        }
        
        now = datetime.now()
        week_from_now = now + timedelta(days=7)
        
        for task in self.tasks:
            # Status counts
            status = task.get('status', 'todo')
            if status in stats['by_status']:
                stats['by_status'][status] += 1
            
            # Priority counts
            priority = task.get('priority', 'medium')
            if priority in stats['by_priority']:
                stats['by_priority'][priority] += 1
            
            # Due date analysis
            if task.get('due_date') and status != 'done':
                due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                if due_date < now:
                    stats['overdue'] += 1
                elif due_date <= week_from_now:
                    stats['due_this_week'] += 1
        
        return stats


def render_task_card(task: Dict, idx: int):
    """Render a single task card."""
    priority_class = f"priority-{task.get('priority', 'medium')}"
    
    # Check if overdue
    is_overdue = False
    if task.get('due_date') and task['status'] != 'done':
        due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
        is_overdue = due_date < datetime.now().replace(tzinfo=due_date.tzinfo)
    
    with st.container():
        st.markdown(f"""
        <div class="task-card {priority_class}">
            <h5>{task['title']}</h5>
            <p style="font-size: 0.9rem; color: #6c757d;">{task.get('description', '')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Task metadata
        col1, col2 = st.columns(2)
        
        with col1:
            if task.get('assignee'):
                st.markdown(f"""
                <div class="assignee-badge">👤 {task['assignee']}</div>
                """, unsafe_allow_html=True)
        
        with col2:
            if task.get('due_date'):
                due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                due_str = due_date.strftime("%b %d")
                due_class = "overdue" if is_overdue else ""
                st.markdown(f"""
                <div class="due-date {due_class}">📅 {due_str}</div>
                """, unsafe_allow_html=True)
        
        # Progress bar
        if task.get('progress', 0) > 0:
            st.progress(task['progress'] / 100.0)
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✏️", key=f"edit_task_{idx}", help="Edit task"):
                st.session_state[f'editing_task_{idx}'] = True
        
        with col2:
            if task['status'] != 'done':
                if st.button("✓", key=f"complete_task_{idx}", help="Mark complete"):
                    task['status'] = 'done'
                    task['progress'] = 100
                    st.session_state.task_manager.save_tasks()
                    st.rerun()
        
        with col3:
            if st.button("🗑️", key=f"delete_task_{idx}", help="Delete task"):
                if st.session_state.get(f'confirm_delete_{idx}'):
                    st.session_state.task_manager.delete_task(task['id'])
                    st.rerun()
                else:
                    st.session_state[f'confirm_delete_{idx}'] = True
                    st.warning("Click again to confirm delete")


def render_kanban_board(task_manager: TaskManager):
    """Render the Kanban board view."""
    col1, col2, col3 = st.columns(3)
    
    statuses = [
        ('todo', 'To Do', col1),
        ('in_progress', 'In Progress', col2),
        ('done', 'Done', col3)
    ]
    
    for status, title, column in statuses:
        with column:
            tasks = task_manager.get_tasks_by_status(status)
            
            st.markdown(f"""
            <div class="kanban-column">
                <div class="kanban-header">{title} ({len(tasks)})</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Render tasks
            for idx, task in enumerate(tasks):
                unique_idx = f"{status}_{idx}"
                
                # Check if editing
                if st.session_state.get(f'editing_task_{unique_idx}'):
                    with st.form(key=f"edit_form_{unique_idx}"):
                        title = st.text_input("Title", value=task['title'])
                        description = st.text_area("Description", value=task.get('description', ''))
                        priority = st.selectbox("Priority", ['high', 'medium', 'low'], 
                                              index=['high', 'medium', 'low'].index(task.get('priority', 'medium')))
                        assignee = st.selectbox("Assignee", task_manager.team_members,
                                               index=task_manager.team_members.index(task.get('assignee', task_manager.team_members[0])))
                        due_date = st.date_input("Due Date", 
                                                value=datetime.fromisoformat(task.get('due_date', datetime.now().isoformat()).replace('Z', '+00:00')))
                        progress = st.slider("Progress %", 0, 100, task.get('progress', 0))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Save"):
                                task_manager.update_task(task['id'], {
                                    'title': title,
                                    'description': description,
                                    'priority': priority,
                                    'assignee': assignee,
                                    'due_date': due_date.isoformat(),
                                    'progress': progress
                                })
                                st.session_state[f'editing_task_{unique_idx}'] = False
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("Cancel"):
                                st.session_state[f'editing_task_{unique_idx}'] = False
                                st.rerun()
                else:
                    render_task_card(task, unique_idx)
                
                # Status change buttons
                if not st.session_state.get(f'editing_task_{unique_idx}'):
                    button_col1, button_col2 = st.columns(2)
                    
                    if status == 'todo':
                        with button_col2:
                            if st.button("→", key=f"move_right_{unique_idx}", help="Move to In Progress"):
                                task_manager.update_task(task['id'], {'status': 'in_progress'})
                                st.rerun()
                    
                    elif status == 'in_progress':
                        with button_col1:
                            if st.button("←", key=f"move_left_{unique_idx}", help="Move to To Do"):
                                task_manager.update_task(task['id'], {'status': 'todo'})
                                st.rerun()
                        
                        with button_col2:
                            if st.button("→", key=f"move_right2_{unique_idx}", help="Move to Done"):
                                task_manager.update_task(task['id'], {'status': 'done', 'progress': 100})
                                st.rerun()
                    
                    elif status == 'done':
                        with button_col1:
                            if st.button("←", key=f"move_left2_{unique_idx}", help="Move to In Progress"):
                                task_manager.update_task(task['id'], {'status': 'in_progress'})
                                st.rerun()


def create_burndown_chart(task_manager: TaskManager) -> go.Figure:
    """Create a burndown chart for campaign tasks."""
    # Calculate daily task completion over past 14 days
    now = datetime.now()
    dates = pd.date_range(end=now, periods=14, freq='D')
    
    # Mock data for demonstration
    total_tasks = len(task_manager.tasks)
    remaining_tasks = []
    completed_tasks = []
    
    for i, date in enumerate(dates):
        # Simulate task completion
        completed = min(i * 2, total_tasks * 0.6)
        remaining = total_tasks - completed
        
        remaining_tasks.append(remaining)
        completed_tasks.append(completed)
    
    fig = go.Figure()
    
    # Ideal burndown line
    fig.add_trace(go.Scatter(
        x=dates,
        y=[total_tasks - (i * total_tasks / 14) for i in range(14)],
        mode='lines',
        name='Ideal',
        line=dict(dash='dash', color='gray')
    ))
    
    # Actual remaining tasks
    fig.add_trace(go.Scatter(
        x=dates,
        y=remaining_tasks,
        mode='lines+markers',
        name='Remaining',
        line=dict(color='#e74c3c')
    ))
    
    # Completed tasks
    fig.add_trace(go.Scatter(
        x=dates,
        y=completed_tasks,
        mode='lines+markers',
        name='Completed',
        line=dict(color='#27ae60')
    ))
    
    fig.update_layout(
        title="Campaign Task Burndown Chart",
        xaxis_title="Date",
        yaxis_title="Number of Tasks",
        height=400,
        hovermode='x unified'
    )
    
    return fig


def main():
    """Main task management interface."""
    st.title("✅ Campaign Task Management")
    st.markdown("*Organize and track campaign activities with Kanban board*")
    
    # Initialize task manager
    if 'task_manager' not in st.session_state:
        st.session_state.task_manager = TaskManager()
    
    task_manager = st.session_state.task_manager
    
    # Get statistics
    stats = task_manager.get_task_stats()
    
    # Quick stats row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Tasks", stats['total'])
    
    with col2:
        st.metric("To Do", stats['by_status']['todo'])
    
    with col3:
        st.metric("In Progress", stats['by_status']['in_progress'])
    
    with col4:
        st.metric("Completed", stats['by_status']['done'])
    
    with col5:
        st.metric("Overdue", stats['overdue'], 
                 delta=f"-{stats['overdue']}" if stats['overdue'] > 0 else "0",
                 delta_color="inverse")
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Kanban Board", "➕ New Task", "📊 Analytics", "👥 Team View"])
    
    with tab1:
        # Kanban board view
        st.markdown("### Campaign Task Board")
        
        # Quick filters
        filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])
        
        with filter_col1:
            priority_filter = st.selectbox(
                "Filter by Priority",
                ["All", "High", "Medium", "Low"],
                key="priority_filter"
            )
        
        with filter_col2:
            assignee_filter = st.selectbox(
                "Filter by Assignee",
                ["All"] + task_manager.team_members,
                key="assignee_filter"
            )
        
        # Apply filters
        filtered_tasks = task_manager.tasks
        
        if priority_filter != "All":
            filtered_tasks = [t for t in filtered_tasks if t.get('priority', '').lower() == priority_filter.lower()]
        
        if assignee_filter != "All":
            filtered_tasks = [t for t in filtered_tasks if t.get('assignee') == assignee_filter]
        
        # Update task manager temporarily with filtered tasks
        original_tasks = task_manager.tasks
        task_manager.tasks = filtered_tasks
        
        # Render Kanban board
        render_kanban_board(task_manager)
        
        # Restore original tasks
        task_manager.tasks = original_tasks
    
    with tab2:
        # Add new task form
        st.markdown("### Create New Task")
        
        with st.form("new_task_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Task Title", placeholder="Enter task title...")
                description = st.text_area("Description", placeholder="Describe the task...")
                priority = st.selectbox("Priority", ["high", "medium", "low"])
            
            with col2:
                assignee = st.selectbox("Assign To", task_manager.team_members)
                due_date = st.date_input("Due Date", min_value=datetime.now().date())
                tags = st.text_input("Tags (comma-separated)", placeholder="e.g., urgent, investigation")
            
            submitted = st.form_submit_button("Create Task", type="primary")
            
            if submitted and title:
                task_data = {
                    'title': title,
                    'description': description,
                    'status': 'todo',
                    'priority': priority,
                    'assignee': assignee,
                    'due_date': due_date.isoformat(),
                    'tags': [tag.strip() for tag in tags.split(',') if tag.strip()]
                }
                
                task_id = task_manager.add_task(task_data)
                st.success(f"✅ Task created successfully!")
                st.balloons()
                
                # Clear form
                st.rerun()
            elif submitted:
                st.error("Please enter a task title")
    
    with tab3:
        # Analytics view
        st.markdown("### Task Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Priority distribution
            priority_data = pd.DataFrame([
                {'Priority': k.title(), 'Count': v} 
                for k, v in stats['by_priority'].items()
            ])
            
            fig_priority = px.pie(
                priority_data,
                values='Count',
                names='Priority',
                title="Tasks by Priority",
                color_discrete_map={
                    'High': '#dc3545',
                    'Medium': '#ffc107',
                    'Low': '#28a745'
                }
            )
            
            st.plotly_chart(fig_priority, use_container_width=True)
        
        with col2:
            # Status distribution
            status_data = pd.DataFrame([
                {'Status': k.replace('_', ' ').title(), 'Count': v}
                for k, v in stats['by_status'].items()
            ])
            
            fig_status = px.bar(
                status_data,
                x='Status',
                y='Count',
                title="Tasks by Status",
                color='Status',
                color_discrete_map={
                    'Todo': '#6c757d',
                    'In Progress': '#ffc107',
                    'Done': '#28a745'
                }
            )
            
            st.plotly_chart(fig_status, use_container_width=True)
        
        # Burndown chart
        st.markdown("### Campaign Progress")
        burndown_fig = create_burndown_chart(task_manager)
        st.plotly_chart(burndown_fig, use_container_width=True)
        
        # Upcoming deadlines
        st.markdown("### 📅 Upcoming Deadlines")
        
        upcoming_tasks = []
        now = datetime.now()
        
        for task in task_manager.tasks:
            if task.get('due_date') and task['status'] != 'done':
                due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                days_until = (due_date.replace(tzinfo=None) - now).days
                
                if days_until <= 7:
                    upcoming_tasks.append({
                        'Task': task['title'],
                        'Assignee': task.get('assignee', 'Unassigned'),
                        'Due Date': due_date.strftime('%b %d'),
                        'Days Until': days_until,
                        'Priority': task.get('priority', 'medium').title()
                    })
        
        if upcoming_tasks:
            df_upcoming = pd.DataFrame(upcoming_tasks)
            df_upcoming = df_upcoming.sort_values('Days Until')
            
            st.dataframe(
                df_upcoming,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Days Until": st.column_config.NumberColumn(
                        "Days Until",
                        help="Days until due date",
                        format="%d"
                    )
                }
            )
        else:
            st.info("No tasks due in the next 7 days")
    
    with tab4:
        # Team view
        st.markdown("### Team Workload")
        
        # Calculate workload per team member
        workload = {}
        for member in task_manager.team_members:
            member_tasks = [t for t in task_manager.tasks if t.get('assignee') == member]
            workload[member] = {
                'total': len(member_tasks),
                'todo': sum(1 for t in member_tasks if t['status'] == 'todo'),
                'in_progress': sum(1 for t in member_tasks if t['status'] == 'in_progress'),
                'done': sum(1 for t in member_tasks if t['status'] == 'done')
            }
        
        # Display team cards
        cols = st.columns(len(task_manager.team_members))
        
        for idx, (member, stats) in enumerate(workload.items()):
            with cols[idx]:
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                    <h4>👤 {member}</h4>
                    <p><strong>{stats['total']}</strong> Total Tasks</p>
                    <p>📝 To Do: {stats['todo']}</p>
                    <p>🔄 In Progress: {stats['in_progress']}</p>
                    <p>✅ Completed: {stats['done']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Progress
                if stats['total'] > 0:
                    completion_rate = stats['done'] / stats['total']
                    st.progress(completion_rate)
                    st.caption(f"{completion_rate:.0%} Complete")


if __name__ == "__main__":
    main()