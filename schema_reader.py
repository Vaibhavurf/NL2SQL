import sqlite3

DATABASE = "database.db"


def get_database_schema():
    conn = sqlite3.connect(DATABASE)

    try:
        cursor = conn.cursor()

        tables = cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
        """).fetchall()

        schema = []

        for (table_name,) in tables:
            columns = cursor.execute(
                f"PRAGMA table_info('{table_name}')"
            ).fetchall()

            column_names = [
                column[1] for column in columns
            ]

            schema.append(
                f"Table: {table_name}\n"
                f"Columns: {', '.join(column_names)}"
            )

        return "\n\n".join(schema)

    finally:
        conn.close()


if __name__ == "__main__":
    print(get_database_schema())