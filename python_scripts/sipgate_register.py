import socket
import hashlib
import os
import uuid  # Import uuid for generating unique Call-IDs
from dotenv import load_dotenv
import random
import click
import time

# Determine local IP address automatically
def get_local_ip():
    # Connect to an external server to determine the local IP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))  # Google's public DNS server
            return s.getsockname()[0]
        except Exception as e:
            print(f"Error obtaining local IP: {e}")
            return "127.0.0.1"

def generate_branch():
    """Generate a unique branch parameter for the Via header."""
    return f"z9hG4bK{random.randint(100000, 999999)}"

def send_register(sock, sip_server, sip_port, local_ip, local_port, cseq, call_id, sip_id):
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

def handle_401(response, sock, sip_server, sip_port, local_ip, local_port, cseq, call_id, sip_id, sip_password):
    """Handle 401 Unauthorized response and send authenticated REGISTER."""
    print("Handling 401 Unauthorized response")
    lines = response.split("\r\n")
    realm = nonce = None
    for line in lines:
        if line.startswith("WWW-Authenticate:"):
            parts = line.split('"')
            if len(parts) >= 4:
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

@click.command()
@click.option('--port', default=5060, help='Local port for the SIP client')
def main(port):
    load_dotenv()

    # Retrieve SIP credentials from environment variables
    sip_id = os.getenv("SIP_ID")
    sip_password = os.getenv("SIP_PASSWORD")
    sip_domain = os.getenv("SIP_DOMAIN")

    if not all([sip_id, sip_password, sip_domain]):
        print("Missing SIP credentials in environment variables.")
        return

    # SIP server details
    sip_server = sip_domain
    sip_port = 5060  # Assuming the SIP server listens on port 5060

    # Generate a unique Call-ID for this registration
    call_id = str(uuid.uuid4())
    print(f"Using Call-ID: {call_id}")

    # Initialize CSeq
    cseq = 1

    # Determine local IP address
    local_ip = get_local_ip()

    while True:
        try:
            # Create a UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((local_ip, port))
            sock.settimeout(10)  # Set timeout for socket operations
            print(f"Socket bound to {local_ip}:{port}")
        except OSError:
            print(f"Port {port} is in use. Retrying in 10 seconds...")
            time.sleep(10)
            continue
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 10 seconds...")
            time.sleep(10)
            continue

        try:
            # Send REGISTER message
            send_register(sock, sip_server, sip_port, local_ip, port, cseq, call_id, sip_id)
            cseq += 1  # Increment CSeq after sending REGISTER

            # Receive the response
            try:
                response, _ = sock.recvfrom(4096)
                response_text = response.decode()
                print("Received response:")
                print(response_text)

                # Handle 401 Unauthorized response
                if "401 Unauthorized" in response_text:
                    handle_401(response_text, sock, sip_server, sip_port, local_ip, port, cseq, call_id, sip_id, sip_password)
                    cseq += 1  # Increment CSeq after sending AUTH REGISTER

                    # Receive the response to the authenticated REGISTER
                    try:
                        response, _ = sock.recvfrom(4096)
                        response_text = response.decode()
                        print("Received response:")
                        print(response_text)
                    except socket.timeout:
                        print("No response to authenticated REGISTER received.")
            except socket.timeout:
                print("No response received for REGISTER.")
            except Exception as e:
                print(f"An error occurred while receiving response: {e}")
        finally:
            sock.close()
            print(f"Socket on port {port} closed.")

        print("Registration successful. Next registration in 5 minutes.")
        time.sleep(300)  # Wait for 5 minutes before re-registering

if __name__ == '__main__':
    main()
