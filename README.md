# QProcess Chatbot

AI-powered task creation system for QCheck/QTasks. Create tasks using natural language through a conversational interface.

## Features

- **Natural Language Processing**: Create tasks using conversational language
- **Database Integration**: Seamlessly integrates with existing QCheck/QTasks database
- **User Management**: Automatic user validation and configuration
- **Task Scheduling**: Support for recurring tasks and complex scheduling
- **Modern UI**: Clean, responsive React frontend
- **Docker Support**: Easy deployment with Docker containers

## Quick Start with Docker

### Prerequisites

1. **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
2. **SQL Server** - SQL Server 2019 or later with QTasks3 database
3. **Claude API Key** - [Get one here](https://console.anthropic.com/)

### Installation

1. **Download and extract** the application files
2. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your database and API settings
   ```
3. **Install database stored procedure**:
   - Run `database/install_stored_procedure.sql` in SQL Server Management Studio
4. **Start the application**:
   ```bash
   docker-compose up -d
   ```
5. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Manual Installation

### Backend Setup

1. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure database** in `backend/chatbot/chatbot/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'mssql',
           'NAME': 'QTasks3',
           'USER': '',  # Leave blank for Windows Authentication
           'PASSWORD': '',  # Leave blank for Windows Authentication
           'HOST': 'YOUR_SERVER_NAME\\INSTANCE_NAME',
           'PORT': '',
           'OPTIONS': {
               'driver': 'ODBC Driver 17 for SQL Server',
               'trusted_connection': 'yes',
           },
       }
   }
   ```

3. **Set environment variables**:
   ```bash
   export CLAUDE_API_KEY=your-api-key
   export DJANGO_SETTINGS_MODULE=chatbot.settings
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Start the server**:
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. **Install Node.js dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm start
   ```

## Database Requirements

### Required Tables
- `QCheck_Users` - User information
- `QCheck_Groups` - Group definitions
- `QCheck_Checklists` - Task templates
- `QCheck_ChecklistInstances` - Task instances
- `QCheck_ActiveChecklists` - Active task tracking
- `QCheck_Assignments` - Task assignments
- `QCheck_ChecklistManagers` - Task managers

### Required Stored Procedures
- `QCheck_CreateTaskThroughChatbot` - Main task creation procedure
- `QCheck_CreateSimple_part1` - Task creation helper
- `QCheck_AddManager` - Add task managers
- `QCheck_AddAssignedTo` - Add task assignees
- `QCheck_AddItem` - Add task items
- `QCheck_UpdateSchedule_part1` - Schedule management
- `QCheck_UpdateSchedule_Part2` - Schedule management
- `QCheck_DuplicateNameCheck` - Duplicate prevention
- `Util_fn_List_To_Table` - String parsing utility

### User Configuration
Users must exist in both `QCheck_Users` and `QCheck_Groups` tables with matching names to be able to create tasks through the chatbot.

## API Endpoints

- `GET /api/users/` - Get list of configured users
- `POST /api/chat/` - Send chat message and create tasks
- `GET /api/tasks/` - Get user's tasks (if implemented)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_API_KEY` | Claude API key for AI service | Required |
| `DB_NAME` | Database name | QTasks3 |
| `DB_HOST` | Database server | DESKTOP-BIP1CP7\\SQLEXPRESS |
| `DB_USER` | Database username | (Windows Auth) |
| `DB_PASSWORD` | Database password | (Windows Auth) |
| `SECRET_KEY` | Django secret key | Generated |

### Database Connection

The application supports both Windows Authentication and SQL Server Authentication:

#### Windows Authentication (Recommended)
```python
'USER': '',
'PASSWORD': '',
'OPTIONS': {'trusted_connection': 'yes'}
```

#### SQL Server Authentication
```python
'USER': 'your_username',
'PASSWORD': 'your_password',
'OPTIONS': {'trusted_connection': 'no'}
```

## Troubleshooting

### Common Issues

1. **"Could not find stored procedure"**
   - Run the database installation script
   - Verify the procedure exists in the correct database

2. **"User not configured"**
   - Users need personal groups in `QCheck_Groups`
   - Run the user management script: `python scripts/manage_users.py --list`

3. **Database connection failed**
   - Verify SQL Server is running
   - Check firewall settings
   - Ensure ODBC Driver 17 is installed

4. **Frontend can't connect to backend**
   - Check CORS settings
   - Verify both services are running
   - Check network connectivity

### Logs

- **Backend logs**: Check Django console output or `/app/logs/django.log`
- **Frontend logs**: Check browser developer console
- **Docker logs**: `docker-compose logs -f`

## Development

### Project Structure
```
qprocess-chatbot/
├── backend/                    # Django backend
│   ├── chatbot/               # Main Django app
│   │   ├── api/              # API views
│   │   ├── services/         # Business logic
│   │   ├── config/           # Configuration
│   │   └── models.py         # Database models
│   ├── requirements.txt      # Python dependencies
│   └── manage.py            # Django management
├── frontend/                  # React frontend
│   ├── src/                 # Source code
│   ├── public/              # Static files
│   └── package.json         # Node.js dependencies
├── database/                 # Database scripts
├── scripts/                  # Utility scripts
└── docs/                     # Documentation
```

### Adding New Features

1. **Backend**: Add new API endpoints in `backend/chatbot/api/views/`
2. **Frontend**: Add new components in `frontend/src/`
3. **Database**: Add new stored procedures as needed
4. **Testing**: Test with the verification scripts

## Support

For issues or questions:
1. Check the [DEPLOYMENT.md](DEPLOYMENT.md) guide
2. Review the troubleshooting section
3. Check logs for error details
4. Contact support with specific error messages

## License

This project is proprietary software. All rights reserved.
