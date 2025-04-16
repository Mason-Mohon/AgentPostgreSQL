from flask import Flask, request, render_template_string, jsonify, send_file
import psycopg2
import pandas as pd
import os
import tempfile
import json
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_DATABASE = os.getenv("PG_DATABASE", "my_local_db")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "your_password")
PG_PORT = os.getenv("PG_PORT", "5432")

# Initialize Gemini client with the new SDK pattern
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Import the HTML template from your artifact
with open('templates/index.html', 'r') as f:
    template = f.read()

app = Flask(__name__)

def get_table_schemas():
    """Fetches table schema information from PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD,
            port=PG_PORT
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
        """)
        schema_info = {}
        for table, column, datatype in cursor.fetchall():
            if table not in schema_info:
                schema_info[table] = []
            schema_info[table].append(f"{column} ({datatype})")
        conn.close()
        return schema_info
    except Exception as e:
        print(f"Error fetching schema: {e}")
        return {}

def generate_sql(user_query):
    """Use Google Gemini AI to convert plain English to SQL with schema info."""
    schema_info = get_table_schemas()
    schema_text = "\n".join([f"Table {table}: {', '.join(columns)}" for table, columns in schema_info.items()])
    
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"""
            Based on the following database schema:
            {schema_text}
            Convert this natural language query into an SQL query for a PostgreSQL database: {user_query}
            Return as plaintext, query only, with no markdown formatting.
            """
        )
        return response.text, None
    except Exception as e:
        error_message = f"Error generating SQL: {str(e)}"
        print(error_message)
        return None, error_message

def execute_query(sql_query):
    """Execute the SQL query and return results as a DataFrame."""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD,
            port=PG_PORT
        )
        # Use pandas to execute the query and get results as DataFrame
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        
        # Convert to dict for JSON serialization
        results = {
            "columns": df.columns.tolist(),
            "data": df.to_dict('records')
        }
        
        return results, None
    except Exception as e:
        error_message = f"Error executing query: {str(e)}"
        print(error_message)
        return None, error_message

@app.route('/')
def index():
    return render_template_string(template)

@app.route('/query', methods=['POST'])
def query():
    user_input = request.form['user_input']
    sql_query, error = generate_sql(user_input)
    
    if error:
        return jsonify({"error": error})
    
    return jsonify({"sql_query": sql_query})

@app.route('/execute', methods=['POST'])
def execute():
    sql_query = request.form['sql_query']
    results, error = execute_query(sql_query)
    
    if error:
        return jsonify({"error": error})
    
    return jsonify({"results": results})

@app.route('/download', methods=['POST'])
def download():
    sql_query = request.form['sql_query']
    file_type = request.form['file_type']
    
    results, error = execute_query(sql_query)
    
    if error:
        return jsonify({"error": error})
    
    # Convert results to DataFrame
    df = pd.DataFrame(results['data'])
    
    # Create a temporary file
    temp_dir = tempfile.mkdtemp()
    
    if file_type == "csv":
        file_path = os.path.join(temp_dir, "query_results.csv")
        df.to_csv(file_path, index=False)
        mimetype = 'text/csv'
        filename = "query_results.csv"
    else:
        file_path = os.path.join(temp_dir, "query_results.xlsx")
        df.to_excel(file_path, index=False)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = "query_results.xlsx"
    
    return send_file(file_path, mimetype=mimetype, as_attachment=True, download_name=filename)

@app.route('/schema_info')
def schema_info():
    """API endpoint to get database schema information."""
    schema_info = get_table_schemas()
    
    # Format for frontend use
    tables = []
    for table_name, columns in schema_info.items():
        tables.append({
            "name": table_name,
            "columns": columns
        })
    
    return jsonify({
        "database": PG_DATABASE,
        "tables": tables
    })

if __name__ == '__main__':
    # Ensure the template directory exists
    import os
    os.makedirs('templates', exist_ok=True)

    # Save the HTML template to a file
    with open('templates/index.html', 'w') as f:
        f.write(template)
        
    app.run(debug=True)

"""
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQLGenius - Natural Language to SQL</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    
    <!-- Custom CSS -->
    <style>
        :root {
            --primary: #4361ee;
            --secondary: #3a0ca3;
            --success: #4cc9f0;
            --light: #f8f9fa;
            --dark: #212529;
            --code-bg: #2b2d3a;
            --transition: all 0.3s ease;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f9fafb;
            color: #333;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
        }
        
        .brand-highlight {
            color: var(--primary);
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.18);
            transition: var(--transition);
        }
        
        .glass-card:hover {
            box-shadow: 0 10px 40px rgba(31, 38, 135, 0.2);
            transform: translateY(-5px);
        }
        
        .hero-section {
            position: relative;
            overflow: hidden;
            background: linear-gradient(135deg, #4cc9f0, #4361ee, #3a0ca3);
            padding: 60px 0;
            color: white;
        }
        
        .hero-pattern {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        }
        
        .main-container {
            position: relative;
            z-index: 10;
            padding-bottom: 60px;
        }
        
        .code-editor {
            font-family: 'JetBrains Mono', monospace;
            background-color: var(--code-bg);
            color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            position: relative;
        }
        
        .editor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            color: #adb5bd;
            font-size: 0.85rem;
        }
        
        .editor-dots {
            display: flex;
            gap: 6px;
        }
        
        .editor-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .dot-red { background-color: #ff5f56; }
        .dot-yellow { background-color: #ffbd2e; }
        .dot-green { background-color: #27c93f; }
        
        .sql-keyword {
            color: #ff79c6;
        }
        
        .sql-function {
            color: #8be9fd;
        }
        
        .sql-string {
            color: #f1fa8c;
        }
        
        .sql-number {
            color: #bd93f9;
        }
        
        .sql-comment {
            color: #6272a4;
        }
        
        .query-input {
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 15px 20px;
            font-size: 1rem;
            transition: var(--transition);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        .query-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.3);
        }
        
        .btn-primary {
            background-color: var(--primary);
            border-color: var(--primary);
            padding: 10px 24px;
            font-weight: 600;
            border-radius: 8px;
            transition: var(--transition);
        }
        
        .btn-primary:hover {
            background-color: var(--secondary);
            border-color: var(--secondary);
            transform: translateY(-2px);
        }
        
        .btn-outline-primary {
            color: var(--primary);
            border-color: var(--primary);
            padding: 10px 24px;
            font-weight: 600;
            border-radius: 8px;
            transition: var(--transition);
        }
        
        .btn-outline-primary:hover {
            background-color: var(--primary);
            border-color: var(--primary);
            transform: translateY(-2px);
        }
        
        .results-table {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        .table {
            margin-bottom: 0;
        }
        
        .table thead th {
            background-color: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
            color: #495057;
            font-weight: 600;
        }
        
        .table tbody tr:hover {
            background-color: rgba(67, 97, 238, 0.05);
        }
        
        .download-options {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
        }
        
        .form-select {
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 0.9rem;
        }
        
        .feature-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4cc9f0, #4361ee);
            color: white;
            font-size: 24px;
            margin-bottom: 20px;
        }
        
        .loading {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            backdrop-filter: blur(5px);
            visibility: hidden;
            opacity: 0;
            transition: opacity 0.3s, visibility 0.3s;
        }
        
        .loading.show {
            visibility: visible;
            opacity: 1;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid rgba(67, 97, 238, 0.2);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .clipboard-btn {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            border-radius: 4px;
            color: #adb5bd;
            padding: 5px 10px;
            font-size: 0.8rem;
            transition: var(--transition);
        }
        
        .clipboard-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            color: white;
        }
        
        .toast-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
        }
        
        .history-item {
            cursor: pointer;
            padding: 10px 15px;
            border-radius: 8px;
            transition: var(--transition);
            margin-bottom: 8px;
        }
        
        .history-item:hover {
            background-color: rgba(67, 97, 238, 0.1);
        }
        
        .history-query {
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .history-sql {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: #6c757d;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .section-heading {
            position: relative;
            padding-bottom: 10px;
            margin-bottom: 25px;
        }
        
        .section-heading::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 50px;
            height: 3px;
            background: linear-gradient(to right, var(--primary), var(--success));
            border-radius: 3px;
        }
        
        @media (max-width: 767px) {
            .hero-section {
                padding: 40px 0;
            }
            
            .glass-card {
                margin-bottom: 20px;
            }
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        
        /* Animation for the loader */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .fade-in {
            animation: fadeIn 0.5s ease forwards;
        }
        
        /* Animation delays for staggered effect */
        .delay-1 { animation-delay: 0.1s; }
        .delay-2 { animation-delay: 0.2s; }
        .delay-3 { animation-delay: 0.3s; }
        .delay-4 { animation-delay: 0.4s; }
        .delay-5 { animation-delay: 0.5s; }
    </style>
</head>
<body>
    <!-- Loading indicator -->
    <div class="loading" id="loadingIndicator">
        <div class="spinner"></div>
    </div>
    
    <!-- Toast notifications -->
    <div class="toast-container"></div>
    
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="#">SQL<span class="brand-highlight">Genius</span></a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link active" href="#"><i class="fas fa-home me-1"></i> Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#features"><i class="fas fa-star me-1"></i> Features</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#how-it-works"><i class="fas fa-question-circle me-1"></i> How It Works</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    
    <!-- Hero section -->
    <section class="hero-section">
        <div class="hero-pattern"></div>
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-7 mb-4 mb-md-0">
                    <h1 class="display-4 fw-bold mb-3 fade-in">Natural Language to SQL</h1>
                    <p class="lead mb-4 fade-in delay-1">Unlock the power of your database with simple English queries. Let Google Gemini AI convert your plain language into precise SQL queries instantly.</p>
                    <div class="d-flex gap-3 fade-in delay-2">
                        <a href="#query-section" class="btn btn-light btn-lg">
                            <i class="fas fa-magic me-2"></i> Try It Now
                        </a>
                        <a href="#how-it-works" class="btn btn-outline-light btn-lg">
                            <i class="fas fa-info-circle me-2"></i> Learn More
                        </a>
                    </div>
                </div>
                <div class="col-md-5 fade-in delay-3">
                    <div class="code-editor">
                        <div class="editor-header">
                            <div class="editor-dots">
                                <div class="editor-dot dot-red"></div>
                                <div class="editor-dot dot-yellow"></div>
                                <div class="editor-dot dot-green"></div>
                            </div>
                            <div>SQL Query</div>
                        </div>
                        <code>
                            <span class="sql-keyword">SELECT</span> c.name, COUNT(o.id) <span class="sql-keyword">AS</span> total_orders<br>
                            <span class="sql-keyword">FROM</span> customers c<br>
                            <span class="sql-keyword">JOIN</span> orders o <span class="sql-keyword">ON</span> c.id = o.customer_id<br>
                            <span class="sql-keyword">WHERE</span> o.order_date > <span class="sql-string">'2023-01-01'</span><br>
                            <span class="sql-keyword">GROUP BY</span> c.name<br>
                            <span class="sql-keyword">ORDER BY</span> total_orders <span class="sql-keyword">DESC</span><br>
                            <span class="sql-keyword">LIMIT</span> <span class="sql-number">10</span>;
                        </code>
                    </div>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Main content -->
    <div class="container main-container">
        <!-- Query section -->
        <section id="query-section" class="py-5">
            <h2 class="section-heading">Ask Your Database</h2>
            <div class="row">
                <div class="col-lg-8">
                    <div class="glass-card p-4 mb-4 fade-in">
                        <form id="queryForm" action="/query" method="post">
                            <div class="mb-4">
                                <label for="userInput" class="form-label fw-bold">Type your question in plain English</label>
                                <div class="input-group">
                                    <input type="text" class="form-control query-input" id="userInput" name="user_input" placeholder="e.g., Show me the top 5 customers by order value" required>
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-wand-magic-sparkles me-2"></i> Generate SQL
                                    </button>
                                </div>
                                <div class="form-text mt-2">
                                    <i class="fas fa-lightbulb text-warning me-1"></i> Try "Show me all customers who ordered more than $1000 last month"
                                </div>
                            </div>
                        </form>
                    </div>
                    
                    <!-- SQL results (initially hidden) -->
                    <div id="sqlResults" class="glass-card p-4 mb-4 fade-in" style="display: none;">
                        <h3 class="h5 fw-bold mb-3">Generated SQL Query</h3>
                        <div class="code-editor mb-3">
                            <div class="editor-header">
                                <div class="editor-dots">
                                    <div class="editor-dot dot-red"></div>
                                    <div class="editor-dot dot-yellow"></div>
                                    <div class="editor-dot dot-green"></div>
                                </div>
                                <div>SQL Query</div>
                            </div>
                            <pre id="sqlQueryDisplay"></pre>
                            <button class="clipboard-btn" id="copyToClipboard">
                                <i class="far fa-clipboard me-1"></i> Copy
                            </button>
                        </div>
                        <form id="executeForm" action="/execute" method="post" class="text-end">
                            <input type="hidden" id="sqlQueryInput" name="sql_query">
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-play me-2"></i> Execute Query
                            </button>
                        </form>
                    </div>
                    
                    <!-- Query results (initially hidden) -->
                    <div id="queryResults" class="glass-card p-4 fade-in" style="display: none;">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h3 class="h5 fw-bold mb-0">Query Results</h3>
                            <span class="badge bg-success" id="rowCount">0 rows</span>
                        </div>
                        <div class="results-table mb-4">
                            <div class="table-responsive">
                                <table class="table" id="resultsTable">
                                    <!-- Table content will be inserted here -->
                                </table>
                            </div>
                        </div>
                        <div class="download-options">
                            <form id="downloadForm" action="/download" method="post" class="row g-3 align-items-center">
                                <div class="col-md-6">
                                    <label for="fileType" class="form-label">Download Results</label>
                                    <select class="form-select" id="fileType" name="file_type">
                                        <option value="csv">CSV File (.csv)</option>
                                        <option value="excel">Excel File (.xlsx)</option>
                                    </select>
                                </div>
                                <div class="col-md-6 d-flex align-items-end">
                                    <input type="hidden" id="downloadQuery" name="sql_query">
                                    <button type="submit" class="btn btn-outline-primary w-100">
                                        <i class="fas fa-download me-2"></i> Download
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                    
                    <!-- Error message (initially hidden) -->
                    <div id="errorMessage" class="alert alert-danger mt-4" style="display: none;">
                        <i class="fas fa-exclamation-triangle me-2"></i> 
                        <span id="errorText"></span>
                    </div>
                </div>
                
                <div class="col-lg-4">
                    <!-- Query history -->
                    <div class="glass-card p-4 mb-4 fade-in delay-4">
                        <h3 class="h5 fw-bold mb-3">Query History</h3>
                        <div id="queryHistory" class="d-flex flex-column">
                            <div class="text-center text-muted py-4">
                                <i class="fas fa-history fa-2x mb-3"></i>
                                <p>Your query history will appear here</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Database info -->
                    <div class="glass-card p-4 fade-in delay-5">
                        <h3 class="h5 fw-bold mb-3">Database Info</h3>
                        <div class="mb-3">
                            <div class="text-muted small mb-1">Connected to:</div>
                            <div class="d-flex align-items-center">
                                <i class="fas fa-database me-2 text-primary"></i>
                                <span class="fw-medium" id="dbName">PostgreSQL DB</span>
                            </div>
                        </div>
                        <div id="schemaInfo">
                            <div class="mb-2 mt-3 text-muted small">Available Tables:</div>
                            <div class="list-group list-group-flush">
                                <!-- Table list will be populated by JavaScript -->
                                <a href="#" class="list-group-item list-group-item-action py-2 px-3">
                                    <i class="fas fa-table me-2 text-primary"></i> customers
                                </a>
                                <a href="#" class="list-group-item list-group-item-action py-2 px-3">
                                    <i class="fas fa-table me-2 text-primary"></i> orders 
                                </a>
                                <a href="#" class="list-group-item list-group-item-action py-2 px-3">
                                    <i class="fas fa-table me-2 text-primary"></i> products
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
        
        <!-- Features section -->
        <section id="features" class="py-5">
            <h2 class="section-heading">Key Features</h2>
            <div class="row g-4">
                <div class="col-md-4 fade-in">
                    <div class="glass-card p-4 h-100">
                        <div class="feature-icon">
                            <i class="fas fa-brain"></i>
                        </div>
                        <h3 class="h5 fw-bold mb-3">AI-Powered Translation</h3>
                        <p class="text-muted">Leverages Google Gemini to accurately convert natural language into optimized SQL queries without requiring technical knowledge.</p>
                    </div>
                </div>
                
                <div class="col-md-4 fade-in delay-1">
                    <div class="glass-card p-4 h-100">
                        <div class="feature-icon">
                            <i class="fas fa-table"></i>
                        </div>
                        <h3 class="h5 fw-bold mb-3">Real-time Results</h3>
                        <p class="text-muted">Instantly execute generated queries against your PostgreSQL database and view formatted results in an interactive table.</p>
                    </div>
                </div>
                
                <div class="col-md-4 fade-in delay-2">
                    <div class="glass-card p-4 h-100">
                        <div class="feature-icon">
                            <i class="fas fa-file-export"></i>
                        </div>
                        <h3 class="h5 fw-bold mb-3">Export Options</h3>
                        <p class="text-muted">Download query results in multiple formats including CSV and Excel for further analysis or reporting.</p>
                    </div>
                </div>
            </div>
        </section>
        
        <!-- How it works section -->
        <section id="how-it-works" class="py-5">
            <h2 class="section-heading">How It Works</h2>
            <div class="glass-card p-4 fade-in">
                <div class="row">
                    <div class="col-lg-6 mb-4 mb-lg-0">
                        <div class="d-flex mb-4">
                            <div class="me-3">
                                <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center" style="width: 30px; height: 30px;">1</div>
                            </div>
                            <div>
                                <h3 class="h5 fw-bold">Ask Your Question</h3>
                                <p class="text-muted">Enter your question in plain English, as if you were asking a colleague about your data.</p>
                            </div>
                        </div>
                        
                        <div class="d-flex mb-4">
                            <div class="me-3">
                                <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center" style="width: 30px; height: 30px;">2</div>
                            </div>
                            <div>
                                <h3 class="h5 fw-bold">AI Translation</h3>
                                <p class="text-muted">Google Gemini AI analyzes your question and the database schema to generate an optimized SQL query.</p>
                            </div>
                        </div>
                        
                        <div class="d-flex">
                            <div class="me-3">
                                <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center" style="width: 30px; height: 30px;">3</div>
                            </div>
                            <div>
                                <h3 class="h5 fw-bold">View & Export Results</h3>
                                <p class="text-muted">Execute the query against your database, view the results, and export data in your preferred format.</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-lg-6">
                        <div class="code-editor h-100">
                            <div class="editor-header">
                                <div class="editor-dots">
                                    <div class="editor-dot dot-red"></div>
                                    <div class="editor-dot dot-yellow"></div>
                                    <div class="editor-dot dot-green"></div>
                                </div>
                                <div>Example</div>
                            </div>
                            <div class="mb-3">
                                <div class="text-muted mb-2">/* You type this */</div>
                                <div class="p-2 bg-dark rounded">Show customers who ordered more than 5 products last month</div>
                            </div>
                            
                            <div class="mb-3">
                                <div class="text-muted mb-2">/* Gemini generates this */</div>
                                <code>
                                    <span class="sql-keyword">SELECT</span> c.name, c.email, COUNT(o.id) <span class="sql-keyword">AS</span> order_count<br>
                                    <span class="sql-keyword">FROM</span> customers c<br>
                                    <span class="sql-keyword">JOIN</span> orders o <span class="sql-keyword">ON</span> c.id = o.customer_id<br>
                                    <span class="sql-keyword">JOIN</span> order_items oi <span class="sql-keyword">ON</span> o.id = oi.order_id<br>
                                    <span class="sql-keyword">WHERE</span> o.order_date >= <span class="sql-function">date_trunc</span>(<span class="sql-string">'month'</span>, <span class="sql-function">current_date</span> - <span class="sql-string">'1 month'</span>::<span class="sql-keyword">interval</span>)<br>
                                    <span class="sql-keyword">AND</span> o.order_date < <span class="sql-function">date_trunc</span>(<span class="sql-string">'month'</span>, <span class="sql-function">current_date</span>)<br>
                                    <span class="sql-keyword">GROUP BY</span> c.id<br>
                                    <span class="sql-keyword">HAVING</span> COUNT(DISTINCT oi.product_id) > <span class="sql-number">5</span>;
                                </code>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </div>
    
    <!-- Footer -->
    <footer class="bg-dark text-white py-4">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <h4 class="h5 mb-3">SQLGenius</h4>
                    <p class="text-muted mb-0">Transforming natural language into SQL queries with the power of Google Gemini AI.</p>
                </div>
                <div class="col-md-6 text-md-end">
                    <div class="mb-2">
                        <a href="#" class="text-decoration-none text-white me-3"><i class="fab fa-github"></i></a>
                        <a href="#" class="text-decoration-none text-white me-3"><i class="fab fa-twitter"></i></a>
                        <a href="#" class="text-decoration-none text-white"><i class="fab fa-linkedin"></i></a>
                    </div>
                    <p class="text-muted mb-0">&copy; 2025 SQLGenius. All rights reserved.</p>
                </div>
            </div>
        </div>
    </footer>
    
    <!-- Bootstrap JS, Popper.js -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Custom JavaScript -->
    <script>
        // DOM Elements
        const queryForm = document.getElementById('queryForm');
        const executeForm = document.getElementById('executeForm');
        const downloadForm = document.getElementById('downloadForm');
        const userInput = document.getElementById('userInput');
        const sqlResults = document.getElementById('sqlResults');
        const sqlQueryDisplay = document.getElementById('sqlQueryDisplay');
        const sqlQueryInput = document.getElementById('sqlQueryInput');
        const downloadQuery = document.getElementById('downloadQuery');
        const queryResults = document.getElementById('queryResults');
        const resultsTable = document.getElementById('resultsTable');
        const rowCount = document.getElementById('rowCount');
        const errorMessage = document.getElementById('errorMessage');
        const errorText = document.getElementById('errorText');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const copyToClipboard = document.getElementById('copyToClipboard');
        const queryHistory = document.getElementById('queryHistory');
        
        // Initialize the page - fetch schema info
        document.addEventListener('DOMContentLoaded', () => {
            fetchDatabaseInfo();
            
            // Reveal animations
            document.querySelectorAll('.fade-in').forEach(el => {
                el.style.opacity = "0";
                
                const observer = new IntersectionObserver(entries => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            setTimeout(() => {
                                entry.target.style.opacity = "1";
                            }, 100);
                            observer.unobserve(entry.target);
                        }
                    });
                });
                
                observer.observe(el);
            });
        });
        
        // Fetch database schema info
        async function fetchDatabaseInfo() {
            try {
                const response = await fetch('/schema_info');
                if (response.ok) {
                    const data = await response.json();
                    updateSchemaInfo(data);
                }
            } catch (error) {
                console.error('Error fetching schema info:', error);
            }
        }
        
        // Update schema info in the sidebar
        function updateSchemaInfo(schemaData) {
            const schemaInfo = document.getElementById('schemaInfo');
            const dbName = document.getElementById('dbName');
            
            if (schemaData.database) {
                dbName.textContent = schemaData.database;
            }
            
            if (schemaData.tables && schemaData.tables.length > 0) {
                let tableHTML = '<div class="mb-2 mt-3 text-muted small">Available Tables:</div>';
                tableHTML += '<div class="list-group list-group-flush">';
                
                schemaData.tables.forEach(table => {
                    tableHTML += `
                        <a href="#" class="list-group-item list-group-item-action py-2 px-3">
                            <i class="fas fa-table me-2 text-primary"></i> ${table.name}
                        </a>
                    `;
                });
                
                tableHTML += '</div>';
                schemaInfo.innerHTML = tableHTML;
            }
        }
        
        // Query form submission
        queryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            if (!userInput.value.trim()) {
                showToast('Please enter a query first', 'warning');
                return;
            }
            
            showLoading();
            
            try {
                const response = await fetch('/query', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.error) {
                        showError(data.error);
                    } else {
                        displaySqlQuery(data.sql_query, userInput.value);
                        hideError();
                    }
                } else {
                    throw new Error('Failed to generate SQL query');
                }
            } catch (error) {
                console.error('Error generating SQL:', error);
                showError(error.message);
            } finally {
                hideLoading();
            }
        });
        
        // Execute form submission
        executeForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            showLoading();
            
            try {
                const response = await fetch('/execute', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.error) {
                        showError(data.error);
                    } else {
                        displayQueryResults(data.results);
                        hideError();
                        
                        // Add to history if not already there
                        saveToHistory(userInput.value, sqlQueryInput.value);
                    }
                } else {
                    throw new Error('Failed to execute query');
                }
            } catch (error) {
                console.error('Error executing query:', error);
                showError(error.message);
            } finally {
                hideLoading();
            }
        });
        
        // Download form submission - Using regular form submission for file download
        downloadForm.addEventListener('submit', function() {
            downloadQuery.value = sqlQueryInput.value;
        });
        
        // Display SQL query
        function displaySqlQuery(sqlQuery, userQuestion) {
            // Clean up SQL query
            sqlQuery = sqlQuery.trim();
            
            // Display SQL with syntax highlighting
            sqlQueryDisplay.innerHTML = formatSqlSyntax(sqlQuery);
            
            // Update hidden input with the SQL query
            sqlQueryInput.value = sqlQuery;
            downloadQuery.value = sqlQuery;
            
            // Show SQL results section
            sqlResults.style.display = 'block';
            
            // Hide query results section
            queryResults.style.display = 'none';
            
            // Scroll to results
            sqlResults.scrollIntoView({behavior: 'smooth'});
        }
        
        // Format SQL syntax with highlighting
        function formatSqlSyntax(sql) {
            // SQL keywords to highlight
            const keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN', 'ON', 'AS', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS NULL', 'IS NOT NULL', 'LIMIT', 'OFFSET', 'UNION', 'ALL', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TABLE', 'VIEW', 'INDEX', 'CONSTRAINT', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX'];
            
            // Replace SQL keywords with highlighted versions
            let formattedSql = sql;
            
            // Highlight keywords
            keywords.forEach(keyword => {
                const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
                formattedSql = formattedSql.replace(regex, match => `<span class="sql-keyword">${match}</span>`);
            });
            
            // Highlight strings
            formattedSql = formattedSql.replace(/'([^']*)'/g, `'<span class="sql-string">$1</span>'`);
            
            // Highlight numbers
            formattedSql = formattedSql.replace(/\b(\d+)\b/g, `<span class="sql-number">$1</span>`);
            
            // Highlight functions
            formattedSql = formattedSql.replace(/(\w+)\(/g, `<span class="sql-function">$1</span>(`);
            
            return formattedSql;
        }
        
        // Display query results
        function displayQueryResults(results) {
            if (!results || !results.columns || !results.data) {
                showError('Invalid results format');
                return;
            }
            
            // Build table header
            let tableHTML = '<thead><tr>';
            results.columns.forEach(column => {
                tableHTML += `<th>${column}</th>`;
            });
            tableHTML += '</tr></thead>';
            
            // Build table body
            tableHTML += '<tbody>';
            results.data.forEach(row => {
                tableHTML += '<tr>';
                Object.values(row).forEach(cell => {
                    tableHTML += `<td>${cell !== null ? cell : '<span class="text-muted">NULL</span>'}</td>`;
                });
                tableHTML += '</tr>';
            });
            tableHTML += '</tbody>';
            
            // Update table
            resultsTable.innerHTML = tableHTML;
            
            // Update row count
            rowCount.textContent = `${results.data.length} rows`;
            
            // Show query results section
            queryResults.style.display = 'block';
            
            // Scroll to results
            queryResults.scrollIntoView({behavior: 'smooth'});
        }
        
        // Save query to history
        function saveToHistory(question, sqlQuery) {
            // Check if history contains empty placeholder
            if (queryHistory.querySelector('.text-center.text-muted')) {
                queryHistory.innerHTML = '';
            }
            
            // Create history item
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.dataset.query = question;
            historyItem.dataset.sql = sqlQuery;
            
            historyItem.innerHTML = `
                <div class="history-query">${truncateText(question, 40)}</div>
                <div class="history-sql">${truncateText(sqlQuery, 60)}</div>
            `;
            
            // Add click event
            historyItem.addEventListener('click', function() {
                userInput.value = this.dataset.query;
                displaySqlQuery(this.dataset.sql, this.dataset.query);
            });
            
            // Add to history (prepend)
            queryHistory.prepend(historyItem);
            
            // Limit history to 5 items
            const historyItems = queryHistory.querySelectorAll('.history-item');
            if (historyItems.length > 5) {
                queryHistory.removeChild(historyItems[historyItems.length - 1]);
            }
        }
        
        // Copy SQL to clipboard
        copyToClipboard.addEventListener('click', function() {
            const textToCopy = sqlQueryInput.value;
            
            navigator.clipboard.writeText(textToCopy)
                .then(() => {
                    showToast('SQL copied to clipboard', 'success');
                    this.innerHTML = '<i class="fas fa-check me-1"></i> Copied';
                    
                    setTimeout(() => {
                        this.innerHTML = '<i class="far fa-clipboard me-1"></i> Copy';
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy: ', err);
                    showToast('Failed to copy to clipboard', 'error');
                });
        });
        
        // Show error message
        function showError(message) {
            errorText.textContent = message;
            errorMessage.style.display = 'block';
        }
        
        // Hide error message
        function hideError() {
            errorMessage.style.display = 'none';
        }
        
        // Show loading indicator
        function showLoading() {
            loadingIndicator.classList.add('show');
        }
        
        // Hide loading indicator
        function hideLoading() {
            loadingIndicator.classList.remove('show');
        }
        
        // Show toast notification
        function showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast show`;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            // Set color based on type
            let bgColor = 'bg-info';
            let icon = 'info-circle';
            
            if (type === 'success') {
                bgColor = 'bg-success';
                icon = 'check-circle';
            } else if (type === 'error') {
                bgColor = 'bg-danger';
                icon = 'exclamation-circle';
            } else if (type === 'warning') {
                bgColor = 'bg-warning';
                icon = 'exclamation-triangle';
            }
            
            toast.innerHTML = `
                <div class="toast-header ${bgColor} text-white">
                    <i class="fas fa-${icon} me-2"></i>
                    <strong class="me-auto">SQLGenius</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            `;
            
            document.querySelector('.toast-container').appendChild(toast);
            
            // Remove after 3 seconds
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    toast.remove();
                }, 300);
            }, 3000);
        }
        
        // Helper function to truncate text
        function truncateText(text, maxLength) {
            return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
        }
    </script>
</body>
</html>)<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQLGenius - Natural Language to SQL</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    
    <!-- Custom CSS -->
    <style>
        :root {
            --primary: #4361ee;
            --secondary: #3a0ca3;
            --success: #4cc9f0;
            --light: #f8f9fa;
            --dark: #212529;
            --code-bg: #2b2d3a;
            --transition: all 0.3s ease;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f9fafb;
            color: #333;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
        }
        
        .brand-highlight {
            color: var(--primary);
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.18);
            transition: var(--transition);
        }
        
        .glass-card:hover {
            box-shadow: 0 10px 40px rgba(31, 38, 135, 0.2);
            transform: translateY(-5px);
        }
        
        .hero-section {
            position: relative;
            overflow: hidden;
            background: linear-gradient(135deg, #4cc9f0, #4361ee, #3a0ca3);
            padding: 60px 0;
            color: white;
        }
        
        .hero-pattern {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        }
        
        .main-container {
            position: relative;
            z-index: 10;
            padding-bottom: 60px;
        }
        
        .code-editor {
            font-family: 'JetBrains Mono', monospace;
            background-color: var(--code-bg);
            color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            position: relative;
        }
        
        .editor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            color: #adb5bd;
            font-size: 0.85rem;
        }
        
        .editor-dots {
            display: flex;
            gap: 6px;
        }
        
        .editor-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .dot-red { background-color: #ff5f56; }
        .dot-yellow { background-color: #ffbd2e; }
        .dot-green { background-color: #27c93f; }
        
        .sql-keyword {
            color: #ff79c6;
        }
        
        .sql-function {
            color: #8be9fd;
        }
        
        .sql-string {
            color: #f1fa8c;
        }
        
        .sql-number {
            color: #bd93f9;
        }
        
        .sql-comment {
            color: #6272a4;
        }
        
        .query-input {
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 15px 20px;
            font-size: 1rem;
            transition: var(--transition);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        .query-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.3);
        }
        
        .btn-primary {
            background-color: var(--primary);
            border-color: var(--primary);
            padding: 10px 24px;
            font-weight: 600;
            border-radius: 8px;
            transition: var(--transition);
        }
        
        .btn-primary:hover {
            background-color: var(--secondary);
            border-color: var(--secondary);
            transform: translateY(-2px);
        }
        
        .btn-outline-primary {
            color: var(--primary);
            border-color: var(--primary);
            padding: 10px 24px;
            font-weight: 600;
            border-radius: 8px;
            transition: var(--transition);
        }
        
        .btn-outline-primary:hover {
            background-color: var(--primary);
            border-color: var(--primary);
            transform: translateY(-2px);
        }
        
        .results-table {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        .table {
            margin-bottom: 0;
        }
        
        .table thead th {
            background-color: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
            color: #495057;
            font-weight: 600;
        }
        
        .table tbody tr:hover {
            background-color: rgba(67, 97, 238, 0.05);
        }
        
        .download-options {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
        }
        
        .form-select {
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 0.9rem;
        }
        
        .feature-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4cc9f0, #4361ee);
            color: white;
            font-size: 24px;
            margin-bottom: 20px;
        }
        
        .loading {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            backdrop-filter: blur(5px);
            visibility: hidden;
            opacity: 0;
            transition: opacity 0.3s, visibility 0.3s;
        }
        
        .loading.show {
            visibility: visible;
            opacity: 1;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid rgba(67, 97, 238, 0.2);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .clipboard-btn {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            border-radius: 4px;
            color: #adb5bd;
            padding: 5px 10px;
            font-size: 0.8rem;
            transition: var(--transition);
        }
        
        .clipboard-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            color: white;
        }
        
        .toast-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
        }
        
        .history-item {
            cursor: pointer;
            padding: 10px 15px;
            border-radius: 8px;
            transition: var(--transition);
            margin-bottom: 8px;
        }
        
        .history-item:hover {
            background-color: rgba(67, 97, 238, 0.1);
        }
        
        .history-query {
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .history-sql {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: #6c757d;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .section-heading {
            position: relative;
            padding-bottom: 10px;
            margin-bottom: 25px;
        }
        
        .section-heading::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 50px;
            height: 3px;
            background: linear-gradient(to right, var(--primary), var(--success));
            border-radius: 3px;
        }
        
        @media (max-width: 767px) {
            .hero-section {
                padding: 40px 0;
            }
            
            .glass-card {
                margin-bottom: 20px;
            }
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        
        /* Animation for the loader */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .fade-in {
            animation: fadeIn 0.5s ease forwards;
        }
        
        /* Animation delays for staggered effect */
        .delay-1 { animation-delay: 0.1s; }
        .delay-2 { animation-delay: 0.2s; }
        .delay-3 { animation-delay: 0.3s; }
        .delay-4 { animation-delay: 0.4s; }
        .delay-5 { animation-delay: 0.5s; }"""