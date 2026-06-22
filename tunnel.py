import asyncio
import re
import logging
from config import WEBAPP_URL as CONFIG_WEBAPP_URL

WEBAPP_URL = CONFIG_WEBAPP_URL or "https://127.0.0.1:6767"
_tunnel_process = None

async def start_tunnel():
    global WEBAPP_URL, _tunnel_process
    
    if CONFIG_WEBAPP_URL:
        logging.info(f"Using provided WEBAPP_URL: {CONFIG_WEBAPP_URL}")
        return
        
    logging.info("Starting HTTPS tunnel via localhost.run...")
    try:
        _tunnel_process = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=accept-new", "-R", "80:localhost:6767", "nokey@localhost.run",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        # Give it a few seconds to find the URL
        async def wait_for_url():
            global WEBAPP_URL
            while True:
                line = await _tunnel_process.stdout.readline()
                if not line:
                    break
                line_str = line.decode('utf-8').strip()
                match = re.search(r'(https://[a-zA-Z0-9.-]+\.lhr\.life)', line_str)
                if match:
                    WEBAPP_URL = match.group(1)
                    logging.info(f"✅ SSH Tunnel established: {WEBAPP_URL}")
                    return True
            return False

        try:
            await asyncio.wait_for(wait_for_url(), timeout=10.0)
        except asyncio.TimeoutError:
            logging.error("Timeout waiting for SSH tunnel URL.")
    except Exception as e:
        logging.error(f"Failed to start tunnel: {e}")

def get_webapp_url():
    return WEBAPP_URL

async def stop_tunnel():
    if _tunnel_process:
        try:
            _tunnel_process.terminate()
        except:
            pass
