#!/usr/bin/env bash
set -e

# Basic env from docker run
TEAM_NUM="${TEAM_NUM:-00}"
TEAM_NAME="${TEAM_NAME:-Team_${TEAM_NUM}}"
ROLE="defense"
SSH_PORT="${SSH_PORT:-3200}"

# Central log dir for passwords (host: /opt/ctf_logs, container: /logs)
LOG_DIR="/logs"
PASS_FILE="${LOG_DIR}/defense_passwords.txt"

# Create /logs (host should mount /opt/ctf_logs:/logs)
mkdir -p "$LOG_DIR"

USERNAME="team${TEAM_NUM}"

if ! id "$USERNAME" &>/dev/null; then
    useradd -m -s /bin/bash "$USERNAME"

    # Generate 6-digit numeric password
    PASSWORD="$(tr -dc '0-9' </dev/urandom | head -c 6)"
    echo "${USERNAME}:${PASSWORD}" | chpasswd

    # Log credentials for organizer (host: /opt/ctf_logs/defense_passwords.txt)
    {
        echo "TEAM_NUM=${TEAM_NUM} TEAM_NAME=${TEAM_NAME} USER=${USERNAME} PASSWORD=${PASSWORD} SSH_PORT=${SSH_PORT}"
    } >> "$PASS_FILE"
    chmod 600 "$PASS_FILE" 2>/dev/null || true
fi

HOME_DIR="$(getent passwd "$USERNAME" | cut -d: -f6)"

# Ensure .bashrc is loaded on login
if ! grep -q ". \$HOME/.bashrc" "$HOME_DIR/.profile" 2>/dev/null; then
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
#### DEF TEAM ENV END ####
EOF
fi

chown "$USERNAME:$USERNAME" "$HOME_DIR/.bashrc" "$HOME_DIR/.profile"

# Lock down entrypoint
chmod 700 /entrypoint.sh

# Start SSH on given port
exec /usr/sbin/sshd -D -p "$SSH_PORT"
