#!/usr/bin/env python3
import subprocess
import os
import random
import json

ATTACK_IMAGE = "ctf-attack"
DEFENSE_IMAGE = "ctf-defense"

LOG_DIR_HOST = "/opt/ctf_logs/logs"         # mounted into containers
PASS_DIR_HOST = "/opt/ctf_logs/passwords"   # host-only
PASSWORD_FILE = os.path.join(PASS_DIR_HOST, "passwords.txt")
API_KEYS_FILE = os.path.join(PASS_DIR_HOST, "api_keys.json")

# Scoring API endpoint (defense containers use host network)
SCORE_API_URL = "http://127.0.0.1:9000/api/ids/report"

# Team names and ports: (team_num, team_name, att_ssh, att_api_port, def_ssh)
TEAMS = [
    ("01", "Team_Alpha",    2201, 8001, 2301),
    ("02", "Team_Bravo",    2202, 8002, 2302),
    ("03", "Team_Charlie",  2203, 8003, 2303),
    ("04", "Team_Delta",    2204, 8004, 2304),
    ("05", "Team_Echo",     2205, 8005, 2305),
    ("06", "Team_Foxtrot",  2206, 8006, 2306),
    ("07", "Team_Golf",     2207, 8007, 2307),
    ("08", "Team_Hotel",    2208, 8008, 2308),
    ("09", "Team_India",    2209, 8009, 2309),
    ("10", "Team_Juliet",   2210, 8010, 2310),
    ("11", "Team_Kilo",     2211, 8011, 2311),
    ("12", "Team_Lima",     2212, 8012, 2312),
    ("13", "Team_Mike",     2213, 8013, 2313),
    ("14", "Team_November", 2214, 8014, 2314),
    ("15", "Team_Oscar",    2215, 8015, 2315),
    ("16", "Team_Papa",     2216, 8016, 2316),
]


def generate_password() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(6))


def run(cmd):
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"Command failed with code {result.returncode}")
    return result.returncode


def ensure_dirs():
    os.makedirs(LOG_DIR_HOST, exist_ok=True)
    os.makedirs(PASS_DIR_HOST, exist_ok=True)


def init_password_file():
    with open(PASSWORD_FILE, "w") as f:
        f.write("=== TEAM PASSWORDS ===\n\n")


def remove_container_if_exists(name: str):
    run(["sudo", "docker", "rm", "-f", name])


def create_attack_container(team_num: str, team_name: str, ssh_port: int, api_port: int, password: str):
    container_name = f"team{team_num}_attack"
    hostname = container_name

    print(f"\n=== Starting ATTACK container for {team_name} (team{team_num}, SSH {ssh_port}, API {api_port}) ===")
    remove_container_if_exists(container_name)

    env_vars = [
        f"TEAM_NUM={team_num}",
        f"TEAM_NAME={team_name}",
        "ROLE=attack",
        "LOG_FILE=/logs/can_log.jsonl",
        f"SSH_PORT={ssh_port}",
        f"API_PORT={api_port}",
        f"TEAM_PASSWORD={password}",      # SSH password
        f"SCORE_API_KEY={password}",      # API key (same)
        f"SCORE_API={SCORE_API_URL}",
    ]

    cmd = [
        "sudo", "docker", "run", "-d",
        "--name", container_name,
        "--hostname", hostname,
        "--network", "host",
        "--cap-add=NET_ADMIN",
        "-v", f"{LOG_DIR_HOST}:/logs",
    ]
    for e in env_vars:
        cmd.extend(["-e", e])
    cmd.append(ATTACK_IMAGE)

    run(cmd)


def create_defense_container(team_num: str, team_name: str, ssh_port: int, password: str):
    container_name = f"team{team_num}_defense"
    hostname = container_name

    print(f"\n=== Starting DEFENSE container for {team_name} (team{team_num}, SSH {ssh_port}) ===")
    remove_container_if_exists(container_name)

    env_vars = [
        f"TEAM_NUM={team_num}",
        f"TEAM_NAME={team_name}",
        "ROLE=defense",
        f"SSH_PORT={ssh_port}",
        f"TEAM_PASSWORD={password}",      # SSH password
        f"SCORE_API_KEY={password}",      # API key (same)
        f"SCORE_API={SCORE_API_URL}",
    ]

    cmd = [
        "sudo", "docker", "run", "-d",
        "--name", container_name,
        "--hostname", hostname,
        "--network", "host",
        "--cap-add=NET_ADMIN",
        # NOTE: if you DON'T want defense to see logs, remove this mount:
        "-v", f"{LOG_DIR_HOST}:/logs",
    ]
    for e in env_vars:
        cmd.extend(["-e", e])
    cmd.append(DEFENSE_IMAGE)

    run(cmd)


def main():
    ensure_dirs()
    init_password_file()

    api_keys = {}  # password -> team info

    print("Starting attack + defense containers...")
    for team_num, team_name, att_ssh, api_port, def_ssh in TEAMS:
        password = generate_password()

        create_attack_container(team_num, team_name, att_ssh, api_port, password)
        create_defense_container(team_num, team_name, def_ssh, password)

        api_keys[password] = {
            "team_num": team_num,
            "team_name": team_name,
        }

        with open(PASSWORD_FILE, "a") as f:
            f.write(f"TEAM {team_num} ({team_name})\n")
            f.write(f"  Username: team{team_num}\n")
            f.write(f"  Password / API key: {password}\n")
            f.write(f"  Attack SSH:  ssh team{team_num}@<host-ip> -p {att_ssh}\n")
            f.write(f"  Defense SSH: ssh team{team_num}@<host-ip> -p {def_ssh}\n\n")

    # Write API key mapping for scoring_api.py
    with open(API_KEYS_FILE, "w") as f:
        json.dump(api_keys, f, indent=2, ensure_ascii=False)

    print("\nDone.")
    print("Attack SSH example:  ssh team01@<host-ip> -p 2201")
    print("Defense SSH example: ssh team01@<host-ip> -p 2301")
    print("Passwords file:", PASSWORD_FILE)
    print("API keys file:", API_KEYS_FILE)
    print("Logs dir (mounted):", LOG_DIR_HOST)


if __name__ == "__main__":
    main()
