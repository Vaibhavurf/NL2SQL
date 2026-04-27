from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def generate_sql(text):
    q = text.lower()

    if "all students" in q:
        return "SELECT * FROM students;"

    elif "above 18" in q or "older than 18" in q:
        return "SELECT * FROM students WHERE age > 18;"

    elif "marks above 80" in q:
        return "SELECT * FROM students WHERE marks > 80;"

    elif "top students" in q:
        return "SELECT * FROM students ORDER BY marks DESC LIMIT 5;"

    elif "all employees" in q:
        return "SELECT * FROM employees;"

    elif "salary above 50000" in q:
        return "SELECT * FROM employees WHERE salary > 50000;"

    else:
        return "SELECT * FROM students;"

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json(silent=True) or {}
    user_query = data.get('query','').strip()
    sql = generate_sql(user_query)

    return jsonify({
        "sql": sql,
        "rows": [
            {"id": 1, "name": "Rahul", "age": 20, "marks": 88},
            {"id": 2, "name": "Priya", "age": 19, "marks": 91},
            {"id": 3, "name": "Aman", "age": 21, "marks": 76}
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)