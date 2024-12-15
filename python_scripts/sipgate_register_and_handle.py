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
import json  # Import json for handling guest list
from datetime import datetime  # Import datetime for time comparisons
import RPi.GPIO as GPIO  # Import RPi.GPIO for GPIO control

# GPIO pin definitions
GPIO_PIN_20 = 20
GPIO_PIN_21 = 21

# Set the GPIO mode
GPIO.setmode(GPIO.BCM)

# Set up the GPIO pins as outputs with an initial low state
GPIO.setup(GPIO_PIN_20, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(GPIO_PIN_21, GPIO.OUT, initial=GPIO.LOW)

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
    """Open both doors, wait, and then close them accordingly."""
    try:
        logging.info("Opening both doors...")
        # Open both doors
        GPIO.output(GPIO_PIN_20, GPIO.HIGH)  # Open apartment door
        GPIO.output(GPIO_PIN_21, GPIO.HIGH)  # Open house door
        logging.info("Both doors opened.")
        
        time.sleep(1)  # Wait for 1 second
        
        # Close house door
        logging.info("Closing house door...")
        GPIO.output(GPIO_PIN_21, GPIO.LOW)
        logging.info("House door closed.")
        
        time.sleep(15)  # Wait for 15 seconds
        
        # Close apartment door
        logging.info("Closing apartment door...")
        GPIO.output(GPIO_PIN_20, GPIO.LOW)
        logging.info("Apartment door closed.")
        
    except Exception as e:
        logging.error(f"Error in open_doors: {e}")
    finally:
        # Optional: Cleanup can be handled elsewhere if needed
        pass

def handle_invite(sock, invite_message, address, sip_id, local_ip, local_port, guests):
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

    # Check if caller is in the guest list and within allowed time
    is_guest_allowed = False
    for guest_name, guest_info in guests.items():
        guest_phone = re.sub(r'\D', '', guest_info.get("phone", ""))  # Remove non-digit characters
        if caller_number == guest_phone:
            allowed_from_str = guest_info.get("allowedFrom")
            allowed_until_str = guest_info.get("allowedUntil")
            if allowed_from_str and allowed_until_str:
                try:
                    allowed_from = datetime.fromisoformat(allowed_from_str)
                    allowed_until = datetime.fromisoformat(allowed_until_str)
                    current_time = datetime.now()
                    if allowed_from <= current_time <= allowed_until:
                        logging.info(f"Caller {caller_number} ({guest_name}) is allowed to enter.")
                        is_guest_allowed = True
                    else:
                        logging.info(f"Caller {caller_number} ({guest_name}) is not within the allowed time.")
                except ValueError as ve:
                    logging.error(f"Invalid datetime format for guest {guest_name}: {ve}")
            break  # Phone number matched, no need to continue

    if is_guest_allowed:
        logging.info(f"Caller {caller_number} is on the guest list and within the allowed time. Opening doors.")
        # Start a new thread to open doors
        door_thread = threading.Thread(target=open_doors, daemon=True)
        door_thread.start()
    else:
        logging.info(f"Caller {caller_number} is not on the guest list or not within the allowed time.")

    # Extract the From header (full header)
    from_header = re.search(r'(From: .*?;tag=\S+)', invite_message, re.IGNORECASE).group(1) if re.search(r'(From: .*?;tag=\S+)', invite_message, re.IGNORECASE) else f"From: <sip:{caller_number}@unknown>;tag=unknown"

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
    # time.sleep(1)

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

def listening_loop(sock, sip_id, local_ip, local_port, guests):
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
                handle_invite(sock, message, addr, sip_id, local_ip, local_port, guests)
            else:
                logging.info(f"Ignoring unsupported SIP method from {addr}.")
        except Exception as e:
            logging.error(f"An error occurred while listening for messages: {e}")

@click.command()
@click.option('--port', default=5060, help='Local port for the SIP client', show_default=True)
@click.option('--verbose', is_flag=True, help='Enable verbose (DEBUG) logging')
def main(port, verbose):
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    load_dotenv()

    # Retrieve SIP credentials from environment variables
    sip_id = os.getenv("SIP_ID")
    sip_password = os.getenv("SIP_PASSWORD")
    sip_domain = os.getenv("SIP_DOMAIN")

    if not all([sip_id, sip_password, sip_domain]):
        logging.error("Missing SIP credentials in environment variables.")
        return

    # Load guest list from guests.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    guests_path = os.path.join(script_dir, "guests.json")
    try:
        with open(guests_path, "r") as f:
            guests = json.load(f)
        logging.info(f"Loaded guests from {guests_path}")
    except FileNotFoundError:
        logging.error(f"guests.json not found in {script_dir}.")
        return
    except json.JSONDecodeError as jde:
        logging.error(f"Error decoding guests.json: {jde}")
        return
    except Exception as e:
        logging.error(f"Unexpected error loading guests.json: {e}")
        return

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
        listening_loop(sock, sip_id, local_ip, port, guests)
    except KeyboardInterrupt:
        logging.info("Shutting down SIP client.")
    finally:
        sock.close()
        logging.info(f"Socket on port {port} closed.")
        GPIO.cleanup()
        logging.info("GPIO cleanup completed.")

if __name__ == '__main__':
    main()
