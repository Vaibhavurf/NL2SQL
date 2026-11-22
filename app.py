from flask import Flask, render_template, request, jsonify
import sqlite3
import re

from ollama import chat
from schema_reader import get_database_schema

app = Flask(__name__)

DATABASE = "database.db"
MODEL = "qwen2.5-coder:3b"


# ---------------- DATABASE CONNECTION ----------------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- AI SQL GENERATION ----------------

def generate_sql(text):
    schema = get_database_schema()

    if not schema:
        raise ValueError("Could not read database schema.")

    response = chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": f"""
You are QueryMate, an expert SQLite SQL query generator.

Database schema:
{schema}

Your task:
Convert the user's natural language question into a valid SQLite query.

Rules:
1. Generate only SELECT queries.
2. Use only tables and columns present in the schema.
3. Do not invent tables or columns.
4. Do not generate INSERT, UPDATE, DELETE, DROP, ALTER,
   CREATE, ATTACH, DETACH, or PRAGMA statements.
5. Use valid SQLite syntax.
6. Return only the SQL query.
7. Do not include markdown, explanations, or comments.
8. If the question cannot be answered using the schema,
   return SELECT 1 WHERE 0;
"""
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )

    sql = response.message.content.strip()

    # Remove markdown formatting if the model adds it
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)

    sql = sql.strip()

    return sql


# ---------------- SQL VALIDATION ----------------

def validate_sql(sql):
    if not sql:
        raise ValueError("The AI did not generate a query.")

    cleaned_sql = sql.strip()

    # Remove trailing semicolon
    cleaned_sql = cleaned_sql.rstrip(";").strip()

    # Only SELECT or WITH queries are allowed
    if not re.match(r"^(SELECT|WITH)\b", cleaned_sql, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")

    # Block multiple SQL statements
    if ";" in cleaned_sql:
        raise ValueError("Multiple SQL statements are not allowed.")

    # Block dangerous SQL operations
    forbidden = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "REPLACE",
        "VACUUM"
    ]

    for keyword in forbidden:
        pattern = r"\b" + keyword + r"\b"

        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            raise ValueError("Unsafe SQL query detected.")

    return cleaned_sql


# ---------------- SQL EXECUTION ----------------

def execute_sql(sql):
    validated_sql = validate_sql(sql)

    conn = get_db_connection()

    try:
        # Enforce read-only mode at SQLite level
        conn.execute("PRAGMA query_only = ON")

        cursor = conn.execute(validated_sql)

        rows = [dict(row) for row in cursor.fetchall()]

        return rows

    finally:
        conn.close()


# ---------------- FLASK ROUTES ----------------

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

    try:
        # Generate SQL using local AI
        sql = generate_sql(user_query)

        # Validate and execute SQL
        rows = execute_sql(sql)

        return jsonify({
            "sql": sql,
            "rows": rows
        })

    except Exception:
        app.logger.exception("Query generation failed")

        return jsonify({
            "error": "Something went wrong while generating or executing the query."
        }), 400


# ---------------- APPLICATION START ----------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )