# QProcess Chatbot Deployment Guide

This guide explains how to deploy the QProcess Chatbot application using Docker.

## Prerequisites

### What the Client Needs:

1. **Docker Desktop** (Windows/Mac/Linux)
   - Download from: https://www.docker.com/products/docker-desktop/
   - Install and start Docker Desktop

2. **SQL Server Database**
   - SQL Server 2019 or later
   - The `QTasks3` database with required tables and stored procedures
   - ODBC Driver 17 for SQL Server

3. **Claude API Key**
- Sign up at: https://console.anthropic.com/
   - Get your API key

## Quick Start

### 1. Download the Application

The client should receive a ZIP file containing:
```
qprocess-chatbot/
├── docker-compose.yml
├── env.example
├── DEPLOYMENT.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── chatbot/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
└── database/
    ├── install_stored_procedure.sql
    └── verify_installation.sql
```

### 2. Configure Environment Variables

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your actual values:
   ```env
   # Database Configuration
   DB_NAME=QTasks3
   DB_USER=
   DB_PASSWORD=
   DB_HOST=YOUR_SQL_SERVER_NAME
   DB_PORT=

   # AI Service Configuration
   CLAUDE_API_KEY=your-actual-claude-api-key

   # Django Configuration
   SECRET_KEY=your-django-secret-key
   DEBUG=False
   ```

### 3. Install Database Stored Procedure

1. Open SQL Server Management Studio
2. Connect to your SQL Server
3. Select the `QTasks3` database
4. Run the script: `database/install_stored_procedure.sql`
5. Verify installation: `database/verify_installation.sql`

### 4. Start the Application

```bash
# Build and start all services
docker-compose up -d

# Check if services are running
docker-compose ps

# View logs
docker-compose logs -f
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

## Configuration Options

### Database Connection

#### Windows Authentication (Recommended)
```env
DB_USER=
DB_PASSWORD=
DB_HOST=YOUR_SERVER_NAME\\INSTANCE_NAME
```

#### SQL Server Authentication
```env
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=YOUR_SERVER_NAME
DB_PORT=1433
```

### Custom Ports

To change ports, edit `docker-compose.yml`:
```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Change 8001 to your preferred port
  frontend:
    ports:
      - "3001:3000"  # Change 3001 to your preferred port
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify SQL Server is running
   - Check firewall settings
   - Ensure ODBC Driver 17 is installed
   - Test connection in SQL Server Management Studio

2. **Port Already in Use**
   - Change ports in `docker-compose.yml`
   - Or stop other services using those ports

3. **Permission Denied**
   - Run Docker Desktop as Administrator (Windows)
   - Ensure user has Docker permissions

4. **Frontend Can't Connect to Backend**
   - Check if both containers are running: `docker-compose ps`
   - Verify CORS settings in backend
   - Check network connectivity

### Useful Commands

```bash
# Stop all services
docker-compose down

# Rebuild containers
docker-compose up --build

# View specific service logs
docker-compose logs backend
docker-compose logs frontend

# Access container shell
docker-compose exec backend bash
docker-compose exec frontend sh

# Remove all containers and volumes
docker-compose down -v
```

### Logs Location

- **Backend logs**: `/app/logs/django.log` (inside container)
- **Docker logs**: `docker-compose logs -f`

## Production Considerations

### Security
- Change default `SECRET_KEY`
- Use strong passwords
- Configure firewall rules
- Enable HTTPS in production

### Performance
- Use production database server
- Configure proper logging
- Set up monitoring
- Consider load balancing

### Backup
- Regular database backups
- Application code version control
- Environment configuration backup

## Support

For issues or questions:
1. Check the logs: `docker-compose logs`
2. Verify database connection
3. Test API endpoints: http://localhost:8000/api/users/
4. Contact support with error details

## File Structure

```
qprocess-chatbot/
├── docker-compose.yml          # Main deployment configuration
├── .env                        # Environment variables (create from env.example)
├── backend/
│   ├── Dockerfile             # Backend container configuration
│   ├── requirements.txt       # Python dependencies
│   └── chatbot/              # Django application
├── frontend/
│   ├── Dockerfile            # Frontend container configuration
│   ├── package.json          # Node.js dependencies
│   └── src/                  # React application
└── database/
    ├── install_stored_procedure.sql    # Database setup
    └── verify_installation.sql         # Verification script
```
