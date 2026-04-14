# Microsoft Python Dev Container image
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Syft (SBOM generator)
RUN curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Install Grype (vulnerability scanner)
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Install Node.js (required for CodeQL JavaScript analysis and autobuild)
# Remove problematic yarn repository first to avoid GPG key errors
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update && apt-get install -y --no-install-recommends curl unzip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install CodeQL CLI
RUN curl -sSfL https://github.com/github/codeql-cli-binaries/releases/download/v2.25.1/codeql-linux64.zip -o /tmp/codeql.zip \
    && unzip -q /tmp/codeql.zip -d /usr/local \
    && chmod +x /usr/local/codeql/codeql \
    && ln -s /usr/local/codeql/codeql /usr/local/bin/codeql \
    && rm /tmp/codeql.zip

# Pre-download CodeQL query packs into a shared location accessible by all users (e.g. vscode)
RUN mkdir -p /opt/codeql/packages \
    && codeql pack download --dir=/opt/codeql/packages codeql/python-queries \
    && codeql pack download --dir=/opt/codeql/packages codeql/javascript-queries \
    && codeql pack download --dir=/opt/codeql/packages codeql/java-queries \
    && chmod -R a+rX /opt/codeql

# Verify installations
RUN echo "CodeQL version:" && codeql version \
    && echo "Grype version:" && grype version \
    && echo "Node.js version:" && node --version \
    && echo "npm version:" && npm --version

# Set environment variables for uv
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
