import socket
import subprocess
import sys
import re


def get_ip_info_windows():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        result = subprocess.check_output("ipconfig /all", shell=True).decode('cp866')
        lines = result.split('\n')
        subnet_mask = ""
        found_ip = False

        for i, line in enumerate(lines):
            if ip_address in line:
                found_ip = True
            if found_ip and "Маска подсети" in line:
                subnet_mask = line.split(':')[-1].strip()
                break

        return ip_address, subnet_mask

    except Exception as e:
        return f"Ошибка: {e}", ""


def get_ip_info_linux():
    try:
        ip_address = subprocess.check_output("hostname -I", shell=True).decode('utf-8').split()[0]
        interface = subprocess.check_output(f"ip route | grep {ip_address} | awk '{{print $3}}'", shell=True).decode('utf-8').strip()

        if not interface:
            interface = subprocess.check_output("ip route | grep default | awk '{print $5}'", shell=True).decode('utf-8').strip()

        result = subprocess.check_output(f"ip addr show {interface}", shell=True).decode('utf-8')
        mask_match = re.search(r'inet\s+' + re.escape(ip_address) + r'/(\d+)', result)

        if mask_match:
            cidr = int(mask_match.group(1))
            subnet_mask = convert_cidr_to_mask(cidr)
            return ip_address, subnet_mask
        else:
            return ip_address, "Cannot define mask"

    except Exception as e:
        return f"Error: {e}", ""


def get_ip_info_mac():
    try:
        ip_address = subprocess.check_output("ipconfig getifaddr en0 || ipconfig getifaddr en1", shell=True).decode('utf-8').strip()
        result = subprocess.check_output("ifconfig en0 2>/dev/null || ifconfig en1 2>/dev/null", shell=True).decode('utf-8')
        mask_match = re.search(r'netmask\s+(0x[0-9a-fA-F]+)', result)

        if mask_match:
            hex_mask = mask_match.group(1)
            subnet_mask = convert_hex_to_mask(hex_mask)
            return ip_address, subnet_mask
        else:
            return ip_address, "Cannot define mask"

    except Exception as e:
        return f"Error: {e}", ""


def convert_cidr_to_mask(cidr):
    mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
    return '.'.join([str((mask >> (8 * i)) & 0xff) for i in range(3, -1, -1)])


def convert_hex_to_mask(hex_str):
    if hex_str.startswith("0x"):
        hex_str = hex_str[2:]

    int_mask = int(hex_str, 16)

    return '.'.join([str((int_mask >> (8 * i)) & 0xff) for i in range(3, -1, -1)])


def main():
    if sys.platform.startswith('win'):
        ip_address, subnet_mask = get_ip_info_windows()
    elif sys.platform.startswith('linux'):
        ip_address, subnet_mask = get_ip_info_linux()
    elif sys.platform.startswith('darwin'):
        ip_address, subnet_mask = get_ip_info_mac()
    else:
        ip_address = "Unknown os"
        subnet_mask = ""

    print(f"IP-address: {ip_address}")
    print(f"Mask: {subnet_mask}")


if __name__ == "__main__":
    main()