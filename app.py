from flask import Flask, render_template, request, jsonify
import sqlite3
import re

app = Flask(__name__)

DATABASE = "database.db"


# Connect to SQLite database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Convert natural language into SQL
def generate_sql(text):
    query = text.lower().strip()

    # Students
    if "all students" in query or "show students" in query:
        return "SELECT * FROM students;"

    if "marks above" in query or "marks greater than" in query:
        match = re.search(r"(?:above|greater than)\s+(\d+)", query)

        if match:
            marks = int(match.group(1))
            return f"SELECT * FROM students WHERE marks > {marks};"

    if "older than" in query or "age above" in query:
        match = re.search(r"(?:older than|age above)\s+(\d+)", query)

        if match:
            age = int(match.group(1))
            return f"SELECT * FROM students WHERE age > {age};"

    if "top students" in query or "highest marks" in query:
        return "SELECT * FROM students ORDER BY marks DESC LIMIT 5;"

    if "average marks" in query:
        return "SELECT AVG(marks) AS average_marks FROM students;"

    if "student count" in query or "number of students" in query:
        return "SELECT COUNT(*) AS student_count FROM students;"

    # Employees
    if "all employees" in query or "show employees" in query:
        return "SELECT * FROM employees;"

    if "salary above" in query or "salary greater than" in query:
        match = re.search(
            r"(?:above|greater than)\s+(\d+)",
            query
        )

        if match:
            salary = int(match.group(1))
            return f"SELECT * FROM employees WHERE salary > {salary};"

    if "highest paid employees" in query:
        return "SELECT * FROM employees ORDER BY salary DESC LIMIT 5;"

    if "average salary" in query:
        return "SELECT AVG(salary) AS average_salary FROM employees;"

    if "employee count" in query or "number of employees" in query:
        return "SELECT COUNT(*) AS employee_count FROM employees;"

    return None


# Execute SQL safely
def execute_sql(sql):
    if not sql:
        raise ValueError("Could not understand the question.")

    cleaned_sql = sql.strip().rstrip(";")

    # Only allow SELECT queries
    if not cleaned_sql.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    # Block potentially dangerous SQL operations
    forbidden = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "ATTACH",
        "DETACH",
        "PRAGMA"
    ]

    sql_upper = cleaned_sql.upper()

    for keyword in forbidden:
        if re.search(r"\b" + keyword + r"\b", sql_upper):
            raise ValueError("Unsafe SQL query detected.")

    conn = get_db_connection()

    try:
        cursor = conn.execute(cleaned_sql)
        rows = [dict(row) for row in cursor.fetchall()]

        return rows

    finally:
        conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}

    user_query = data.get("query", "").strip()

    if not user_query:
        return jsonify({
            "error": "Please enter a question."
        }), 400

    sql = generate_sql(user_query)

    if sql is None:
        return jsonify({
            "error": "I couldn't understand that question yet."
        }), 400

    try:
        rows = execute_sql(sql)

        return jsonify({
            "sql": sql,
            "rows": rows
        })

    except Exception as error:
        return jsonify({
            "sql": sql,
            "error": str(error)
        }), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)