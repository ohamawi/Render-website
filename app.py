# =========================================================
# IMPORTS
# =========================================================

# Flask tools for routing, forms, sessions, and redirects
from flask import Flask, render_template_string, request, redirect, session

# Used to pull the current system date/month for automatic recurring logic
from datetime import datetime

# Used for checking environment ports and paths
import os

# SQLite database driver
import sqlite3

# =========================================================
# CREATE FLASK APP
# =========================================================

app = Flask(__name__)

# Secret key used for login sessions
app.secret_key = "supersecretkey"

# Database Configuration - using absolute paths to keep Render happy
try:
    # This works when running as a normal script (like on Render)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
except NameError:
    # This kicks in if you're testing inside a Jupyter Notebook or REPL
    BASE_DIR = os.path.abspath(os.getcwd())

DB_FILE = os.path.join(BASE_DIR, "app.db")


# =========================================================
# SQLITE DATABASE INITIALIZATION
# =========================================================

# Sets up the database file and builds tables if they don't exist yet.
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    
    # 2. Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            description TEXT,
            category TEXT,
            amount REAL,
            is_income INTEGER
        )
    """)
    
    # 3. Recurring Templates table (NEW for Feature 3)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            day_of_month INTEGER,
            description TEXT,
            category TEXT,
            amount REAL,
            is_income INTEGER,
            last_generated TEXT  -- Tracked as 'YYYY-MM'
        )
    """)
    
    # 4. Journal table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            title TEXT,
            content TEXT
        )
    """)
    
    # 5. Schedule table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            time TEXT,
            title TEXT,
            description TEXT
        )
    """)
    
    # Seed default users if the user table is totally empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            [("admin", "pass"), ("user", "pass2")]
        )
        conn.commit()
        
    conn.close()


# Quick helper to open a connection to our database file with dictionary rows.
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# RUN DB INITIALIZATION OUT IN THE OPEN
# =========================================================
# Moving this outside the main block guarantees Gunicorn builds your 
# tables instantly on startup when deployed to production servers like Render!
init_db()


# =========================================================
# TRANSACTION CATEGORIES
# =========================================================

# True = income category, False = expense category
CATEGORIES = {
    "Salary": True,
    "Freelance": True,
    "Other Income": True,
    "Food": False,
    "Rent": False,
    "Utilities": False,
    "Entertainment": False
}


# =========================================================
# LOGIN CHECK
# =========================================================

# Simple utility to check if a user is currently logged into the session.
def is_logged_in():
    return session.get("logged_in") and session.get("user")


# =========================================================
# AUTOMATIC RECURRING TRANSACTION ENGINE (FEATURE 3)
# =========================================================

# Checks if any recurring templates for this user haven't been copied over 
# into the transactions ledger yet for the current calendar month.
def process_recurring_transactions(user):
    current_month = datetime.now().strftime("%Y-%m")  # Formats as '2026-06'
    conn = get_db_connection()
    
    # Grab templates that haven't run yet this month
    templates = conn.execute("""
        SELECT * FROM recurring_templates 
        WHERE username = ? AND (last_generated IS NULL OR last_generated != ?)
    """, (user, current_month)).fetchall()
    
    for t in templates:
        # Build out a pristine date string using this month and the template's specified day
        day_str = str(t["day_of_month"]).zfill(2)
        target_date = f"{current_month}-{day_str}"
        
        # Double check to prevent overlapping duplicates
        exists = conn.execute("""
            SELECT 1 FROM transactions 
            WHERE username = ? AND date = ? AND description = ? AND amount = ?
        """, (user, target_date, t["description"], t["amount"])).fetchone()
        
        if not exists:
            conn.execute("""
                INSERT INTO transactions (username, date, description, category, amount, is_income)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user, target_date, t["description"], t["category"], t["amount"], t["is_income"]))
            
        # Mark this month as completed for this specific template line
        conn.execute("UPDATE recurring_templates SET last_generated = ? WHERE id = ?", (current_month, t["id"]))
        
    conn.commit()
    conn.close()


# =========================================================
# DATA RETRIEVAL HELPERS
# =========================================================

# Grabs all the journal entries written by the logged-in user.
def load_journal():
    user = session.get("user")
    if not user:
        return []
    conn = get_db_connection()
    rows = conn.execute("SELECT date, title, content FROM journal WHERE username = ? ORDER BY date DESC", (user,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Grabs all the calendar/schedule events saved by the logged-in user.
def load_schedule():
    user = session.get("user")
    if not user:
        return []
    conn = get_db_connection()
    rows = conn.execute("SELECT date, time, title, description FROM schedule WHERE username = ? ORDER BY date ASC, time ASC", (user,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =========================================================
# SHARED MODERN CSS & JS (WITH CHART.JS IMPORTED)
# =========================================================

SHARED_HEAD = """
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-app: #f4f6f9;
            --bg-card: #ffffff;
            --text-main: #2d3748;
            --text-muted: #718096;
            --border-color: #e2e8f0;
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --income: #10b981;
            --expense: #ef4444;
        }
        body.dark-mode {
            --bg-app: #0f172a;
            --bg-card: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
        }
        body {
            background-color: var(--bg-app);
            color: var(--text-main);
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 0;
            transition: background-color 0.2s, color 0.2s;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
        }
        .app-container {
            width: 100%;
            max-width: 850px;
            margin: 2rem 1rem;
            background: var(--bg-card);
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -4px rgba(0,0,0,0.05);
            border: 1px solid var(--border-color);
            position: relative;
        }
        .theme-toggle {
            position: absolute;
            top: 1.5rem;
            right: 1.5rem;
            background: var(--border-color);
            border: none;
            color: var(--text-main);
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
        }
        h1, h2, h3 { color: var(--text-main); margin-top: 0; }
        a { color: var(--primary); text-decoration: none; font-weight: 500; }
        a:hover { text-decoration: underline; }
        input, select, textarea {
            width: 100%;
            padding: 0.75rem;
            margin-bottom: 1.25rem;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-app);
            color: var(--text-main);
            box-sizing: border-box;
            font-size: 1rem;
        }
        input:focus, select:focus, textarea:focus {
            outline: 2px solid var(--primary);
        }
        button[type="submit"] {
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            width: 100%;
            transition: background 0.2s;
        }
        button[type="submit"]:hover { background: var(--primary-hover); }
        
        /* Inline styling additions for the search layout and templates boxes */
        .checkbox-container {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1.25rem;
        }
        .checkbox-container input {
            width: auto;
            margin-bottom: 0;
            cursor: pointer;
        }
        .filter-bar {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }
        .filter-bar input, .filter-bar select {
            margin-bottom: 0;
        }
        .chart-container {
            background: var(--bg-app);
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            margin: 1.5rem 0;
            display: flex;
            justify-content: center;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin: 1.5rem 0;
        }
        .summary-card {
            background: var(--bg-app);
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
            border: 1px solid var(--border-color);
        }
        .summary-card h4 { margin: 0 0 0.5rem 0; color: var(--text-muted); font-size: 0.875rem; text-transform: uppercase; }
        .summary-card p { margin: 0; font-size: 1.25rem; font-weight: 700; }
        .val-income { color: var(--income); }
        .val-expense { color: var(--expense); }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-color); text-align: left; }
        th { background-color: var(--bg-app); color: var(--text-muted); font-weight: 600; }
        .card-list-item {
            border: 1px solid var(--border-color);
            padding: 1.25rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            background: var(--bg-app);
        }
        .nav-links { display: flex; gap: 1rem; margin-bottom: 1.5rem; font-size: 0.95rem; }
    </style>
</head>
<button class="theme-toggle" onclick="toggleTheme()">🌓 Toggle Mode</button>
<script>
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
    }
    function toggleTheme() {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
        // Let the chart update colors if it exists on the active dashboard page
        if (typeof renderChart === 'function') { renderChart(); }
    }
</script>
"""


# =========================================================
# HTML TEMPLATES
# =========================================================

LOGIN_HTML = SHARED_HEAD + """
<div class="app-container">
    <h2>Login</h2>
    <form method="POST">
        <input name="username" placeholder="Username" required>
        <input name="password" type="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    <br>
    <a href="/register">Create Account</a>
    <p style="color:red;">{{ error }}</p>
</div>
"""

REGISTER_HTML = SHARED_HEAD + """
<div class="app-container">
    <h2>Create Account</h2>
    <form method="POST">
        <input name="username" placeholder="New Username" required>
        <input name="password" type="password" placeholder="New Password" required>
        <button type="submit">Create Account</button>
    </form>
    <br>
    <a href="/">Back to Login</a>
    <p style="color:red;">{{ error }}</p>
</div>
"""

MAIN_HTML = SHARED_HEAD + """
<div class="app-container">
    <h1>Finance Tracker</h1>
    <p>Logged in as: <strong>{{ user }}</strong></p>
    
    <div class="nav-links">
        <a href="/journal">📝 Open Journal</a>
        <a href="/schedule">📅 Open Scheduler</a>
        <a href="/logout" style="margin-left: auto; color: var(--text-muted);">Logout</a>
    </div>
    
    <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;">
    
    <h3>Summary</h3>
    <div class="summary-grid">
        <div class="summary-card">
            <h4>Income</h4>
            <p class="val-income">${{ income }}</p>
        </div>
        <div class="summary-card">
            <h4>Expenses</h4>
            <p class="val-expense">${{ expenses }}</p>
        </div>
        <div class="summary-card">
            <h4>Balance</h4>
            <p>${{ balance }}</p>
        </div>
    </div>
    
    <h3>Expense Breakdown</h3>
    <div class="chart-container">
        <canvas id="expenseChart" style="max-height: 220px; max-width: 400px;"></canvas>
    </div>
    
    <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;">
    
    <h3>Add Transaction</h3>
    <form method="POST" action="/add">
        <input name="description" placeholder="Description" required>
        <select name="category">
            {% for c in categories %}
                <option>{{ c }}</option>
            {% endfor %}
        </select>
        <input type="number" step="0.01" name="amount" placeholder="Amount" required>
        <input type="date" name="date" required>
        
        <div class="checkbox-container">
            <input type="checkbox" name="is_recurring" id="is_recurring">
            <label for="is_recurring">Repeat monthly on this day</label>
        </div>
        
        <button type="submit">Add Transaction</button>
    </form>
    
    <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;">
    
    <h3>Transactions</h3>
    
    <form method="GET" action="/dashboard" class="filter-bar">
        <input name="search" value="{{ search_query }}" placeholder="Search descriptions..." style="flex: 2;">
        <select name="filter_category" style="flex: 1;">
            <option value="">All Categories</option>
            {% for c in categories %}
                <option value="{{ c }}" {% if c == selected_category %}selected{% endif %}>{{ c }}</option>
            {% endfor %}
        </select>
        <button type="submit" style="width: auto; padding: 0 1.25rem;">Filter</button>
        {% if search_query or selected_category %}
            <a href="/dashboard" style="background: var(--border-color); color: var(--text-main); padding: 0.75rem 1rem; border-radius: 6px; display: flex; align-items: center; justify-content: center; text-decoration: none;">Clear</a>
        {% endif %}
    </form>
    
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                <th>Amount</th>
                <th>Edit</th>
            </tr>
        </thead>
        <tbody>
            {% for t in transactions %}
            <tr>
                <td>{{ t.date }}</td>
                <td>{{ t.description }}</td>
                <td>{{ t.category }}</td>
                <td class="{% if t.is_income %}val-income{% else %}val-expense{% endif %}">
                    {% if t.is_income %}+{% else %}-{% endif %}${{ t.amount }}
                </td>
                <td><a href="/edit/{{ loop.index0 }}">Edit</a></td>
            </tr>
            {% else %}
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No matching logs found.</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<script>
    let globalChartInstance = null;

    function renderChart() {
        const ctx = document.getElementById('expenseChart').getContext('2d');
        const labels = {{ chart_labels | tojson }};
        const dataValues = {{ chart_values | tojson }};
        const isDark = document.body.classList.contains('dark-mode');
        
        if (globalChartInstance) { globalChartInstance.destroy(); }
        
        if (labels.length === 0) {
            globalChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['No Data Available'],
                    datasets: [{ data: [1], backgroundColor: [isDark ? '#334155' : '#e2e8f0'] }]
                },
                options: {
                    plugins: { legend: { labels: { color: isDark ? '#94a3b8' : '#718096' } } }
                }
            });
            return;
        }

        globalChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: ['#4f46e5', '#10b981', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899'],
                    borderWidth: 0
                }]
            },
            options: {
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: isDark ? '#f8fafc' : '#2d3748' }
                    }
                }
            });
    }
    
    // Fire off chart calculation on initial viewport render pass
    renderChart();
</script>
"""

EDIT_HTML = SHARED_HEAD + """
<div class="app-container">
    <h2>Edit Transaction</h2>
    <p>Editing options are currently being initialized. <a href="/dashboard">Return to Dashboard</a></p>
</div>
"""

JOURNAL_HTML = SHARED_HEAD + """
<div class="app-container">
    <h1>Journal</h1>
    <a href="/dashboard">← Back to Dashboard</a>
    <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;">
    
    <form method="POST" action="/journal/add">
        <input type="date" name="date" required>
        <input name="title" placeholder="Entry Title" required>
        <textarea name="content" rows="6" placeholder="Write your thoughts here..." required></textarea>
        <button type="submit">Save Entry</button>
    </form>
    
    <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;">
    
    {% for entry in entries %}
    <div class="card-list-item">
        <h3 style="margin-bottom: 0.25rem;">{{ entry.title }}</h3>
        <small style="color: var(--text-muted); display: block; margin-bottom: 1rem;">{{ entry.date }}</small>
        <p style="margin: 0; white-space: pre-wrap;">{{ entry.content }}</p>
    </div>
    {% endfor %}
</div>
"""

SCHEDULE_HTML = SHARED_HEAD + """
<div class="app-container">
    <h1>Scheduler</h1>
    <a href="/dashboard">← Back to Dashboard</a>
    <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;">
    
    <form method="POST" action="/schedule/add">
        <input type="date" name="date" required>
        <input type="time" name="time" required>
        <input name="title" placeholder="Event Title" required>
        <textarea name="description" rows="4" placeholder="Event Description"></textarea>
        <button type="submit">Add Event</button>
    </form>
    
    <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;">
    
    {% for event in events %}
    <div class="card-list-item">
        <h3 style="margin-bottom: 0.25rem;">{{ event.title }}</h3>
        <small style="color: var(--text-muted); display: block; margin-bottom: 1rem;">🗓️ {{ event.date }} at {{ event.time }}</small>
        <p style="margin: 0; white-space: pre-wrap;">{{ event.description }}</p>
    </div>
    {% endfor %}
</div>
"""


# =========================================================
# ROUTE ACTIONS
# =========================================================

# Handles the login route. Shows the form on a standard GET, 
# and looks up the credentials in the users table on a POST.
@app.route("/", methods=["GET", "POST"])
def login():
    if is_logged_in():
        return redirect("/dashboard")

    error = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user_row = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user_row and user_row["password"] == password:
            session["logged_in"] = True
            session["user"] = username
            return redirect("/dashboard")
        else:
            error = "Invalid username or password"

    return render_template_string(LOGIN_HTML, error=error)


# Handles new sign-ups. Checks if the username is already taken, 
# and if not, saves the new username/password combo to the database.
@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user_row = conn.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()

        if user_row:
            error = "Username already exists"
            conn.close()
        else:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect("/")

    return render_template_string(REGISTER_HTML, error=error)


# Core view handling overall calculations, filtering metrics, and data charts.
@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        session.clear()
        return redirect("/")

    user = session.get("user")
    
    # Feature 3: Run recurring transactions engine right as the user hits the dashboard
    process_recurring_transactions(user)

    # Feature 4: Catch searching and filtering arguments from incoming GET requests
    search_query = request.args.get("search", "")
    selected_category = request.args.get("filter_category", "")

    conn = get_db_connection()
    
    # Base summary card logic (calculates totals over EVERYTHING, regardless of search bar query)
    all_rows = conn.execute("SELECT amount, is_income FROM transactions WHERE username = ?", (user,)).fetchall()
    income = sum(r["amount"] for r in all_rows if r["is_income"])
    expenses = sum(r["amount"] for r in all_rows if not r["is_income"])
    balance = income - expenses

    # Feature 1: Query for chart breakdown metrics (Aggregates expenses grouped by category)
    chart_rows = conn.execute("""
        SELECT category, SUM(amount) as total 
        FROM transactions 
        WHERE username = ? AND is_income = 0 
        GROUP BY category
    """, (user,)).fetchall()
    chart_labels = [r["category"] for r in chart_rows]
    chart_values = [r["total"] for r in chart_rows]

    # Feature 4: Form dynamic parameters for search filter SQL query block
    query = "SELECT date, description, category, amount, is_income FROM transactions WHERE username = ?"
    params = [user]
    
    if search_query:
        query += " AND description LIKE ?"
        params.append(f"%{search_query}%")
    if selected_category:
        query += " AND category = ?"
        params.append(selected_category)
        
    query += " ORDER BY date DESC"
    filtered_rows = conn.execute(query, params).fetchall()
    conn.close()

    return render_template_string(
        MAIN_HTML,
        transactions=[dict(r) for r in filtered_rows],
        income=round(income, 2),
        expenses=round(expenses, 2),
        balance=round(balance, 2),
        categories=CATEGORIES.keys(),
        user=user,
        search_query=search_query,
        selected_category=selected_category,
        chart_labels=chart_labels,
        chart_values=chart_values
    )


# Takes form data from the dashboard and logs a new transaction.
@app.route("/add", methods=["POST"])
def add():
    if not is_logged_in():
        return redirect("/")

    user = session.get("user")
    category = request.form["category"]
    date_str = request.form["date"]  # Formats as 'YYYY-MM-DD'
    amount = float(request.form["amount"])
    description = request.form["description"]
    is_income = 1 if CATEGORIES[category] else 0

    conn = get_db_connection()
    
    # Save base entry directly to the primary database ledger
    conn.execute("""
        INSERT INTO transactions (username, date, description, category, amount, is_income) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user, date_str, description, category, amount, is_income))
    
    # Feature 3: If marked as recurring, extract the day element and save a template
    if request.form.get("is_recurring") == "on":
        try:
            day_of_month = int(date_str.split("-")[2])
            current_month = date_str[:7]  # Extracts 'YYYY-MM'
            
            conn.execute("""
                INSERT INTO recurring_templates (username, day_of_month, description, category, amount, is_income, last_generated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user, day_of_month, description, category, amount, is_income, current_month))
        except Exception:
            pass  # Fail safely if date formatting acts strange
            
    conn.commit()
    conn.close()

    return redirect("/dashboard")


# Displays the journal logs page with all historical entries for this user.
@app.route("/journal")
def journal():
    if not is_logged_in():
        return redirect("/")

    entries = load_journal()
    return render_template_string(JOURNAL_HTML, entries=entries)


# Processes the form to add a new journal post and saves it to the database.
@app.route("/journal/add", methods=["POST"])
def add_journal():
    if not is_logged_in():
        return redirect("/")

    user = session.get("user")
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO journal (username, date, title, content) VALUES (?, ?, ?, ?)",
        (user, request.form["date"], request.form["title"], request.form["content"])
    )
    conn.commit()
    conn.close()

    return redirect("/journal")


# Displays the scheduler layout page and grabs all upcoming entries.
@app.route("/schedule")
def schedule():
    if not is_logged_in():
        return redirect("/")

    events = load_schedule()
    return render_template_string(SCHEDULE_HTML, events=events)


# Captures calendar forms and inserts a new event row into the schedule table.
@app.route("/schedule/add", methods=["POST"])
def add_event():
    if not is_logged_in():
        return redirect("/")

    user = session.get("user")
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO schedule (username, date, time, title, description) VALUES (?, ?, ?, ?, ?)",
        (user, request.form["date"], request.form["time"], request.form["title"], request.form["description"])
    )
    conn.commit()
    conn.close()

    return redirect("/schedule")


# Quick placeholder route for editing single transaction lines down the road.
@app.route("/edit/<int:index>")
def edit(index):
    return render_template_string(EDIT_HTML)


# Clears out cookies/session values and kicks the user back to login.
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================================================
# RUN APPLICATION TRADITIONAL RUNNERS
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
