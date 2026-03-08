import sqlite3
import datetime

def add_task(task, due_date, due_time):
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

    cursor.execute("INSERT INTO tasks (task, status, due_date, priority) VALUES (?, ?, ?, ?)", (task, "pending", due_datetime_str, priority))

    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()

    conn.close()
    return tasks

def get_top_priority_tasks(limit=5):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Priority order: high, medium, low
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

def add_job_application(job_name, reference_number, status):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO job_applications (job_name, reference_number, status) VALUES (?, ?, ?)", (job_name, reference_number, status))

    conn.commit()
    conn.close()

def get_job_applications():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM job_applications")
    jobs = cursor.fetchall()

    conn.close()
    return jobs

def update_job_status(id, status):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE job_applications SET status = ? WHERE id = ?", (status, id))

    conn.commit()
    conn.close()

def delete_job_application(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM job_applications WHERE id = ?", (id,))

    conn.commit()
    conn.close()

def delete_all_job_applications():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM job_applications")

    conn.commit()
    conn.close()