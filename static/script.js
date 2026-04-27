async function generateSQL() {
    let query = document.getElementById("queryInput").value;

    let response = await fetch("/generate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ query: query })
    });

    let data = await response.json();

    document.getElementById("sqlOutput").textContent = data.sql;

    let table = document.getElementById("resultTable");
    table.innerHTML = "";

    if (data.rows.length > 0) {
        let headers = Object.keys(data.rows[0]);

        let headRow = "<tr>";
        headers.forEach(h => headRow += `<th>${h}</th>`);
        headRow += "</tr>";
        table.innerHTML += headRow;

        data.rows.forEach(row => {
            let tr = "<tr>";
            headers.forEach(h => tr += `<td>${row[h]}</td>`);
            tr += "</tr>";
            table.innerHTML += tr;
        });
    }
}