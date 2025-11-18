FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install packages (SSH, CAN tools, Python, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server \
        curl \
        ca-certificates \
        bash \
        sudo \
        iproute2 \
        net-tools \
        kmod \
        iputils-ping \
        bc \
        python3 \
        python3-pip \
        can-utils \
        netcat \
        uuid-runtime && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/run/sshd /app

# Python deps
RUN pip3 install --no-cache-dir python-can requests fastapi "uvicorn[standard]"


# SSH config: allow password auth, disable root login, change port
RUN sed -ri 's/^#?PasswordAuthentication\s+.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -ri 's/^#?PermitRootLogin\s+.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -ri 's/^#?Port .*/Port 2222/' /etc/ssh/sshd_config

RUN mkdir -p /app
WORKDIR /app

# Copy scripts
COPY entrypoint.sh /entrypoint.sh
RUN chmod 700 /entrypoint.sh

COPY entry.py /app/entry.py
RUN chmod 755 /app/entry.py

COPY api.py /app/api.py
RUN chmod +x /app/api.py

# Expose SSH
EXPOSE 2222

# Start entrypoint
ENTRYPOINT ["/entrypoint.sh"]
