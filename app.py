import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from tasks import get_tasks, add_task, get_job_applications, add_job_application, update_job_status, get_top_priority_tasks, delete_job_application, delete_all_job_applications, get_analytics_data
from assistant import ask_ai, speak

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

# Initialize database
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
)
""")

# Modify tasks table to include user_id
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks_new (
    id INTEGER PRIMARY KEY,
    task TEXT,
    status TEXT,
    priority INTEGER,
    due_date TEXT,
    due_time TEXT,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

# Check if tasks table has user_id column, if not, migrate data
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
if cursor.fetchone():
    cursor.execute("PRAGMA table_info(tasks)")
    columns = cursor.fetchall()
    has_user_id = any(col[1] == 'user_id' for col in columns)

    if not has_user_id:
        # Migrate existing data to new table
        cursor.execute("INSERT INTO tasks_new (id, task, status, priority, due_date, due_time) SELECT id, task, status, priority, due_date, due_time FROM tasks")
        cursor.execute("DROP TABLE tasks")
        cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")
else:
    # If tasks table doesn't exist, just rename tasks_new to tasks
    cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")

# Modify job_applications table to include user_id
cursor.execute("""
CREATE TABLE IF NOT EXISTS job_applications_new (
    id INTEGER PRIMARY KEY,
    job_name TEXT,
    reference_number TEXT,
    status TEXT,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

# Check if job_applications table has user_id column
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_applications'")
if cursor.fetchone():
    cursor.execute("PRAGMA table_info(job_applications)")
    columns = cursor.fetchall()
    has_user_id_jobs = any(col[1] == 'user_id' for col in columns)

    if not has_user_id_jobs:
        # Migrate existing data to new table
        cursor.execute("INSERT INTO job_applications_new (id, job_name, reference_number, status) SELECT id, job_name, reference_number, status FROM job_applications")
        cursor.execute("DROP TABLE job_applications")
        cursor.execute("ALTER TABLE job_applications_new RENAME TO job_applications")
else:
    # If job_applications table doesn't exist, just rename job_applications_new to job_applications
    cursor.execute("ALTER TABLE job_applications_new RENAME TO job_applications")

conn.commit()
conn.close()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required')
            return redirect(url_for('register'))
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            flash('Username already exists')
            return redirect(url_for('register'))
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], user_data[2])
            login_user(user)
            return redirect(url_for('summary_dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/")
@login_required
def summary_dashboard():
    top_tasks = get_top_priority_tasks(5, current_user.id)
    data = get_analytics_data(current_user.id)
    return render_template("dashboard_main.html", top_tasks=top_tasks, **data)

@app.route("/tasks")
@login_required
def dashboard():
    tasks = get_tasks(current_user.id)
    answer = request.args.get('answer', None)
    return render_template("tasks.html", tasks=tasks, answer=answer)

@app.route("/add_task", methods=["POST"])
@login_required
def add_task_route():
    task = request.form.get("task")
    due_date = request.form.get("due_date")
    due_time = request.form.get("due_time")
    if task and due_date and due_time:
        add_task(task, due_date, due_time, current_user.id)
    return redirect(url_for('dashboard'))

@app.route("/complete/<int:id>", methods=["POST"])
@login_required
def complete(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ? AND user_id = ?", (id, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route("/ask", methods=["POST"])
@login_required
def ask_route():
    question = request.form.get("question")
    if question:
        answer = ask_ai(question)
        return redirect(url_for('dashboard', answer=answer))
    return redirect(url_for('dashboard'))

@app.route("/speak/<path:text>")
@login_required
def speak_route(text):
    speak(text)
    return redirect(url_for('summary_dashboard'))

@app.route("/job_applications")
@login_required
def job_applications():
    jobs = get_job_applications(current_user.id)
    return render_template("job_applications.html", jobs=jobs)

@app.route("/add_job", methods=["POST"])
@login_required
def add_job_route():
    job_name = request.form.get("job_name")
    reference_number = request.form.get("reference_number")
    status = request.form.get("status")
    if job_name and reference_number and status:
        add_job_application(job_name, reference_number, status, current_user.id)
    return redirect(url_for('job_applications'))

@app.route("/update_job_status/<int:id>", methods=["POST"])
@login_required
def update_job_status_route(id):
    print(f"DEBUG: update_job_status called with id={id}, user_id={current_user.id}")
    print(f"DEBUG: Request form data: {request.form}")
    status = request.form.get("status")
    print(f"DEBUG: Status from form: {status}")
    if status:
        try:
            update_job_status(id, status, current_user.id)
            print(f"DEBUG: Successfully updated job {id} to {status}")
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            print(f"DEBUG: Error updating: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    print("DEBUG: No status provided in request")
    return jsonify({'status': 'error', 'message': 'No status provided'}), 400

@app.route("/delete_job/<int:id>", methods=["POST"])
@login_required
def delete_job_route(id):
    delete_job_application(id, current_user.id)
    return jsonify({'status': 'success'}), 200

@app.route("/delete_all_jobs", methods=["POST"])
@login_required
def delete_all_jobs_route():
    delete_all_job_applications(current_user.id)
    return jsonify({'status': 'success'}), 200


@app.route("/analytics")
@login_required
def analytics():
    data = get_analytics_data(current_user.id)
    return render_template("analytics.html", **data)


@app.route("/voice_command", methods=["POST"])
@login_required
def voice_command():
    import json
    import datetime
    
    data = request.get_json()
    command = data.get('command', '').lower().strip()
    
    result = {'success': False, 'message': '', 'action': None}
    
    # Parse voice command
    if 'add task' in command or 'create task' in command:
        # Extract task details from command
        # Format: "Add Task [task name] [date] [time]"
        # Example: "Add Task Clean tomorrow 15:30"
        parts = command.split()
        
        if len(parts) >= 4:
            task_name = ' '.join(parts[2:-2])
            date_str = parts[-2]
            time_str = parts[-1]
            
            # Convert relative dates
            today = datetime.date.today()
            if date_str.lower() == 'today':
                date_obj = today
            elif date_str.lower() == 'tomorrow':
                date_obj = today + datetime.timedelta(days=1)
            elif date_str.lower() == 'next week':
                date_obj = today + datetime.timedelta(days=7)
            else:
                try:
                    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    date_obj = today
            
            try:
                add_task(task_name, date_obj.isoformat(), time_str, current_user.id)
                result['success'] = True
                result['message'] = f'Task "{task_name}" added for {date_obj.strftime("%B %d")} at {time_str}'
                result['action'] = 'add_task'
            except Exception as e:
                result['message'] = f'Error adding task: {str(e)}'
        else:
            result['message'] = 'Please provide task name, date, and time'
    
    elif 'show tasks' in command or 'list tasks' in command:
        tasks = get_tasks(current_user.id)
        result['success'] = True
        result['message'] = f'You have {len(tasks)} tasks'
        result['action'] = 'show_tasks'
        result['redirect'] = '/tasks'
    
    elif 'show analytics' in command or 'analytics' in command:
        result['success'] = True
        result['message'] = 'Showing analytics dashboard'
        result['action'] = 'show_analytics'
        result['redirect'] = '/analytics'
    
    elif 'show applications' in command or 'job applications' in command:
        result['success'] = True
        result['message'] = 'Showing job applications'
        result['action'] = 'show_applications'
        result['redirect'] = '/job_applications'
    
    elif 'show dashboard' in command or 'home' in command:
        result['success'] = True
        result['message'] = 'Showing dashboard'
        result['action'] = 'show_dashboard'
        result['redirect'] = '/'
    
    else:
        result['message'] = 'Command not recognized. Try "Add Task", "Show Tasks", or "Show Analytics"'
    
    return jsonify(result)



# Run Flask (for Render deployment)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)