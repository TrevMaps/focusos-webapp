import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for
from tasks import get_tasks, add_task, get_job_applications, add_job_application, update_job_status, get_top_priority_tasks, delete_job_application, delete_all_job_applications
from assistant import ask_ai, speak

# Initialize database
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    task TEXT,
    status TEXT,
    priority INTEGER
)
""")
try:
    cursor.execute("ALTER TABLE tasks ADD COLUMN priority INTEGER")
except:
    pass

cursor.execute("""
CREATE TABLE IF NOT EXISTS job_applications (
    id INTEGER PRIMARY KEY,
    job_name TEXT,
    reference_number TEXT,
    status TEXT
)
""")

conn.commit()
conn.close()

app = Flask(__name__)

@app.route("/")
def summary_dashboard():
    top_tasks = get_top_priority_tasks(5)
    return render_template("summary_dashboard.html", top_tasks=top_tasks)

@app.route("/tasks")
def dashboard():
    tasks = get_tasks()
    answer = request.args.get('answer', None)
    return render_template("dashboard.html", tasks=tasks, answer=answer)

@app.route("/add_task", methods=["POST"])
def add_task_route():
    task = request.form.get("task")
    due_date = request.form.get("due_date")
    due_time = request.form.get("due_time")
    if task and due_date and due_time:
        add_task(task, due_date, due_time)
    return redirect(url_for('dashboard'))

@app.route("/complete/<int:id>", methods=["POST"])
def complete(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route("/ask", methods=["POST"])
def ask_route():
    question = request.form.get("question")
    if question:
        answer = ask_ai(question)
        return redirect(url_for('dashboard', answer=answer))
    return redirect(url_for('dashboard'))

@app.route("/speak/<path:text>")
def speak_route(text):
    speak(text)
    return redirect(url_for('summary_dashboard'))

@app.route("/job_applications")
def job_applications():
    jobs = get_job_applications()
    return render_template("job_applications.html", jobs=jobs)

@app.route("/add_job", methods=["POST"])
def add_job_route():
    job_name = request.form.get("job_name")
    reference_number = request.form.get("reference_number")
    status = request.form.get("status")
    if job_name and reference_number and status:
        add_job_application(job_name, reference_number, status)
    return redirect(url_for('job_applications'))

@app.route("/update_job_status/<int:id>", methods=["POST"])
def update_job_status_route(id):
    status = request.form.get("status")
    if status:
        update_job_status(id, status)
    return redirect(url_for('job_applications'))

@app.route("/delete_job/<int:id>", methods=["POST"])
def delete_job_route(id):
    delete_job_application(id)
    return {'status': 'success'}, 200

@app.route("/delete_all_jobs", methods=["POST"])
def delete_all_jobs_route():
    delete_all_job_applications()
    return {'status': 'success'}, 200


# Run Flask (for Render deployment)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)