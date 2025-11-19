#!/bin/bash
set -e

# ===== Basic env =====
TEAM_NUM="${TEAM_NUM:-00}"  
TEAM_NAME="${TEAM_NAME:-Team_${TEAM_NUM}}"
ROLE="${ROLE:-attack}"
SSH_PORT="${SSH_PORT:-2222}"
LOG_FILE="${LOG_FILE:-/logs/can_log.jsonl}"   # If host mounts /opt/ctf_logs:/logs, we set LOG_FILE=/logs/can_log.jsonl
API_PORT="${API_PORT:-8000}"
API_KEY="${API_KEY:-}"

# ===== Secret tag (unique per container) =====

if [ -f /etc/container_secret ]; then
    SECRET_TAG="$(cat /etc/container_secret)"
else
    if command -v uuidgen >/dev/null 2>&1; then
        SECRET_TAG="$(uuidgen)"
    else
        SECRET_TAG="$(head -c 16 /dev/urandom | xxd -p)"
    fi
    echo "$SECRET_TAG" > /etc/container_secret
fi

export TEAM_NUM TEAM_NAME ROLE SECRET_TAG LOG_FILE SSH_PORT API_PORT API_KEY

# ===== Create user if not exists =====
USERNAME="team${TEAM_NUM}"

if ! id "$USERNAME" &>/dev/null; then
    useradd -m -s /bin/bash "$USERNAME"

    if [ -n "$TEAM_PASSWORD" ]; then
        PASSWORD="$TEAM_PASSWORD"
    else
        PASSWORD="$(tr -dc '0-9' </dev/urandom | head -c 6)"
    fi
    echo "$USERNAME:$PASSWORD" | chpasswd

    # No sudo for you :V
    # echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

    # Log the password for the organizer (host sees this as /opt/ctf_logs/ssh_passwords.txt)
    # PASS_FILE="/logs/ssh_passwords.txt"
    #{
    #    echo "TEAM_NUM=$TEAM_NUM TEAM_NAME=$TEAM_NAME USER=$USERNAME PASSWORD=$PASSWORD SSH_PORT=$SSH_PORT"
    #} >> "$PASS_FILE"

    # Make it readable only by root (inside container)
    #chmod 600 "$PASS_FILE" 2>/dev/null || true
fi

HOME_DIR="$(getent passwd "$USERNAME" | cut -d: -f6)"

# ===== Ensure .bashrc is loaded on SSH login =====
if ! grep -q "source ~/.bashrc" "$HOME_DIR/.profile" 2>/dev/null && \
   ! grep -q ". ~/.bashrc" "$HOME_DIR/.profile" 2>/dev/null; then
    echo 'if [ -f "$HOME/.bashrc" ]; then . "$HOME/.bashrc"; fi' >> "$HOME_DIR/.profile"
fi

# ===== Inject TEAM env into .bashrc (so SSH sessions get it) =====
if ! grep -q "#### TEAM ENV START ####" "$HOME_DIR/.bashrc" 2>/dev/null; then
cat <<EOF >> "$HOME_DIR/.bashrc"

#### TEAM ENV START ####
export TEAM_NUM="$TEAM_NUM"
export TEAM_NAME="$TEAM_NAME"
export ROLE="$ROLE"
export LOG_FILE="$LOG_FILE"
export SECRET_TAG="$SECRET_TAG"
export CONTAINER_NAME="team${TEAM_NUM}_attack"
#### TEAM ENV END ####
EOF
fi

# ===== CAN wrappers in .bashrc (only once) =====
if ! grep -q "==== CAN WRAPPERS START ====" "$HOME_DIR/.bashrc" 2>/dev/null; then
cat << 'EOF' >> "$HOME_DIR/.bashrc"

# ==== CAN WRAPPERS START ====
candump() {
    # No need to log candump so deleted the log section 
    # Call the real candump
    command candump "$@"
}

cansend() {
    # Log the command (metadata goes via TCP, not CAN)
    python3 /app/entry.py log "CMD=cansend IF=$1 ARGS=\"$*\" USER=$USER"
    # Call the real cansend
    command cansend "$@"
}
# ==== CAN WRAPPERS END ====
EOF
fi

chown "$USERNAME:$USERNAME" "$HOME_DIR/.bashrc" "$HOME_DIR/.profile"

# ===== Start HTTP API fastapi + uvicorn =====
cd /app
uvicorn api:app --host 0.0.0.0 --port "$API_PORT" >> /var/log/api.log 2>&1 &

# ===== Start SSH daemon in the foreground =====
exec /usr/sbin/sshd -D -p "$SSH_PORT"