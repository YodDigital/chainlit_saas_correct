# AutoGen Data Science Image
FROM python:3.11-slim

# Install essential tools and PostgreSQL client libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    git \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /workspace

# Install Python packages
RUN pip install --no-cache-dir \
    chainlit \
    pyautogen \
    openai \
    "autogen[openai]" \
    psycopg2 \
    pandas \
    numpy \
    sqlalchemy \
    flaml[automl] \
    matplotlib

# Copy your script (optional - better to mount for development)
COPY orchestrator.py /workspace/orchestrator.py
COPY WA_Fn-UseC_-HR-Employee-Attrition.csv /workspace/WA_Fn-UseC_-HR-Employee-Attrition.csv
COPY dwh_agents /workspace/dwh_agents
COPY chat_agents /workspace/chat_agents
COPY public /public

# Expose Chainlit port
EXPOSE 4200

# Default run command (can still be overridden in docker-compose.yml)
CMD ["python", "-m", "chainlit", "run", "orchestrator.py", "--host", "0.0.0.0", "--port", "4200"]


