import socket
import hashlib
import os
import uuid  # Import uuid for generating unique Call-IDs
from dotenv import load_dotenv
import random
import click
import time
import re
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine local IP address automatically
def get_local_ip():
    # Connect to an external server to determine the local IP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))  # Google's public DNS server
            return s.getsockname()[0]
        except Exception as e:
            logging.error(f"Error obtaining local IP: {e}")
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
    logging.info(f"Sending REGISTER with CSeq: {cseq}, Branch: {branch}")
    sock.sendto(sip_message.encode(), (sip_server, sip_port))

def handle_401(response, sock, sip_server, sip_port, local_ip, local_port, cseq, call_id, sip_id, sip_password):
    """Handle 401 Unauthorized response and send authenticated REGISTER."""
    logging.info("Handling 401 Unauthorized response")
    lines = response.split("\r\n")
    realm = nonce = None
    for line in lines:
        if line.startswith("WWW-Authenticate:"):
            # Extract realm and nonce using regex
            realm_match = re.search(r'realm="([^"]+)"', line)
            nonce_match = re.search(r'nonce="([^"]+)"', line)
            if realm_match and nonce_match:
                realm = realm_match.group(1)
                nonce = nonce_match.group(1)
                logging.info(f"Extracted realm: {realm}, nonce: {nonce}")
                break

    if realm and nonce:
        # Compute HA1, HA2, and response
        ha1 = hashlib.md5(f"{sip_id}:{realm}:{sip_password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"REGISTER:sip:{sip_server}".encode()).hexdigest()
        response_digest = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        logging.info(f"Computed HA1: {ha1}, HA2: {ha2}, response: {response_digest}")

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
        logging.info(f"Sending authenticated REGISTER with CSeq: {cseq}, Branch: {branch}")
        sock.sendto(auth_message.encode(), (sip_server, sip_port))
    else:
        logging.error("Failed to parse WWW-Authenticate header.")

def send_response(sock, response_message, address):
    """Send a SIP response message."""
    logging.debug(f"Sending response to {address}:\n{response_message}")
    sock.sendto(response_message.encode(), address)

def open_doors():
    """Dummy function to simulate opening doors."""
    logging.info("Door is being opened...")

def handle_invite(sock, invite_message, address, sip_id, local_ip, local_port, guest_list):
    """Handle an incoming INVITE request by sending a 180 Ringing response,
    check if caller is on guest list, and if yes, open doors."""
    logging.info(f"Handling INVITE from {address}")

    # Extract necessary headers from the INVITE message
    call_id_match = re.search(r'Call-ID:\s*(\S+)', invite_message, re.IGNORECASE)
    if not call_id_match:
        logging.error("Failed to extract Call-ID from INVITE.")
        return
    call_id = call_id_match.group(1)

    cseq_match = re.search(r'CSeq:\s*(\d+)\s+INVITE', invite_message, re.IGNORECASE)
    if not cseq_match:
        logging.error("Failed to extract CSeq from INVITE.")
        return
    cseq = cseq_match.group(1)

    # Extract all Via headers
    via_headers = re.findall(r'(Via: SIP/2.0/UDP .*?;branch=\S+)', invite_message, re.IGNORECASE)
    if not via_headers:
        logging.error("Failed to extract Via headers from INVITE.")
        return

    # Extract all Record-Route headers
    record_route_headers = re.findall(r'(Record-Route: <sip:.*?>)', invite_message, re.IGNORECASE)

    # Extract the From header
    from_match = re.search(r'From: .*<sip:(\d+)@[^>]+>', invite_message, re.IGNORECASE)
    if not from_match:
        logging.error("Failed to extract From header from INVITE.")
        return
    caller_number = from_match.group(1)
    logging.info(f"Caller Number: {caller_number}")

    # Check if caller is in the guest list
    if caller_number in guest_list:
        logging.info(f"Caller {caller_number} is on the guest list. Opening doors.")
        # Start a new thread to open doors
        door_thread = threading.Thread(target=open_doors, daemon=True)
        door_thread.start()
    else:
        logging.info(f"Caller {caller_number} is not on the guest list.")

    # Extract the From header (full header)
    from_header = re.search(r'(From: .*?;tag=\S+)', invite_message, re.IGNORECASE).group(1)

    # Extract the To header without tag
    to_match = re.search(r'(To: <sip:.*?>)', invite_message, re.IGNORECASE)
    if not to_match:
        logging.error("Failed to extract To header from INVITE.")
        return
    to_header = to_match.group(1)

    # Generate a unique tag for the To header
    to_tag = uuid.uuid4().hex

    # Construct the 180 Ringing response
    ringing_response = (
        f"SIP/2.0 180 Ringing\r\n"
        + "\r\n".join(via_headers) + "\r\n"
        + "\r\n".join(record_route_headers) + "\r\n"
        + f"{to_header};tag={to_tag}\r\n"
        + f"{from_header}\r\n"
        + f"Call-ID: {call_id}\r\n"
        + f"CSeq: {cseq} INVITE\r\n"
        + f"Contact: <sip:{sip_id}@{local_ip}:{local_port}>\r\n"
        + f"Content-Length: 0\r\n\r\n"
    )
    send_response(sock, ringing_response, address)
    logging.info(f"Sent 180 Ringing for Call-ID: {call_id}")

    # Wait for 1 second before hanging up
    time.sleep(1)

    # Construct the 487 Request Terminated response
    terminated_response = (
        f"SIP/2.0 487 Request Terminated\r\n"
        + "\r\n".join(via_headers) + "\r\n"
        + "\r\n".join(record_route_headers) + "\r\n"
        + f"{to_header};tag={to_tag}\r\n"
        + f"{from_header}\r\n"
        + f"Call-ID: {call_id}\r\n"
        + f"CSeq: {cseq} INVITE\r\n"
        + f"Contact: <sip:{sip_id}@{local_ip}:{local_port}>\r\n"
        + f"Content-Length: 0\r\n\r\n"
    )
    send_response(sock, terminated_response, address)
    logging.info(f"Sent 487 Request Terminated for Call-ID: {call_id}")

def registration_loop(sock, sip_server, sip_port, local_ip, local_port, call_id, sip_id, sip_password):
    """Continuously send REGISTER messages every 5 minutes."""
    cseq = 1
    while True:
        try:
            send_register(sock, sip_server, sip_port, local_ip, local_port, cseq, call_id, sip_id)
            cseq += 1  # Increment CSeq after sending REGISTER

            # Receive the response
            try:
                response, _ = sock.recvfrom(4096)
                response_text = response.decode()
                logging.info("Received response:")
                logging.info(response_text)

                # Handle 401 Unauthorized response
                if "401 Unauthorized" in response_text:
                    handle_401(response_text, sock, sip_server, sip_port, local_ip, local_port, cseq, call_id, sip_id, sip_password)
                    cseq += 1  # Increment CSeq after sending AUTH REGISTER

                    # Receive the response to the authenticated REGISTER
                    try:
                        response, _ = sock.recvfrom(4096)
                        response_text = response.decode()
                        logging.info("Received response:")
                        logging.info(response_text)
                    except socket.timeout:
                        logging.warning("No response to authenticated REGISTER received.")
            except socket.timeout:
                logging.warning("No response received for REGISTER.")
            except Exception as e:
                logging.error(f"An error occurred while receiving response: {e}")
        except Exception as e:
            logging.error(f"An error occurred during registration: {e}")

        logging.info("Registration successful. Next registration in 5 minutes.")
        time.sleep(300)  # Wait for 5 minutes before re-registering

def listening_loop(sock, sip_id, local_ip, local_port, guest_list):
    """Listen for incoming SIP messages and handle INVITE requests."""
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            try:
                message = data.decode()
            except UnicodeDecodeError:
                logging.error(f"Failed to decode message from {addr}.")
                continue
            logging.debug(f"Received message from {addr}:\n{message}")

            if message.startswith("INVITE"):
                handle_invite(sock, message, addr, sip_id, local_ip, local_port, guest_list)
            else:
                logging.info(f"Ignoring unsupported SIP method from {addr}.")
        except Exception as e:
            logging.error(f"An error occurred while listening for messages: {e}")

@click.command()
@click.option('--port', default=5060, help='Local port for the SIP client', show_default=True)
def main(port):
    load_dotenv()

    # Retrieve SIP credentials from environment variables
    sip_id = os.getenv("SIP_ID")
    sip_password = os.getenv("SIP_PASSWORD")
    sip_domain = os.getenv("SIP_DOMAIN")
    test_guest = os.getenv("TEST_GUEST", "")

    if not all([sip_id, sip_password, sip_domain]):
        logging.error("Missing SIP credentials in environment variables.")
        return

    # Process guest list
    guest_list = [number.strip() for number in test_guest.split(",") if number.strip()]
    logging.info(f"Guest List: {guest_list}")

    # SIP server details
    sip_server = sip_domain
    sip_port = 5060  # Assuming the SIP server listens on port 5060

    # Generate a unique Call-ID for this registration
    call_id = str(uuid.uuid4())
    logging.info(f"Using Call-ID: {call_id}")

    # Determine local IP address
    local_ip = get_local_ip()

    try:
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((local_ip, port))
        sock.settimeout(10)  # Set timeout for socket operations
        logging.info(f"Socket bound to {local_ip}:{port}")
    except OSError:
        logging.error(f"Port {port} is in use. Please choose a different port.")
        return
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return

    # Start the registration loop in a separate thread
    reg_thread = threading.Thread(target=registration_loop, args=(sock, sip_server, sip_port, local_ip, port, call_id, sip_id, sip_password), daemon=True)
    reg_thread.start()
    logging.info("Started registration thread.")

    # Start the listening loop in the main thread
    try:
        listening_loop(sock, sip_id, local_ip, port, guest_list)
    except KeyboardInterrupt:
        logging.info("Shutting down SIP client.")
    finally:
        sock.close()
        logging.info(f"Socket on port {port} closed.")

if __name__ == '__main__':
    main()
