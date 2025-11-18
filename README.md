# Attack-Defense
This scripts for attack and defense type competition


To test run 

SETUP run setup.sh to create interfaces
BUILD docker first 

## ATTACK DOCKER
sudo docker build -f Dockerfile -t ctf-attack .

## DEFENSE DOCKER
sudo docker build -f Dockerfile.defense -t ctf-defense .

RUN PYTHON INIT CODE TO DOCKER UP

python3 __init__.py

===============

Create can0 interface 
____________________________

sudo modprobe vcan
sudo ip link add dev can0 type vcan
sudo ip link set can0 up
ip link show can0

===============

Create log folder 
____________________________

sudo mkdir -p /opt/ctf_logs
sudo chmod 777 /opt/ctf_logs

===============


Create docker image and run 

______________________________

docker build -t ctf-attack .

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
# password: ******

cansend can0 440#00005000000000

___________________________


tail -f /opt/ctf_logs/can_log.jsonl

___________________________ check log


===== CHECKING THE PASSWORD FOR USERS =====

After creating the dockers with SSH we can check out the passwords from 


/opt/ctf_logs/ssh_passwords.txt 


you need privilege to read them 




++++++++++++ API ++++++++++++

API connectivity check 


On HOST : 

curl http://127.0.0.1:<port>/api/health

from user 

curl http://<server-ip>:<port>/api/health

_____________________________________


Send message 

curl -X POST http://127.0.0.1:8002/api/cansend \
> -H "Content-Type: application/json" \
> -H "X-Username: $USER" \
> -d '{"interface":"can0", "frame":"123#R"}'


===== output =====
{"status":"ok","interface":"can0","frame":"123#R"}
