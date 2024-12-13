import socket
import os
from dotenv import load_dotenv
import re
# import pyaudio
import wave

# Load environment variables from .env file
load_dotenv()

# Retrieve SIP credentials and guest list from environment variables
sip_id = os.getenv("SIP_ID")
sip_domain = os.getenv("SIP_DOMAIN")
guest_list = os.getenv("TEST_GUEST", "").split(",")

# Determine local IP address automatically
def get_local_ip():
    # Connect to an external server to determine the local IP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))  # Google's public DNS server
        return s.getsockname()[0]

local_ip = get_local_ip() # has to be
local_port = 5060  # Port for your SIP client

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((local_ip, local_port))

def send_response(response_message, address):
    """Send a SIP response message."""
    sock.sendto(response_message.encode(), address)

def handle_invite(invite_message, address):
    """Handle an incoming INVITE request."""
    # Extract phone number from the INVITE message
    match = re.search(r'From:.*<sip:(.*?)@', invite_message)
    if match:
        phone_number = match.group(1)
        print(f"Incoming call from: {phone_number}")

        if phone_number in guest_list:
            print("Phone number is in the guest list. Accepting call.")

            # Send 100 Trying
            trying_response = (
                f"SIP/2.0 100 Trying\r\n"
                f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK776asdhds\r\n"
                f"To: <sip:{sip_id}@{sip_domain}>\r\n"
                f"From: <sip:{phone_number}@{sip_domain}>\r\n"
                f"Call-ID: a84b4c76e66710\r\n"
                f"CSeq: 103 INVITE\r\n"
                f"Content-Length: 0\r\n\r\n"
            )
            send_response(trying_response, address)

            # Send 180 Ringing
            ringing_response = (
                f"SIP/2.0 180 Ringing\r\n"
                f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK776asdhds\r\n"
                f"To: <sip:{sip_id}@{sip_domain}>\r\n"
                f"From: <sip:{phone_number}@{sip_domain}>\r\n"
                f"Call-ID: a84b4c76e66710\r\n"
                f"CSeq: 103 INVITE\r\n"
                f"Content-Length: 0\r\n\r\n"
            )
            send_response(ringing_response, address)

            # Send 200 OK
            ok_response = (
                f"SIP/2.0 200 OK\r\n"
                f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK776asdhds\r\n"
                f"To: <sip:{sip_id}@{sip_domain}>\r\n"
                f"From: <sip:{phone_number}@{sip_domain}>\r\n"
                f"Call-ID: a84b4c76e66710\r\n"
                f"CSeq: 103 INVITE\r\n"
                f"Contact: <sip:{sip_id}@{local_ip}:{local_port}>\r\n"
                f"Content-Length: 0\r\n\r\n"
            )
            send_response(ok_response, address)

            # Play audio file to the caller
            # play_audio_to_caller("welcome_message.wav", address)
        else:
            print("Phone number is not in the guest list. Ignoring call.")

def play_audio_to_caller(audio_file, address):
    """Stream audio file to the caller using RTP."""
    # Open the audio file
    wf = wave.open(audio_file, 'rb')

    # Create a PyAudio stream
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    # Read data from the audio file and send it over RTP
    data = wf.readframes(1024)
    while data:
        stream.write(data)
        data = wf.readframes(1024)

    # Close the stream and PyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()

def parse_sip_message(message):
    """Parse a SIP message into a dictionary."""
    lines = message.split("\r\n")
    headers = {}
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key] = value
    return headers

# Main loop to listen for incoming messages
while True:
    data, addr = sock.recvfrom(4096)
    message = data.decode()
    print("Received message:")
    print(message)

    if message.startswith("INVITE"):
        handle_invite(message, addr)
