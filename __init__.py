#!/usr/bin/env python3
import subprocess
import os
import random

ATTACK_IMAGE = "ctf-attack"
DEFENSE_IMAGE = "ctf-defense"
LOG_DIR_HOST = "/opt/ctf_logs/logs"
PASS_DIR_HOST = "/opt/ctf_logs/passwords"
PASSWORD_FILE = os.path.join(PASS_DIR_HOST, "passwords.txt")


# Team names and SSH ports
TEAMS = [
    ("01", "부릉부릉백부승",   2201, 2301),
    ("02", "가끔씩 툭하고 어셈블리어",   2202, 2302),
    ("03", "KUICS", 2203, 2303),
    ("04", "강민아 온천가자",   2204, 2304),
    ("05", "또봇제로데이찾기",    2205, 2305),
    ("06", "조싸쑤", 2206, 2306),
    ("07", "루나",    2207, 2307),
    ("08", "온천부글부글대작전",   2208, 2308),
    ("09", "명진으로이행시할게요명륜진사갈비",   2209, 2309),
    ("10", "SecurityFact",  2210, 2310),
    ("11", "Team_Kilo",    2211, 2311),
    ("12", "Team_Lima",    2212, 2312),
    ("13", "TEAM_LISA",    2213, 2313),
]

def ensure_password_file():
    os.makedirs(PASS_DIR_HOST, exist_ok=True)
    with open(PASSWORD_FILE, "w") as f:
        f.write("=== TEAM PASSWORDS ===\n\n")


def generate_password():
    return "".join(str(random.randint(0, 9)) for _ in range(6))


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


def create_attack_container(team_num: str, team_name: str, ssh_port: int, password: str):
    container_name = f"team{team_num}_attack"
    hostname = team_name

    print(f"\n=== Starting ATTACK container for {team_name} (team{team_num}, SSH port {ssh_port}) ===")

    # Remove any old container with same name
    remove_container_if_exists(container_name)

    env_vars = [
        f"TEAM_NUM={team_num}",
        f"TEAM_NAME={team_name}",
        "ROLE=attack",
        "LOG_FILE=/logs/can_log.jsonl",
        f"SSH_PORT={ssh_port}",
        f"TEAM_PASSWORD={password}",
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


def create_defense_container(team_num: str, team_name: str, ssh_port: int, password: str):
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
        f"TEAM_PASSWORD={password}",
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
    ensure_password_file()

    print("Starting attack + defense containers...")
    for team_num, team_name, att_ssh, def_ssh in TEAMS:
        password = generate_password()

        create_attack_container(team_num, team_name, att_ssh, password)
        create_defense_container(team_num, team_name, def_ssh, password)
        # write password block
        with open(PASSWORD_FILE, "a") as f:
            f.write(f"TEAM {team_num} ({team_name})\n")
            f.write(f"  Username: team{team_num}\n")
            f.write(f"  Password: {password}\n")
            f.write(f"  Attack SSH:  ssh team{team_num}@<host-ip> -p {att_ssh}\n")
            f.write(f"  Defense SSH: ssh team{team_num}@<host-ip> -p {def_ssh}\n\n")

    
    print("\nDone.")
    print("Attack SSH example:  ssh team01@<host> -p 2201")
    print("Defense SSH example: ssh team01@<host> -p 3201")
    print("Attack/defense passwords in:", os.path.join(PASS_DIR_HOST, "passwords.txt"))
    print("Logs are in:", os.path.join(LOG_DIR_HOST, "can_log.jsonl"))


if __name__ == "__main__":
    main()
