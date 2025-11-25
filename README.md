# Attack-Defense
This scripts for attack and defense type competition


Preparation 
1. Create docker images for both attack and defense
2. Create log folder and password foler in /opt/ctf_logs make them root owned but writable to other users not readable
3. Create interface vcan0 and can0
4. Configure the inside docker files ip address to host ip or domain
5. Run Init code this gives you the dockers for attack and defense
6. Run SERVER_* codes attack API on 8000 defense on 9000



## ATTACK DOCKER
sudo docker build -f Dockerfile -t ctf-attack .

## DEFENSE DOCKER
sudo docker build -f Dockerfile.defense -t ctf-defense .

Create log folder 
____________________________

sudo mkdir -p /opt/ctf_logs
sudo chmod 733 /opt/ctf_logs
____________________________

RUN PYTHON INIT CODE TO DOCKER UP
===============

python3 __init__.py


______________________________

=================  MANUALLY STARTING THE DOCKER FOR SPECIFIC TEAM =================

sudo docker run -d \
  --name team02_attack \
  --hostname team02_attack \
  --network host \
  --cap-add=NET_ADMIN \
  -e TEAM_NUM=02 \
  -e TEAM_NAME="Team_Bravo" \
  -e ROLE=attack \
  -e LOG_FILE=/logs/can_log.jsonl \
  -e SSH_PORT=2202 \
  -v /opt/ctf_logs:/logs \
  ctf-attack




___________________________ Create docker with team name




ssh tester@localhost -p 2207

cansend can0 440#00005000000000

___________________________


tail -f /opt/ctf_logs/can_log.jsonl

___________________________ check log


===== CHECKING THE PASSWORD FOR USERS =====

After creating the dockers with SSH we can check out the passwords from 

### This folder not mounted on docker which it makes safe and not visible in docker 
/opt/ctf_logs/passwords/passwords.txt

_________________________________
 ## API check on locally


API connectivity check 

On HOST : 

curl http://127.0.0.1:<port>/api/health

from user 

curl http://<server-ip>:<port>/api/health

_____________________________________


Send message 

curl -X POST http://127.0.0.1:8002/api/cansend \
> -H "Content-Type: application/json" \
> -d '{"interface":"can0", "frame":"123#R"}'


===== output =====
{"status":"ok","interface":"can0","frame":"123#R"}


<img width="3213" height="1584" alt="Untitled-2025-11-10-2315" src="https://github.com/user-attachments/assets/8147c5f9-39ea-43ae-a975-dfd75f04a2cd" />


