import socket
import os
from dotenv import load_dotenv
import re
import logging
import uuid
import time  # Imported to allow delays

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
file_handler = logging.FileHandler('sip_messages.log')
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Load environment variables from .env file
load_dotenv()

# Retrieve SIP credentials from environment variables
sip_id = os.getenv("SIP_ID")
sip_domain = os.getenv("SIP_DOMAIN")

# Determine local IP address automatically
def get_local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))  # Google's public DNS server
        return s.getsockname()[0]

local_ip = get_local_ip()
local_port = 5061  # Port for your SIP client

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((local_ip, local_port))

def send_response(response_message, address):
    """Send a SIP response message."""
    logging.debug(f"Sending response to {address}:\n{response_message}")
    sock.sendto(response_message.encode(), address)

def handle_invite(invite_message, address):
    """Handle an incoming INVITE request by sending a 180 Ringing response,
    wait for 1 second, then send a 487 Request Terminated response."""
    logging.debug(f"Handling INVITE from {address}")

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
    from_match = re.search(r'(From: .*?;tag=\S+)', invite_message, re.IGNORECASE)
    if not from_match:
        logging.error("Failed to extract From header from INVITE.")
        return
    from_header = from_match.group(1)

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
    send_response(ringing_response, address)
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
    send_response(terminated_response, address)
    logging.info(f"Sent 487 Request Terminated for Call-ID: {call_id}")

# Main loop to listen for incoming messages
while True:
    data, addr = sock.recvfrom(4096)
    try:
        message = data.decode()
    except UnicodeDecodeError:
        logging.error(f"Failed to decode message from {addr}.")
        continue
    logging.debug(f"Received message from {addr}:\n{message}")

    if message.startswith("INVITE"):
        handle_invite(message, addr)
    else:
        logging.info(f"Ignoring unsupported SIP method from {addr}.")
