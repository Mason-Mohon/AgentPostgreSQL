# AgentPostgreSQL

A user-friendly web app that allows users to enter questions in plain English, which are converted into SQL queries and executed against a PostgreSQL database. The app returns query results in both table and downloadable format.

## Features

- Natural language to SQL conversion
- Secure query execution against PostgreSQL
- Web interface built with Flask
- Table preview and Excel/CSV download options

## Project Structure

```
├── app.py                 # Main Flask app
├── templates/
│   ├── index.html         # Home page form
│   └── query_result.html  # Table result view
├── test.ipynb             # Development/testing notebook
└── .gitignore             # Git ignore rules
```

## Technologies Used

- Python
- Flask
- PostgreSQL
- Jinja2 (HTML templating)
- Git & GitHub

## Setup Instructions

1. Clone the repository  
   `git clone git@github.com:Mason-Mohon/AgentPostgreSQL.git`

2. Navigate to the folder  
   `cd AgentPostgreSQL`

3. Set up your virtual environment and install dependencies  
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Add your `.env` file with your database credentials

5. Run the app  
   `python app.py`

## Disclaimer

This project is a prototype and not intended for production use without additional security layers. Always validate and sanitize user inputs when running SQL queries.

## Contact

Created by Mason Mohon (https://github.com/Mason-Mohon)
