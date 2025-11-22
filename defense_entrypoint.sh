#!/usr/bin/env bash
set -e

# Basic env from docker run
TEAM_NUM="${TEAM_NUM:-00}"
TEAM_NAME="${TEAM_NAME:-Team_${TEAM_NUM}}"
ROLE="defense"
SSH_PORT="${SSH_PORT:-2222}"

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


USERNAME="team${TEAM_NUM}"

if ! id "$USERNAME" &>/dev/null; then
    useradd -m -s /bin/bash "$USERNAME"

    if [ -n "$TEAM_PASSWORD" ]; then
        PASSWORD="$TEAM_PASSWORD"
    else
        PASSWORD="$(tr -dc '0-9' </dev/urandom | head -c 6)"
    fi

    echo "${USERNAME}:${PASSWORD}" | chpasswd
fi

HOME_DIR="$(getent passwd "$USERNAME" | cut -d: -f6)"

if [ -f /app/user_custom.py ]; then
    # Only copy if it doesn't already exist (so user edits aren't overwritten)
    if [ ! -f "$HOME_DIR/user_custom.py" ]; then
        cp /app/user_custom.py "$HOME_DIR/user_custom.py"
        chown "$USERNAME:$USERNAME" "$HOME_DIR/user_custom.py"
        chmod 644 "$HOME_DIR/user_custom.py"
    fi
fi


# Ensure .bashrc is loaded on login
if ! grep -q "source ~/.bashrc" "$HOME_DIR/.profile" 2>/dev/null && \
   ! grep -q ". ~/.bashrc" "$HOME_DIR/.profile" 2>/dev/null; then
    echo 'if [ -f "$HOME/.bashrc" ]; then . "$HOME/.bashrc"; fi' >> "$HOME_DIR/.profile"
fi

# Inject team env into .bashrc (no sudo, no secret stuff)
if ! grep -q "#### DEF TEAM ENV START ####" "$HOME_DIR/.bashrc" 2>/dev/null; then
cat <<EOF >> "$HOME_DIR/.bashrc"

#### DEF TEAM ENV START ####
export TEAM_NUM="${TEAM_NUM}"
export TEAM_NAME="${TEAM_NAME}"
export ROLE="${ROLE}"
# Input CAN (mixed data from testbed)
export CAN_INPUT_IF="\${CAN_INPUT_IF:-can0}"
# Output CAN (team-specific virtual channel)
export CAN_OUTPUT_IF="\${CAN_OUTPUT_IF:-vcan${TEAM_NUM#0}}"
export SECRET_TAG="${SECRET_TAG}"
export PYTHONPATH="/app:${PYTHONPATH:-}"
#### DEF TEAM ENV END ####
EOF
fi

chown "$USERNAME:$USERNAME" "$HOME_DIR/.bashrc" "$HOME_DIR/.profile"

# Lock down entrypoint
chmod 700 /entrypoint.sh

# Start SSH on given port
exec /usr/sbin/sshd -D -p "$SSH_PORT" -o ListenAddress=0.0.0.0
