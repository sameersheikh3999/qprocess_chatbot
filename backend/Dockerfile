# Use Python 3.11 slim image
FROM python:3.11-slim

ARG DJANGO_ALLOWED_HOSTS

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=chatbot.settings
ENV DJANGO_ALLOWED_HOSTS=$DJANGO_ALLOWED_HOSTS

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        unixodbc \
        unixodbc-dev \
        curl \
        gnupg2 \
        iputils-ping

# Install dependencies for adding Microsoft repo (Debian no longer includes apt-key, so don't try that method)
RUN apt-get update && apt-get install -y --no-install-recommends \
		ca-certificates curl gnupg \
	&& rm -rf /var/lib/apt/lists/*

# Add Microsoft GPG key 
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
		| gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

# Add Microsoft SQL Server ODBC repo (recommended method for Debian 12/bookworm -- which is the underlay for the python:3.11-slim image)
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
		> /etc/apt/sources.list.d/mssql-release.list
  
# Install msodbcsql18
RUN apt-get update \
	&& ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools18 unixodbc \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/* \
	&& export PATH="$PATH:/opt/mssql-tools17/bin"

## sqlcmd -S $DB_HOST,$DB_PORT -U $DB_USER -P $DB_PASSWORD -C -Q "SELECT TOP 5 FullName,Email FROM $DB_NAME.dbo.QCheck_Users WHERE IsDeleted=0;"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY chatbot .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Run the application
## Use the EntryPoint below instead, so that we can make sure all the initialization/migrations are done before startup.
##CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
ENTRYPOINT ["./docker-entrypoint.sh"]
