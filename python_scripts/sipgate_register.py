import socket
import hashlib
import os
import uuid  # Import uuid for generating unique Call-IDs
from dotenv import load_dotenv
import random

# Load environment variables from .env file
load_dotenv()

# Retrieve SIP credentials from environment variables
sip_id = os.getenv("SIP_ID")
sip_password = os.getenv("SIP_PASSWORD")
sip_domain = os.getenv("SIP_DOMAIN")

# Determine local IP address automatically
def get_local_ip():
    # Connect to an external server to determine the local IP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))  # Google's public DNS server
        return s.getsockname()[0]

local_ip = get_local_ip()
local_port = 5061  # Port for your SIP client

# SIP server details
sip_server = sip_domain
sip_port = 5060

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((local_ip, local_port))

def generate_branch():
    """Generate a unique branch parameter for the Via header."""
    return f"z9hG4bK{random.randint(100000, 999999)}"

def send_register(cseq, call_id):
    """Send a SIP REGISTER message."""
    branch = generate_branch()
    sip_message = (
        f"REGISTER sip:{sip_server} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"To: <sip:{sip_id}@{sip_server}>\r\n"
        f"From: <sip:{sip_id}@{sip_server}>;tag=1928301774\r\n"
        f"Call-ID: {call_id}\r\n"  # Use unique Call-ID
        f"CSeq: {cseq} REGISTER\r\n"
        f"Contact: <sip:{sip_id}@{local_ip}:{local_port}>\r\n"
        f"Expires: 3600\r\n"
        f"Content-Length: 0\r\n\r\n"
    )
    print(f"Sending REGISTER with CSeq: {cseq}, Branch: {branch}")
    print(sip_message)
    sock.sendto(sip_message.encode(), (sip_server, sip_port))

def handle_401(response, cseq, call_id):
    """Handle 401 Unauthorized response and send authenticated REGISTER."""
    print("Handling 401 Unauthorized response")
    lines = response.split("\r\n")
    realm = nonce = None
    for line in lines:
        if line.startswith("WWW-Authenticate:"):
            parts = line.split('"')
            realm = parts[1]
            nonce = parts[3]
            print(f"Extracted realm: {realm}, nonce: {nonce}")
            break

    if realm and nonce:
        # Compute HA1, HA2, and response
        ha1 = hashlib.md5(f"{sip_id}:{realm}:{sip_password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"REGISTER:sip:{sip_server}".encode()).hexdigest()
        response_digest = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        print(f"Computed HA1: {ha1}, HA2: {ha2}, response: {response_digest}")

        # Send authenticated REGISTER
        branch = generate_branch()
        auth_message = (
            f"REGISTER sip:{sip_server} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
            f"Max-Forwards: 70\r\n"
            f"To: <sip:{sip_id}@{sip_server}>\r\n"
            f"From: <sip:{sip_id}@{sip_server}>;tag=1928301774\r\n"
            f"Call-ID: {call_id}\r\n"  # Use the same Call-ID
            f"CSeq: {cseq} REGISTER\r\n"
            f"Contact: <sip:{sip_id}@{local_ip}:{local_port}>\r\n"
            f"Authorization: Digest username=\"{sip_id}\", realm=\"{realm}\", nonce=\"{nonce}\", uri=\"sip:{sip_server}\", response=\"{response_digest}\"\r\n"
            f"Expires: 3600\r\n"
            f"Content-Length: 0\r\n\r\n"
        )
        print(f"Sending authenticated REGISTER with CSeq: {cseq}, Branch: {branch}")
        print(auth_message)
        sock.sendto(auth_message.encode(), (sip_server, sip_port))
    else:
        print("Failed to parse WWW-Authenticate header.")

# Generate a unique Call-ID for this registration
call_id = str(uuid.uuid4())

# Send initial REGISTER message
initial_cseq = 1  # Start with CSeq 1 for new Call-ID
send_register(initial_cseq, call_id)

# Receive the response
response, _ = sock.recvfrom(4096)
response_text = response.decode()
print("Received response:")
print(response_text)

# Handle 401 Unauthorized response
if "401 Unauthorized" in response_text:
    handle_401(response_text, initial_cseq + 1, call_id)
    # Receive the response to the authenticated REGISTER
    response, _ = sock.recvfrom(4096)
    response_text = response.decode()
    print("Received response:")
    print(response_text)

# Close the socket
sock.close()
