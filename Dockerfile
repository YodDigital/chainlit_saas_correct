# Multi-stage build: React frontend + Python backend
FROM node:18-alpine AS react-build

# Build React frontend
WORKDIR /app/frontend
COPY public/package*.json ./
RUN npm install
COPY public/ .
RUN npm run build

# Main Python application stage
FROM python:3.11-slim

# Install essential tools, PostgreSQL client libraries, and Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    git \
    libpq-dev \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /workspace

RUN pip install --upgrade chainlit

# Install Python packages
RUN pip install --no-cache-dir \
    pyautogen \
    openai \
    "autogen[openai]" \
    psycopg2 \
    pandas \
    numpy \
    sqlalchemy \
    flaml[automl] \
    matplotlib

# Copy built React files from the first stage
COPY --from=react-build /app/frontend/build ./static/

# Copy your Python application files
COPY orchestrator.py /workspace/orchestrator.py
COPY WA_Fn-UseC_-HR-Employee-Attrition.csv /workspace/WA_Fn-UseC_-HR-Employee-Attrition.csv
COPY dwh_agents /workspace/dwh_agents
COPY chat_agents /workspace/chat_agents

# Copy the source React files (for development)
COPY public /workspace/public

# Expose Chainlit port
EXPOSE 4200

# Default run command (can still be overridden in docker-compose.yml)
CMD ["python", "-m", "chainlit", "run", "orchestrator.py", "--host", "0.0.0.0", "--port", "4200"]