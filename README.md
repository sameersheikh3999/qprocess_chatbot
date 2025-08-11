# QProcess Chatbot

AI-powered task creation system for QCheck/QTasks. Create tasks using natural language through a conversational interface.

## Features

- Natural language task creation
- Recurring task scheduling
- Multi-user assignment
- Priority list management
- Timezone-aware scheduling
- Checklist items support

## Quick Start

### 1. Prerequisites

- Python 3.8+
- SQL Server with QTasks database
- Claude API key from Anthropic

### 2. Database Setup

The chatbot requires a custom stored procedure in your QCheck database.

#### Install Required Stored Procedure

```bash
# Run the installation script in SQL Server Management Studio
# File: database/install_stored_procedure.sql
```

#### Verify Installation

```bash
# Run verification to ensure all prerequisites are met
# File: database/verify_installation.sql
```

The stored procedure integrates with your existing QCheck procedures:
- QCheck_CreateSimple_part1
- QCheck_AddManager
- QCheck_AddAssignedTo
- QCheck_UpdateSchedule_part1
- QCheck_UpdateSchedule_Part2

For detailed instructions, see [DATABASE_SETUP.md](DATABASE_SETUP.md)

### 3. Backend Setup

```bash
# Navigate to backend
cd backend/chatbot

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - CLAUDE_API_KEY
# - Database connection details
```

### 4. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### 5. Run the Application

```bash
# Option 1: Use the start script
python scripts/start_server.py

# Option 2: Run Django directly
cd backend/chatbot
python manage.py runserver 0.0.0.0:8000
```

Access the application at http://localhost:3000

## User Configuration

### Setting Up Users

Users must exist in both `QCheck_Users` and `QCheck_Groups` tables with matching names.

```bash
# Create missing personal groups for users
python scripts/manage_users.py --create-missing
```

### Checking Configured Users

```sql
SELECT u.FullName, g.Name as GroupName 
FROM QCheck_Users u 
INNER JOIN QCheck_Groups g ON u.FullName = g.Name 
WHERE u.isdeleted <> 1
```

## API Usage

### Endpoint

`POST http://localhost:8000/api/chat/`

### Request Format

```json
{
    "message": "Create a team meeting for next Friday at 2pm",
    "user": "User Name",
    "mainController": "Valid Group Name",
    "timezone": "America/New_York"
}
```

### Response Examples

**Success:**
```json
{
    "reply": "Task created successfully! The task has been added to the system."
}
```

**Need More Info:**
```json
{
    "reply": "I need the following information: assignees for the task."
}
```

## Natural Language Examples

- "Schedule a team meeting for next Friday with John and Jane"
- "Create a recurring task to check reports every Monday at 10am"
- "Remind me to review documents tomorrow at 5pm"
- "Make a weekly task for status updates, add to priority list"

### Time Interpretations

- "morning" → 10:00 AM
- "afternoon" → 2:00 PM  
- "evening" → 7:00 PM
- "end of day" → 5:00 PM

## Troubleshooting

### No Users in Dropdown

Run the user management script:
```bash
python scripts/manage_users.py --create-missing
```

### Database Connection Issues

1. Check credentials in `.env`
2. Verify SQL Server is running
3. Test connection with `python backend/chatbot/manage.py dbshell`

### API Key Errors

Ensure `CLAUDE_API_KEY` is set in `.env` file

### Task Creation Fails

Check that:
- MainController exists in QCheck_Groups table
- Stored procedure is installed (run verification script)
- All required parameters are provided

## Project Structure

```
├── backend/
│   └── chatbot/         # Django REST API
├── frontend/            # React UI
├── database/            # SQL installation scripts
├── scripts/             # Utility scripts
├── .env.example         # Environment template
└── requirements.txt     # Python dependencies
```

## Documentation

- [DATABASE_SETUP.md](DATABASE_SETUP.md) - Complete database installation guide
- [API Reference](backend/chatbot/README.md) - Detailed API documentation
- [Frontend Guide](frontend/README.md) - UI customization and development

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review DATABASE_SETUP.md for database issues
3. Ensure all prerequisites are installed

## License

Proprietary - For authorized use only
## Solution & Architecture
See **docs/solution.md** for the system overview, runbook, and links to ADRs and diagrams.
