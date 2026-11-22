import sqlite3

DATABASE = "database.db"


def get_database_schema():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    tables = cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
    """).fetchall()

    schema = []

    for table in tables:
        table_name = table[0]

        columns = cursor.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        column_names = []

        for column in columns:
            column_names.append(column[1])

        schema.append(
            f"Table: {table_name}\n"
            f"Columns: {', '.join(column_names)}"
        )

    conn.close()

    return "\n\n".join(schema)


def get_database_tables():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    tables = cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
    """).fetchall()

    database_tables = []

    for table in tables:
        table_name = table[0]

        columns = cursor.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        table_columns = []

        for column in columns:
            table_columns.append({
                "name": column[1],
                "type": column[2],
                "primary_key": bool(column[5])
            })

        database_tables.append({
            "name": table_name,
            "columns": table_columns
        })

    conn.close()

    return database_tables


if __name__ == "__main__":
    print(get_database_schema())
    print(get_database_tables())