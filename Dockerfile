from debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-virtualenv \
    parallel \
    myrepos \
    sqlite3 \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt /requirements.txt

# Update pip and then install requirements
RUN pip3 install --break-system-packages --no-cache-dir --upgrade pip && \
    pip3 install --break-system-packages --no-cache-dir -r /requirements.txt

# Mount the code from ./src/ into the container at /src/
# Mount the data directory into the container at /var/log/data
# Mount the git code into the container at /srv/git
WORKDIR /src/
