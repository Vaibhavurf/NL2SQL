from flask import Flask, render_template, request, jsonify
import sqlite3
import re

from ollama import chat
from schema_reader import get_database_schema, get_database_tables

app = Flask(__name__)

DATABASE = "database.db"
MODEL = "qwen2.5-coder:3b"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
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
You are QueryMate, a SQLite SQL query generator.

Database schema:
{schema}

Convert the user's question into a valid SQLite query.

Rules:
- Generate only SELECT queries.
- Use only tables and columns from the schema.
- Do not invent tables or columns.
- Do not generate INSERT, UPDATE, DELETE, DROP, ALTER,
  CREATE, ATTACH, DETACH, or PRAGMA statements.
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

    sql = sql.strip().rstrip(";").strip()

    if not re.match(r"^(SELECT|WITH)\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")

    if ";" in sql:
        raise ValueError("Multiple queries are not allowed.")

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

    for word in forbidden:
        pattern = r"\b" + word + r"\b"

        if re.search(pattern, sql, re.IGNORECASE):
            raise ValueError("Unsafe query.")

    return sql


def execute_sql(sql):
    sql = validate_sql(sql)

    conn = get_db_connection()

    try:
        conn.execute("PRAGMA query_only = ON")

        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]

        return rows

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

    try:
        sql = generate_sql(user_query)
        rows = execute_sql(sql)

        return jsonify({
            "sql": sql,
            "rows": rows
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