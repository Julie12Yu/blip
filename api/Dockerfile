FROM python:3.12-slim

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /api

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY cron.py .

# Copy cron job definition
COPY cronjob /etc/cron.d/cronjob

# Give execution rights
RUN chmod 0644 /etc/cron.d/cronjob && crontab /etc/cron.d/cronjob

# Create log file
RUN touch /var/log/cron.log

# Env vars (set at runtime via --env-file .env or -e). See .env.model.
ENV SUPABASE_URL=
ENV SUPABASE_KEY=
ENV GPT_KEY=
ENV GUARDIAN_API_KEY=
ENV NYT_API_KEY=

# Run cron + stream logs
CMD ["sh", "-c", "cron && tail -f /var/log/cron.log"]
