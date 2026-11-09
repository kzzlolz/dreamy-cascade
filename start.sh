
#!/bin/bash

set -e
cd /home/container

echo "================================"
echo "   DREAMY CASCADE STARTUP"
echo "================================"

# Install Python dependencies
echo "[1/3] Installing requirements..."
/usr/local/bin/python -m pip install -r requirements.txt

# Download Cloudflare Tunnel if missing
if [ ! -f cloudflared ]; then
    echo "[2/3] Downloading Cloudflare Tunnel..."
    curl -fsSL \
      https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
      -o cloudflared
    chmod +x cloudflared
else
    echo "[2/3] Cloudflare Tunnel already downloaded."
fi

# Start the temporary Quick Tunnel
echo "[3/3] Starting Cloudflare Quick Tunnel..."

./cloudflared tunnel \
    --url http://127.0.0.1:8728 \
    --no-autoupdate \
    > cloudflared.log 2>&1 &

# Print the generated URL when available
(
    for i in $(seq 1 60); do
        URL=$(grep -Eo 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' cloudflared.log | head -n 1 || true)

        if [ -n "$URL" ]; then
            echo ""
            echo "================================"
            echo "YOUR DREAMY CASCADE URL:"
            echo "$URL"
            echo "================================"
            exit 0
        fi

        sleep 1
    done

    echo "Tunnel URL not detected yet. Check cloudflared.log."
) &

# Start the Discord bot and Flask server
exec /usr/local/bin/python /home/container/bot2.py

