#!/usr/bin/env python3
import subprocess
import os

ATTACK_IMAGE = "ctf-attack"
DEFENSE_IMAGE = "ctf-defense"
LOG_DIR_HOST = "/opt/ctf_logs"

# Team names and SSH ports
TEAMS = [
    ("01", "Багануур",   2201, 8001, 2301),
    ("02", "Team_Bravo",   2202, 8002, 2302),
    ("03", "Team_Charlie", 2203, 8003, 2303),
    ("04", "Team_Delta",   2204, 8004, 2304),
    ("05", "Team_Echo",    2205, 8005, 2305),
    ("06", "Team_Foxtrot", 2206, 8006, 2306),
    ("07", "Team_Golf",    2207, 8007, 2307),
    ("08", "Team_Hotel",   2208, 8008, 2308),
    ("09", "Team_India",   2209, 8009, 2309),
    ("10", "Team_Juliet",  2210, 8010, 2310),
    ("11", "Team_Kilo",    2211, 8011, 2311),
    ("12", "Team_Lima",    2212, 8012, 2312),
    ("13", "Team_Mike",    2213, 8013, 2313),
    ("14", "Team_November",2214, 8014, 2314),
    ("15", "Team_Oscar",   2215, 8015, 2315),
    ("16", "Team_Papa",    2216, 8016, 2316),
]


def run(cmd):
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"Command failed with code {result.returncode}")
    return result.returncode


def ensure_log_dir():
    if not os.path.isdir(LOG_DIR_HOST):
        print(f"Creating log dir {LOG_DIR_HOST}")
        os.makedirs(LOG_DIR_HOST, exist_ok=True)


def remove_container_if_exists(name: str):
    # docker rm -f <name> (ignore errors)
    run(["sudo", "docker", "rm", "-f", name])


def create_attack_container(team_num: str, team_name: str, ssh_port: int, api_port: int):
    container_name = f"team{team_num}_attack"
    hostname = team_name

    print(f"\n=== Starting ATTACK container for {team_name} (team{team_num}, SSH port {ssh_port}, API port {api_port}) ===")

    # Remove any old container with same name
    remove_container_if_exists(container_name)

    env_vars = [
        f"TEAM_NUM={team_num}",
        f"TEAM_NAME={team_name}",
        "ROLE=attack",
        "LOG_FILE=/logs/can_log.jsonl",
        f"SSH_PORT={ssh_port}",
        f"API_PORT={api_port}",
        # f"API_KEY=some-secret-{team_num}",
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


def create_defense_container(team_num: str, team_name: str, ssh_port: int):
    container_name = f"team{team_num}_defense"
    hostname = team_name

    print(f"\n=== Starting DEFENSE container for {team_name} (team{team_num}, SSH port {ssh_port}) ===")

    # Remove any old container with same name
    remove_container_if_exists(container_name)

    env_vars = [
        f"TEAM_NUM={team_num}",
        f"TEAM_NAME={team_name}",
        "ROLE=defense",
        f"SSH_PORT={ssh_port}",
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

    cmd.append(DEFENSE_IMAGE)

    run(cmd)

def main():
    ensure_log_dir()

    print("Starting attack + defense containers...")
    for team_num, team_name, att_ssh, api_port, def_ssh in TEAMS:
        create_attack_container(team_num, team_name, att_ssh, api_port)
        create_defense_container(team_num, team_name, def_ssh)
    
    print("\nDone.")
    print("Attack SSH example:  ssh team01@<host> -p 2201")
    print("Defense SSH example: ssh team01@<host> -p 3201")
    print("Attack/defense passwords in:", os.path.join(LOG_DIR_HOST, "ssh_passwords.txt"),
          "and", os.path.join(LOG_DIR_HOST, "defense_passwords.txt"))
    print("Logs are in:", os.path.join(LOG_DIR_HOST, "can_log.jsonl"))


if __name__ == "__main__":
    main()
