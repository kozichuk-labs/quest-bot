import subprocess
import re
import time

print("Starting tunnel...")
process = subprocess.Popen(
    ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-R", "80:localhost:8080", "nokey@localhost.run"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

url = None
start_time = time.time()

while time.time() - start_time < 10:
    line = process.stdout.readline()
    if line:
        print("DEBUG:", line.strip())
        match = re.search(r'(https://[a-zA-Z0-9.-]+\.lhr\.life)', line)
        if match:
            url = match.group(1)
            break

if url:
    print(f"FOUND URL: {url}")
else:
    print("URL not found in 10 seconds.")
    process.terminate()
