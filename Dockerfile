# Vascular_P app image: uses vascular_base (build with Base_Image_Docker_File first).
# Build base: docker build -f Base_Image_Docker_File -t vascular_base .
FROM vascular_base

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and entrypoint
COPY project/ ./project/
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app/project

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "project.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
