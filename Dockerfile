# ---------- Frontend build ----------
FROM node:18 AS frontend-build
WORKDIR /app/frontend
COPY blip-react/package*.json ./
RUN npm install
COPY blip-react/ .
RUN npm run build

# ---------- Backend build ----------
FROM python:3.11-slim AS backend-build
WORKDIR /app/backend
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ .

# ---------- Runtime ----------
FROM python:3.11-slim
WORKDIR /app

# Install Node.js for serving the frontend
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g serve && \
    apt-get remove -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY --from=backend-build /app/backend /app/backend
# Copy frontend
COPY --from=frontend-build /app/frontend/build /app/frontend/build

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

EXPOSE 3000 8000
CMD ["sh", "-c", "python /app/backend/cron.py & serve -s /app/frontend/build -l 3000"]