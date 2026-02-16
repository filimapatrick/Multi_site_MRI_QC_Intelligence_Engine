# Multi-stage build for MRI QC Intelligence Engine
FROM python:3.9-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libblas-dev \
    liblapack-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.9-slim

# Set labels
LABEL maintainer="Patrick Filima <patrick.filima@example.com>"
LABEL description="MRI Quality Control Intelligence Engine"
LABEL version="0.1.0"

# Create non-root user for security
RUN groupadd -r qcuser && useradd -r -g qcuser qcuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libblas3 \
    liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY setup.py .
COPY README.md .
COPY qc_config.yaml .

# Install the package in production mode
RUN pip install --no-deps .

# Create directories for data and outputs
RUN mkdir -p /data /output /tmp/mri_qc && \
    chown -R qcuser:qcuser /app /data /output /tmp/mri_qc

# Switch to non-root user
USER qcuser

# Set environment variables
ENV PYTHONPATH=/app/src
ENV MRI_QC_CONFIG=/app/qc_config.yaml
ENV MRI_QC_TEMP_DIR=/tmp/mri_qc

# Expose port for API (optional)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import mri_qc_intelligence; print('OK')" || exit 1

# Default command
ENTRYPOINT ["qc_engine"]
CMD ["--help"]

# Usage examples:
# docker run -v /path/to/bids:/data -v /path/to/output:/output \
#            mri-qc-intelligence --bids-dir /data --output-dir /output
#
# docker run -p 8000:8000 mri-qc-intelligence qc_api
#
# docker run -it mri-qc-intelligence --bids-dir /data --modality T1w