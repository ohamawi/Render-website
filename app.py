#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# =========================================================
# IMPORTS
# =========================================================

# Flask tools for routing, forms, sessions, and redirects
from flask import Flask, render_template_string, request, redirect, session

# Used for checking environment ports
import os

# SQLite database driver
import sqlite3

# =========================================================
# CREATE FLASK APP
# =========================================================

app = Flask(__name__)

# Secret key used for login sessions
app.secret_key = "supersecretkey"

# Database Configuration
DB_FILE = "app.db"


# =========================================================
# SQLITE DATABASE INITIALIZATION
# =========================================================

def init_db():
    """Initializes the database schema if tables don't exist yet."""
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
    
    # 3. Journal table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            title TEXT,
            content TEXT
        )
    """)
    
    # 4. Schedule table
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

def get_db_connection():
    """Helper connection tool setting Row factories for dict-like query responses."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


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

def is_logged_in():
    return session.get("logged_in") and session.get("user")


# =========================================================
# DATA RETRIEVAL HELPERS (SQLITE BACKED)
# =========================================================

def load_data():
    user = session.get("user")
    if not user:
        return []
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT date, description, category, amount, is_income FROM transactions WHERE username = ?", 
        (user,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def load_journal():
    user = session.get("user")
    if not user:
        return []
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT date, title, content FROM journal WHERE username = ?", 
        (user,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def load_schedule():
    user = session.get("user")
    if not user:
        return []
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT date, time, title, description FROM schedule WHERE username = ?", 
        (user,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =========================================================
# SHARED MODERN CSS & JS (WITH DARK MODE ENGINE)
# =========================================================

SHARED_HEAD = """
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        <button type="submit">Add Transaction</button>
    </form>
    
    <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 1.5rem 0;">
    
    <h3>Transactions</h3>
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
            {% endfor %}
        </tbody>
    </table>
</div>
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


@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        session.clear()
        return redirect("/")

    transactions = load_data()

    income = sum(t["amount"] for t in transactions if t["is_income"])
    expenses = sum(t["amount"] for t in transactions if not t["is_income"])
    balance = income - expenses

    return render_template_string(
        MAIN_HTML,
        transactions=transactions,
        income=round(income, 2),
        expenses=round(expenses, 2),
        balance=round(balance, 2),
        categories=CATEGORIES.keys(),
        user=session.get("user")
    )


@app.route("/add", methods=["POST"])
def add():
    if not is_logged_in():
        return redirect("/")

    user = session.get("user")
    category = request.form["category"]
    is_income = 1 if CATEGORIES[category] else 0

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO transactions (username, date, description, category, amount, is_income) VALUES (?, ?, ?, ?, ?, ?)",
        (user, request.form["date"], request.form["description"], category, float(request.form["amount"]), is_income)
    )
    conn.commit()
    conn.close()

    return redirect("/dashboard")


@app.route("/journal")
def journal():
    if not is_logged_in():
        return redirect("/")

    entries = load_journal()
    return render_template_string(JOURNAL_HTML, entries=entries)


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


@app.route("/schedule")
def schedule():
    if not is_logged_in():
        return redirect("/")

    events = load_schedule()
    return render_template_string(SCHEDULE_HTML, events=events)


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


@app.route("/edit/<int:index>")
def edit(index):
    return render_template_string(EDIT_HTML)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================================================
# RUN APPLICATION WITH DATABASE INITIALIZATION
# =========================================================

if __name__ == "__main__":
    init_db()  # Setup tables automatically before application run
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )


# In[2]:


import os
print(os.getcwd())


# In[ ]:




