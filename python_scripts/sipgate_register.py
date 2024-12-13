import socket
import hashlib
import os
import time
import re
from dotenv import load_dotenv
import random

# Load environment variables from .env file
load_dotenv()

# Retrieve SIP credentials from environment variables
sip_id = os.getenv("SIP_ID")
sip_password = os.getenv("SIP_PASSWORD")
sip_domain = os.getenv("SIP_DOMAIN")

# SIP server details
sip_server = sip_domain
sip_port = 5060
local_port = 5060  # Port for your SIP client

def get_local_ip():
    """Determine local IP address by connecting to the SIP server."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((sip_server, sip_port))
        return s.getsockname()[0]

def generate_branch():
    """Generate a unique branch parameter for the Via header."""
    return f"z9hG4bK{random.randint(100000, 999999)}"

def send_register(cseq):
    """Send a SIP REGISTER message."""
    local_ip = get_local_ip()
    branch = generate_branch()
    sip_message = (
        f"REGISTER sip:{sip_server} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"To: <sip:{sip_id}@{sip_server}>\r\n"
        f"From: <sip:{sip_id}@{sip_server}>;tag=1928301774\r\n"
        f"Call-ID: a84b4c76e66710\r\n"
        f"CSeq: {cseq} REGISTER\r\n"
        f"Contact: <sip:{sip_id}@{local_ip}:{local_port}>\r\n"
        f"Expires: 3600\r\n"
        f"Content-Length: 0\r\n\r\n"
    )
    print(f"Sending REGISTER with CSeq: {cseq}, Branch: {branch}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        sock.sendto(sip_message.encode(), (sip_server, sip_port))
        response, _ = sock.recvfrom(4096)
        response_text = response.decode()
        print("Received response:")
        print(response_text)
        return response_text
    except socket.error as e:
        print(f"Sipgate Registration Error: {e}")
        return None
    finally:
        sock.close()

def handle_401(response, cseq):
    """Handle 401 Unauthorized response and send authenticated REGISTER."""
    print("Handling 401 Unauthorized response")
    # Use regex to extract realm and nonce
    match = re.search(r'WWW-Authenticate: Digest realm="([^"]+)", nonce="([^"]+)"', response)
    if match:
        realm, nonce = match.groups()
        print(f"Extracted realm: {realm}, nonce: {nonce}")
    else:
        print("Failed to parse WWW-Authenticate header.")
        return None

    # Compute HA1, HA2, and response
    ha1 = hashlib.md5(f"{sip_id}:{realm}:{sip_password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"REGISTER:sip:{sip_server}".encode()).hexdigest()
    response_digest = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
    print(f"Computed HA1: {ha1}, HA2: {ha2}, response: {response_digest}")

    # Send authenticated REGISTER
    local_ip = get_local_ip()
    branch = generate_branch()
    auth_message = (
        f"REGISTER sip:{sip_server} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"To: <sip:{sip_id}@{sip_server}>\r\n"
        f"From: <sip:{sip_id}@{sip_server}>;tag=1928301774\r\n"
        f"Call-ID: a84b4c76e66710\r\n"
        f"CSeq: {cseq} REGISTER\r\n"
        f"Contact: <sip:{sip_id}@{local_ip}:{local_port}>\r\n"
        f"Authorization: Digest username=\"{sip_id}\", realm=\"{realm}\", nonce=\"{nonce}\", uri=\"sip:{sip_server}\", response=\"{response_digest}\"\r\n"
        f"Expires: 3600\r\n"
        f"Content-Length: 0\r\n\r\n"
    )
    print(f"Sending authenticated REGISTER with CSeq: {cseq}, Branch: {branch}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        sock.sendto(auth_message.encode(), (sip_server, sip_port))
        response, _ = sock.recvfrom(4096)
        response_text = response.decode()
        print("Received response:")
        print(response_text)
        return response_text
    except socket.error as e:
        print(f"Sipgate Auth Registration Error: {e}")
        return None
    finally:
        sock.close()

def register():
    """Perform the SIP registration process."""
    initial_cseq = 1
    response = send_register(initial_cseq)
    if response and "401 Unauthorized" in response:
        response = handle_401(response, initial_cseq + 1)
        if response and "200 OK" in response:
            print("Registration successful.")
        else:
            print("Sipgate Registration Failed after authentication.")
    elif response and "200 OK" in response:
        print("Registration successful.")
    else:
        print("Sipgate Registration Failed.")

def main_loop():
    while True:
        try:
            register()
            print("Registration process completed. Will attempt again in 5 minutes.\n")
            time.sleep(300)  # Sleep for 5 minutes
        except socket.error as e:
            print(f"Sipgate Registration Error: {e}")
            print("Retrying in 10 seconds...\n")
            time.sleep(10)
        except Exception as e:
            print(f"Unexpected error: {e}")
            print("Retrying in 10 seconds...\n")
            time.sleep(10)

if __name__ == "__main__":
    main_loop()
