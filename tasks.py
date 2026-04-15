import sqlite3
import datetime

def add_task(task, due_date, due_time, user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Combine date and time into datetime string
    due_datetime_str = f"{due_date}T{due_time}"

    # Calculate priority based on due date
    due_dt = datetime.datetime.fromisoformat(due_datetime_str)
    now = datetime.datetime.now()
    diff_hours = (due_dt - now).total_seconds() / 3600
    if diff_hours <= 24:
        priority = 'high'
    elif diff_hours <= 48:
        priority = 'medium'
    else:
        priority = 'low'

    cursor.execute("INSERT INTO tasks (task, status, due_date, priority, user_id) VALUES (?, ?, ?, ?, ?)", (task, "pending", due_datetime_str, priority, user_id))

    conn.commit()
    conn.close()

def get_tasks(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()

    conn.close()
    return tasks

def get_top_priority_tasks(limit=5, user_id=None):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Priority order: high, medium, low
    if user_id:
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE status = 'pending' AND user_id = ?
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END, 
                due_date ASC
            LIMIT ?
        """, (user_id, limit))
    else:
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE status = 'pending'
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END, 
                due_date ASC
            LIMIT ?
        """, (limit,))
    
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def add_job_application(job_name, reference_number, status, user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO job_applications (job_name, reference_number, status, user_id) VALUES (?, ?, ?, ?)", (job_name, reference_number, status, user_id))

    conn.commit()
    conn.close()

def get_job_applications(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM job_applications WHERE user_id = ?", (user_id,))
    jobs = cursor.fetchall()

    conn.close()
    return jobs

def update_job_status(id, status, user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE job_applications SET status = ? WHERE id = ? AND user_id = ?", (status, id, user_id))

    conn.commit()
    conn.close()

def delete_job_application(id, user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM job_applications WHERE id = ? AND user_id = ?", (id, user_id))

    conn.commit()
    conn.close()

def delete_all_job_applications(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM job_applications WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

def get_analytics_data(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Get task statistics
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(*) as total
        FROM tasks 
        WHERE user_id = ?
    """, (user_id,))
    
    task_stats = cursor.fetchone()
    tasks_pending = task_stats[0] or 0
    tasks_completed = task_stats[1] or 0
    total_tasks = task_stats[2] or 0
    
    # Completion rate
    completion_rate = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 0
    
    # Applications sent
    cursor.execute("SELECT COUNT(*) FROM job_applications WHERE user_id = ?", (user_id,))
    applications_sent = cursor.fetchone()[0] or 0
    
    # Task completion projection based on urgency and due date
    cursor.execute("""
        SELECT task, priority, due_date, due_time 
        FROM tasks 
        WHERE user_id = ? AND status = 'pending'
        ORDER BY 
            CASE priority 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                WHEN 'low' THEN 3 
            END, 
            due_date ASC
    """, (user_id,))
    
    pending_tasks = cursor.fetchall()
    
    # Calculate projection (simplified: assume 2 tasks per day completion rate)
    now = datetime.datetime.now()
    projection_data = []
    current_date = now.date()
    tasks_per_day = 2
    
    for i, task in enumerate(pending_tasks):
        days_to_complete = (i // tasks_per_day) + 1
        projected_date = current_date + datetime.timedelta(days=days_to_complete)
        projection_data.append({
            'task': task[0],
            'priority': task[1],
            'due_date': task[2],
            'projected_completion': projected_date.isoformat()
        })
    
    conn.close()
    
    return {
        'tasks_completed': tasks_completed,
        'tasks_pending': tasks_pending,
        'completion_rate': round(completion_rate, 1),
        'applications_sent': applications_sent,
        'projection_data': projection_data
    }