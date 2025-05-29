# AutoGen Data Science Image
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

# Copy your script files
COPY orchestrator.py /workspace/orchestrator.py
COPY WA_Fn-UseC_-HR-Employee-Attrition.csv /workspace/WA_Fn-UseC_-HR-Employee-Attrition.csv
COPY dwh_agents /workspace/dwh_agents
COPY chat_agents /workspace/chat_agents
COPY public /public

# # Install React dependencies if package.json exists
# RUN if [ -f /public/package.json ]; then \
#         cd /public && \
#         npm install @chainlit/react-client recoil && \
#         npm run build; \
#     fi

# Expose Chainlit port
EXPOSE 4200

# Default run command
CMD ["python", "-m", "chainlit", "run", "orchestrator.py", "--host", "0.0.0.0", "--port", "4200"]