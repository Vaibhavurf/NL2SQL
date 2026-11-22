const HISTORY_KEY = "nl2sql_query_history";
const HISTORY_LIMIT = 20;

document.addEventListener("DOMContentLoaded", () => {
    loadSchema();
    setupKeyboard();
});


async function loadSchema() {
    const sidebar = document.querySelector(".sidebar-content");

    if (!sidebar) return;

    try {
        const response = await fetch("/schema");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not load schema.");
        }

        sidebar.innerHTML = "";

        const database = document.createElement("div");
        database.className = "database-name";

        const databaseIcon = document.createElement("span");
        databaseIcon.textContent = "📁";

        const databaseName = document.createElement("span");
        databaseName.textContent = "database.db";

        database.append(databaseIcon, databaseName);
        sidebar.appendChild(database);

        data.tables.forEach(table => {
            const tableItem = document.createElement("div");
            tableItem.className = "table-item";

            const tableIcon = document.createElement("span");
            tableIcon.className = "table-icon";
            tableIcon.textContent = "📋";

            const tableName = document.createElement("strong");
            tableName.textContent = table.name;

            tableItem.append(tableIcon, tableName);
            sidebar.appendChild(tableItem);

            table.columns.forEach(column => {
                const columnItem = document.createElement("div");
                columnItem.className = "column-item";

                const columnIcon = document.createElement("span");
                columnIcon.textContent = column.primary_key ? "🔑" : "🔤";

                const columnName = document.createElement("span");
                columnName.textContent = column.name;

                columnItem.append(columnIcon, columnName);
                sidebar.appendChild(columnItem);
            });
        });

        renderHistory(sidebar);
        updateStatus("Database schema loaded");

    } catch (error) {
        console.error(error);
        sidebar.textContent = "Could not load database schema.";
    }
}


async function generateSQL() {
    const input = document.getElementById("queryInput");
    const sqlOutput = document.getElementById("sqlOutput");
    const resultTable = document.getElementById("resultTable");
    const resultCount = document.getElementById("resultCount");
    const loading = document.getElementById("loading");
    const generateButton = document.getElementById("generateButton");

    const query = input.value.trim();

    if (!query) {
        showError("Please enter a question first.");
        input.focus();
        return;
    }

    hideError();

    sqlOutput.textContent = "Generating SQL...";
    resultTable.innerHTML = "";
    resultCount.textContent = "Loading...";
    loading.style.display = "block";

    generateButton.disabled = true;
    generateButton.textContent = "Generating...";

    updateStatus("Generating query");

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query: query
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || data.message || "Query failed."
            );
        }

        displaySQL(data.sql);
        displayResults(data.rows);

        saveHistory(query, data.sql);
        renderHistory();

        updateStatus("Query completed");

    } catch (error) {
        sqlOutput.textContent = "Query could not be generated.";

        resultTable.innerHTML = "";
        resultCount.textContent = "No results";

        showError(error.message || "Something went wrong.");
        updateStatus("Query failed");

    } finally {
        loading.style.display = "none";

        generateButton.disabled = false;
        generateButton.textContent = "▶ Generate SQL";
    }
}


function displaySQL(sql) {
    const sqlOutput = document.getElementById("sqlOutput");

    if (!sqlOutput) return;

    sqlOutput.textContent = sql || "No SQL generated.";
}


function displayResults(rows) {
    const table = document.getElementById("resultTable");
    const resultCount = document.getElementById("resultCount");

    table.innerHTML = "";

    if (!Array.isArray(rows) || rows.length === 0) {
        resultCount.textContent = "0 rows";

        const emptyRow = document.createElement("tr");
        const emptyCell = document.createElement("td");

        emptyCell.textContent = "No records found.";
        emptyCell.colSpan = 100;

        emptyRow.appendChild(emptyCell);
        table.appendChild(emptyRow);

        return;
    }

    const columns = Object.keys(rows[0]);

    const header = document.createElement("thead");
    const headerRow = document.createElement("tr");

    columns.forEach(column => {
        const th = document.createElement("th");
        th.textContent = column;
        headerRow.appendChild(th);
    });

    header.appendChild(headerRow);
    table.appendChild(header);

    const body = document.createElement("tbody");

    rows.forEach(row => {
        const tr = document.createElement("tr");

        columns.forEach(column => {
            const td = document.createElement("td");
            const value = row[column];

            td.textContent = value === null || value === undefined
                ? ""
                : String(value);

            tr.appendChild(td);
        });

        body.appendChild(tr);
    });

    table.appendChild(body);

    resultCount.textContent = `${rows.length} rows`;
}


function saveHistory(query, sql) {
    let history = getHistory();

    history = history.filter(item => item.query !== query);

    history.unshift({
        query: query,
        sql: sql,
        time: new Date().toLocaleString()
    });

    history = history.slice(0, HISTORY_LIMIT);

    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}


function getHistory() {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    } catch {
        return [];
    }
}


function renderHistory(sidebar) {
    sidebar = sidebar || document.querySelector(".sidebar-content");

    if (!sidebar) return;

    const oldSection = sidebar.querySelector(".history-section");

    if (oldSection) {
        oldSection.remove();
    }

    const history = getHistory();

    const section = document.createElement("div");
    section.className = "history-section";

    section.style.marginTop = "15px";
    section.style.borderTop = "1px solid #999";
    section.style.paddingTop = "8px";

    const heading = document.createElement("div");
    heading.textContent = "🕘 Query History";
    heading.style.fontWeight = "bold";
    heading.style.padding = "5px";
    heading.style.fontSize = "12px";

    section.appendChild(heading);

    const clearButton = document.createElement("button");
    clearButton.textContent = "Clear History";
    clearButton.style.margin = "5px";
    clearButton.style.fontSize = "11px";
    clearButton.onclick = clearHistory;

    section.appendChild(clearButton);

    if (history.length === 0) {
        const empty = document.createElement("div");

        empty.textContent = "No previous queries";
        empty.style.padding = "6px";
        empty.style.fontSize = "11px";
        empty.style.color = "#666";

        section.appendChild(empty);
    }

    history.forEach((item, index) => {
        const button = document.createElement("button");

        button.className = "history-item";
        button.textContent = item.query;
        button.title = item.time + "\n\n" + item.sql;

        button.style.display = "block";
        button.style.width = "100%";
        button.style.textAlign = "left";
        button.style.padding = "6px";
        button.style.margin = "2px 0";
        button.style.border = "1px solid #aaa";
        button.style.background = "#f5f5f5";
        button.style.cursor = "pointer";
        button.style.fontSize = "11px";
        button.style.overflow = "hidden";
        button.style.textOverflow = "ellipsis";

        button.onclick = () => restoreHistory(index);

        section.appendChild(button);
    });

    sidebar.appendChild(section);
}


function restoreHistory(index) {
    const history = getHistory();
    const item = history[index];

    if (!item) return;

    document.getElementById("queryInput").value = item.query;
    displaySQL(item.sql);

    document.getElementById("resultTable").innerHTML = "";
    document.getElementById("resultCount").textContent = "Query restored";

    hideError();
    updateStatus("Previous query restored");
}


function clearHistory() {
    const confirmed = confirm("Clear all query history?");

    if (!confirmed) return;

    localStorage.removeItem(HISTORY_KEY);
    renderHistory();

    updateStatus("Query history cleared");
}


function clearQuery() {
    const input = document.getElementById("queryInput");

    input.value = "";

    document.getElementById("sqlOutput").textContent =
        "Your generated SQL will appear here.";

    document.getElementById("resultTable").innerHTML = "";

    document.getElementById("resultCount").textContent =
        "No results";

    hideError();
    updateStatus("Ready");

    input.focus();
}


function newQuery() {
    clearQuery();
}


function useExample(query) {
    const input = document.getElementById("queryInput");

    input.value = query;
    input.focus();
}


async function copySQL() {
    const sql = document.getElementById("sqlOutput").textContent;

    if (!sql || sql === "Your generated SQL will appear here.") {
        showError("There is no SQL to copy.");
        return;
    }

    try {
        await navigator.clipboard.writeText(sql);
        updateStatus("SQL copied to clipboard");

    } catch (error) {
        showError("Could not copy SQL.");
    }
}


async function showDatabaseInfo() {
    try {
        const response = await fetch("/schema");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Could not load database info.");
        }

        let info = "Database: database.db\n\n";

        data.tables.forEach(table => {
            info += `Table: ${table.name}\n`;

            table.columns.forEach(column => {
                info += `  ${column.name} (${column.type || "Unknown"})`;

                if (column.primary_key) {
                    info += " - Primary Key";
                }

                info += "\n";
            });

            info += "\n";
        });

        alert(info);

    } catch (error) {
        showError(error.message || "Could not load database information.");
    }
}


function showError(message) {
    const errorBox = document.getElementById("errorBox");

    if (!errorBox) return;

    errorBox.textContent = message;
    errorBox.style.display = "block";
}


function hideError() {
    const errorBox = document.getElementById("errorBox");

    if (!errorBox) return;

    errorBox.textContent = "";
    errorBox.style.display = "none";
}


function updateStatus(message) {
    const status = document.getElementById("appStatus");

    if (status) {
        status.textContent = message;
    }
}


function setupKeyboard() {
    const input = document.getElementById("queryInput");

    if (!input) return;

    input.addEventListener("keydown", event => {
        if (event.ctrlKey && event.key === "Enter") {
            generateSQL();
        }
    });
}


window.generateSQL = generateSQL;
window.clearQuery = clearQuery;
window.newQuery = newQuery;
window.useExample = useExample;
window.copySQL = copySQL;
window.showDatabaseInfo = showDatabaseInfo;
window.clearHistory = clearHistory;