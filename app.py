from flask import Flask, render_template, request, jsonify
import sqlite3
import re
import time
from pathlib import Path

from ollama import chat
from schema_reader import get_database_schema, get_database_tables

app = Flask(__name__)

DATABASE = "database.db"
MODEL = "qwen2.5-coder:3b"

MAX_ROWS = 500
QUERY_TIMEOUT = 5


def get_db_connection():
    db_path = Path(DATABASE).resolve().as_uri()
    conn = sqlite3.connect(f"{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


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
You are QueryMate, a SQLite query generator.

Database schema:
{schema}

Convert the user's question into a valid SQLite query.

Rules:
- Generate only SELECT queries.
- Use only tables and columns from the schema.
- Do not invent tables or columns.
- Use valid SQLite syntax.
- Return only the SQL query.
- Do not include markdown or explanations.
- If the question cannot be answered using the schema,
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

    sql = re.sub(
        r"^```(?:sql)?\s*",
        "",
        sql,
        flags=re.IGNORECASE
    )

    sql = re.sub(r"\s*```$", "", sql)

    return sql.strip()


def validate_sql(sql):
    if not sql:
        raise ValueError("No query was generated.")

    sql = sql.strip()

    if not re.match(r"^(SELECT|WITH)\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")

    return sql


def execute_sql(sql):
    sql = validate_sql(sql)

    conn = get_db_connection()

    deadline = time.monotonic() + QUERY_TIMEOUT

    def check_time():
        return int(time.monotonic() > deadline)

    def check_query(action, arg1, arg2, database, source):
        allowed = {
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION
        }

        recursive = getattr(sqlite3, "SQLITE_RECURSIVE", None)

        if recursive is not None:
            allowed.add(recursive)

        if action not in allowed:
            return sqlite3.SQLITE_DENY

        if action == sqlite3.SQLITE_FUNCTION:
            function = (arg2 or arg1 or "").lower()

            if function == "load_extension":
                return sqlite3.SQLITE_DENY

        return sqlite3.SQLITE_OK

    try:
        conn.execute("PRAGMA query_only = ON")

        conn.set_authorizer(check_query)
        conn.set_progress_handler(check_time, 1000)

        cursor = conn.execute(sql)

        rows = [dict(row) for row in cursor.fetchmany(MAX_ROWS + 1)]

        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]

        return rows, truncated

    finally:
        conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/schema", methods=["GET"])
def get_schema():
    try:
        tables = get_database_tables()

        return jsonify({
            "tables": tables
        })

    except Exception:
        app.logger.exception("Could not load schema")

        return jsonify({
            "error": "Could not retrieve database schema."
        }), 500


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}

    user_query = data.get("query", "").strip()

    if not user_query:
        return jsonify({
            "error": "Please enter a question."
        }), 400

    if len(user_query) > 2000:
        return jsonify({
            "error": "Your question is too long."
        }), 400

    try:
        sql = generate_sql(user_query)
        rows, truncated = execute_sql(sql)

        return jsonify({
            "sql": sql,
            "rows": rows,
            "truncated": truncated
        })

    except Exception:
        app.logger.exception("Query failed")

        return jsonify({
            "error": "Something went wrong while generating or running the query."
        }), 400


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )