#!/usr/bin/env bash
set -e

# Load required modules
sudo modprobe can
sudo modprobe vcan

# --- Real or virtual can0 ---
# For virtual testing
if ! ip link show can0 &>/dev/null; then
    echo "[+] Creating vcan can0"
    sudo ip link add dev can0 type vcan
fi
sudo ip link set can0 up

# --- vcan1..vcan16 for teams ---
for i in $(seq 1 16); do
    IF="vcan${i}"
    if ! ip link show "${IF}" &>/dev/null; then
        echo "[+] Creating ${IF}"
        sudo ip link add dev "${IF}" type vcan
    fi
    sudo ip link set "${IF}" up
done

echo "[+] CAN interfaces:"
ip link show type can

