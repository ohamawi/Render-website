# =========================================================
# IMPORTS
# =========================================================

# Flask tools for routing, forms, sessions, and redirects
from flask import Flask, render_template_string, request, redirect, session

# Allows Flask to run inside Jupyter Notebook
import threading

# Used for reading/writing JSON files
import json

# Used for checking if files exist
import os


# =========================================================
# CREATE FLASK APP
# =========================================================

app = Flask(__name__)

# Secret key used for login sessions
app.secret_key = "supersecretkey"


# =========================================================
# USER STORAGE
# =========================================================

# File that stores usernames/passwords
USERS_FILE = "users.json"

# Default accounts automatically created
DEFAULT_USERS = {
    "admin": "pass",
    "user": "pass2"
}


# =========================================================
# LOAD USERS
# =========================================================

def load_users():

    # If users.json doesn't exist,
    # create it with default users
    if not os.path.exists(USERS_FILE):

        with open(USERS_FILE, "w") as f:
            json.dump(DEFAULT_USERS, f, indent=4)

    # Load user data
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)

    except:
        return DEFAULT_USERS


# =========================================================
# SAVE USERS
# =========================================================

def save_users(users):

    # Save updated users into JSON
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


# =========================================================
# TRANSACTION CATEGORIES
# =========================================================

# True = income category
# False = expense category
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

    # Returns True only if BOTH values exist
    return session.get("logged_in") and session.get("user")


# =========================================================
# TRANSACTION FILE HELPERS
# =========================================================

def get_file():

    # Get current logged in user
    user = session.get("user")

    if not user:
        return None

    # Create user-specific transaction filename
    return f"{user}_transactions.json"


def load_data():

    file = get_file()

    if not file:
        return []

    # Load transaction data if file exists
    if os.path.exists(file):

        try:
            with open(file, "r") as f:
                return json.load(f)

        except:
            return []

    return []


def save_data(data):

    file = get_file()

    if not file:
        return

    # Save transaction data
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


# =========================================================
# JOURNAL FILE HELPERS
# =========================================================

def get_journal_file():

    user = session.get("user")

    if not user:
        return None

    # Create user-specific journal filename
    return f"{user}_journal.json"


def load_journal():

    file = get_journal_file()

    if not file:
        return []

    # Load journal entries
    if os.path.exists(file):

        try:
            with open(file, "r") as f:
                return json.load(f)

        except:
            return []

    return []


def save_journal(entries):

    file = get_journal_file()

    if not file:
        return

    # Save journal entries
    with open(file, "w") as f:
        json.dump(entries, f, indent=4)


# =========================================================
# SCHEDULER FILE HELPERS
# =========================================================

def get_schedule_file():

    user = session.get("user")

    if not user:
        return None

    # Create user-specific scheduler filename
    return f"{user}_schedule.json"


def load_schedule():

    file = get_schedule_file()

    if not file:
        return []

    # Load scheduled events
    if os.path.exists(file):

        try:
            with open(file, "r") as f:
                return json.load(f)

        except:
            return []

    return []


def save_schedule(events):

    file = get_schedule_file()

    if not file:
        return

    # Save schedule events
    with open(file, "w") as f:
        json.dump(events, f, indent=4)


# =========================================================
# HTML TEMPLATES
# =========================================================

# Login page HTML
LOGIN_HTML = """
<h2>Login</h2>

<form method="POST">

    <input name="username" placeholder="Username" required><br><br>

    <input
        name="password"
        type="password"
        placeholder="Password"
        required
    ><br><br>

    <button type="submit">Login</button>

</form>

<br>

<a href="/register">Create Account</a>

<p style="color:red;">{{ error }}</p>
"""

# Account creation page HTML
REGISTER_HTML = """
<h2>Create Account</h2>

<form method="POST">

    <input
        name="username"
        placeholder="New Username"
        required
    ><br><br>

    <input
        name="password"
        type="password"
        placeholder="New Password"
        required
    ><br><br>

    <button type="submit">Create Account</button>

</form>

<br>

<a href="/">Back to Login</a>

<p style="color:red;">{{ error }}</p>
"""

# Main dashboard HTML
MAIN_HTML = """
<h1>Finance Tracker</h1>

<p>Logged in as: {{ user }}</p>

<a href="/logout">Logout</a>

<br><br>

<a href="/journal">Open Journal</a>

<br><br>

<a href="/schedule">Open Scheduler</a>

<hr>

<h3>Summary</h3>

<p>Income: ${{ income }}</p>
<p>Expenses: ${{ expenses }}</p>
<p>Balance: ${{ balance }}</p>

<hr>

<h3>Add Transaction</h3>

<form method="POST" action="/add">

    <input
        name="description"
        placeholder="Description"
        required
    >

    <select name="category">

        {% for c in categories %}
            <option>{{ c }}</option>
        {% endfor %}

    </select>

    <input
        type="number"
        step="0.01"
        name="amount"
        placeholder="Amount"
        required
    >

    <input
        type="date"
        name="date"
        required
    >

    <button type="submit">Add</button>

</form>

<hr>

<h3>Transactions</h3>

<table border="1">

<tr>
<th>Date</th>
<th>Description</th>
<th>Category</th>
<th>Amount</th>
<th>Edit</th>
</tr>

{% for t in transactions %}

<tr>
<td>{{ t.date }}</td>
<td>{{ t.description }}</td>
<td>{{ t.category }}</td>
<td>{{ t.amount }}</td>
<td>
    <a href="/edit/{{ loop.index0 }}">Edit</a>
</td>
</tr>

{% endfor %}

</table>
"""

# Transaction editing page
EDIT_HTML = """
<h2>Edit Transaction</h2>
"""

# Journal page
JOURNAL_HTML = """
<h1>Journal</h1>

<a href="/dashboard">Back to Dashboard</a>

<hr>

<form method="POST" action="/journal/add">

    <input type="date" name="date" required>

    <br><br>

    <input
        name="title"
        placeholder="Entry Title"
        required
    >

    <br><br>

    <textarea
        name="content"
        rows="8"
        cols="50"
        required
    ></textarea>

    <br><br>

    <button type="submit">Save Entry</button>

</form>

<hr>

{% for entry in entries %}

<div style="border:1px solid black; padding:10px; margin-bottom:10px;">

    <h3>{{ entry.title }}</h3>

    <p>{{ entry.date }}</p>

    <p>{{ entry.content }}</p>

</div>

{% endfor %}
"""

# Scheduler page
SCHEDULE_HTML = """
<h1>Scheduler</h1>

<a href="/dashboard">Back to Dashboard</a>

<hr>

<form method="POST" action="/schedule/add">

    <input type="date" name="date" required>

    <br><br>

    <input type="time" name="time" required>

    <br><br>

    <input
        name="title"
        placeholder="Event Title"
        required
    >

    <br><br>

    <textarea
        name="description"
        rows="5"
        cols="50"
    ></textarea>

    <br><br>

    <button type="submit">Add Event</button>

</form>

<hr>

{% for event in events %}

<div style="border:1px solid black; padding:10px; margin-bottom:10px;">

    <h3>{{ event.title }}</h3>

    <p>{{ event.date }} at {{ event.time }}</p>

    <p>{{ event.description }}</p>

</div>

{% endfor %}
"""


# =========================================================
# LOGIN ROUTE
# =========================================================

@app.route("/", methods=["GET", "POST"])
def login():

    # Skip login if already logged in
    if is_logged_in():
        return redirect("/dashboard")

    error = ""

    # Login form submitted
    if request.method == "POST":

        users = load_users()

        username = request.form["username"]
        password = request.form["password"]

        # Validate credentials
        if username in users and users[username] == password:

            # Save login session
            session["logged_in"] = True
            session["user"] = username

            return redirect("/dashboard")

        else:
            error = "Invalid username or password"

    return render_template_string(
        LOGIN_HTML,
        error=error
    )


# =========================================================
# REGISTER ROUTE
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    error = ""

    if request.method == "POST":

        users = load_users()

        username = request.form["username"]
        password = request.form["password"]

        # Prevent duplicate usernames
        if username in users:

            error = "Username already exists"

        else:

            # Add new user
            users[username] = password

            save_users(users)

            # Create empty files for new user
            with open(f"{username}_transactions.json", "w") as f:
                json.dump([], f)

            with open(f"{username}_journal.json", "w") as f:
                json.dump([], f)

            with open(f"{username}_schedule.json", "w") as f:
                json.dump([], f)

            return redirect("/")

    return render_template_string(
        REGISTER_HTML,
        error=error
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # Prevent access if not logged in
    if not is_logged_in():

        session.clear()

        return redirect("/")

    transactions = load_data()

    # Calculate total income
    income = sum(
        t["amount"]
        for t in transactions
        if t["is_income"]
    )

    # Calculate total expenses
    expenses = sum(
        t["amount"]
        for t in transactions
        if not t["is_income"]
    )

    # Remaining balance
    balance = income - expenses

    return render_template_string(
        MAIN_HTML,
        transactions=transactions,
        income=income,
        expenses=expenses,
        balance=balance,
        categories=CATEGORIES.keys(),
        user=session.get("user")
    )


# =========================================================
# ADD TRANSACTION
# =========================================================

@app.route("/add", methods=["POST"])
def add():

    if not is_logged_in():
        return redirect("/")

    transactions = load_data()

    category = request.form["category"]

    # Add new transaction
    transactions.append({
        "date": request.form["date"],
        "description": request.form["description"],
        "category": category,
        "amount": float(request.form["amount"]),
        "is_income": CATEGORIES[category]
    })

    save_data(transactions)

    return redirect("/dashboard")


# =========================================================
# JOURNAL ROUTES
# =========================================================

@app.route("/journal")
def journal():

    if not is_logged_in():
        return redirect("/")

    entries = load_journal()

    return render_template_string(
        JOURNAL_HTML,
        entries=entries
    )


@app.route("/journal/add", methods=["POST"])
def add_journal():

    if not is_logged_in():
        return redirect("/")

    entries = load_journal()

    # Add new journal entry
    entries.append({
        "date": request.form["date"],
        "title": request.form["title"],
        "content": request.form["content"]
    })

    save_journal(entries)

    return redirect("/journal")


# =========================================================
# SCHEDULER ROUTES
# =========================================================

@app.route("/schedule")
def schedule():

    if not is_logged_in():
        return redirect("/")

    events = load_schedule()

    return render_template_string(
        SCHEDULE_HTML,
        events=events
    )


@app.route("/schedule/add", methods=["POST"])
def add_event():

    if not is_logged_in():
        return redirect("/")

    events = load_schedule()

    # Add scheduled event
    events.append({
        "date": request.form["date"],
        "time": request.form["time"],
        "title": request.form["title"],
        "description": request.form["description"]
    })

    save_schedule(events)

    return redirect("/schedule")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    # Clear session info
    session.clear()

    return redirect("/")


# =========================================================
# RUN FLASK APP
# =========================================================

def run_app():

    # 0.0.0.0 allows devices on your network to connect
    app.run(
        host="0.0.0.0",
        port=5000,
        use_reloader=False
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
