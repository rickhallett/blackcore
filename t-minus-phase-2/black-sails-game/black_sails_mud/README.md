# Black Sails MUD - Server & Connection Guide

A turn-based MUD-style pirate adventure game with multiple deployment options.

## Table of Contents
- [Quick Start](#quick-start)
- [Single Player Mode](#single-player-mode)
- [Local Multiplayer (Hot Seat)](#local-multiplayer-hot-seat)
- [Network Multiplayer](#network-multiplayer)
- [Deployment Options](#deployment-options)
- [Advanced Configurations](#advanced-configurations)

## Quick Start

```bash
# Install dependencies
pip install rich

# Run single player
python run_mud.py
```

## Single Player Mode

The simplest way to play - no networking required.

```bash
# Standard launch
python run_mud.py

# Or using the module directly
python -m black_sails_mud.game

# Run the demo (shows all UI components)
python demo_mud.py
```

## Local Multiplayer (Hot Seat)

For two players sharing the same terminal:

```bash
# Launch hot-seat mode (players take turns at same terminal)
python run_mud.py local --players 2
```

## Network Multiplayer

### Option 1: Direct TCP Connection (LAN)

**Host (Player 1):**
```bash
# Start the server on default port 9999
python run_mud.py server

# Or specify custom port
python run_mud.py server --port 7777
```

**Client (Player 2):**
```bash
# Connect to host
python run_mud.py connect <host-ip>:9999

# Examples:
python run_mud.py connect 192.168.1.100:9999  # LAN IP
python run_mud.py connect localhost:9999       # Same machine
```

### Option 2: SSH-Based MUD Server

Set up the game as a proper MUD server that players can SSH into:

**Server Setup:**
```bash
# 1. Create a dedicated user for the MUD
sudo adduser blacksails-mud

# 2. Install the game in the user's home
sudo -u blacksails-mud bash
cd ~
git clone <your-repo>
cd black-sails-game
pip install rich

# 3. Set as shell for auto-launch
echo "python ~/black-sails-game/run_mud.py" >> ~/.bashrc

# 4. Configure SSH (in /etc/ssh/sshd_config)
# Add these lines for the MUD user:
Match User blacksails-mud
    ForceCommand python /home/blacksails-mud/black-sails-game/run_mud.py
    PasswordAuthentication yes
```

**Players Connect:**
```bash
# Players SSH directly into the game
ssh blacksails-mud@your-server.com
```

### Option 3: Telnet Server

Run as a traditional MUD with telnet access:

**Server Setup:**
```bash
# Create a telnet wrapper script
cat > telnet_server.py << 'EOF'
#!/usr/bin/env python3
import socket
import threading
import subprocess

def handle_client(client_socket, addr):
    print(f"New connection from {addr}")
    # Launch game instance for this connection
    proc = subprocess.Popen(
        ['python', 'run_mud.py'],
        stdin=client_socket.makefile('rb'),
        stdout=client_socket.makefile('wb'),
        stderr=subprocess.STDOUT
    )
    proc.wait()
    client_socket.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 2323))  # Telnet port
server.listen(5)
print("MUD Server listening on port 2323...")

while True:
    client, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(client, addr))
    thread.start()
EOF

python telnet_server.py
```

**Players Connect:**
```bash
telnet your-server.com 2323
```

### Option 4: Ngrok Tunnel (Internet Play)

Expose your local game to the internet:

**Host Setup:**
```bash
# 1. Start local server
python run_mud.py server --port 9999

# 2. In another terminal, create ngrok tunnel
ngrok tcp 9999

# 3. Share the ngrok URL with players
# Example: tcp://2.tcp.ngrok.io:12345
```

**Remote Players:**
```bash
# Connect using ngrok URL
python run_mud.py connect 2.tcp.ngrok.io:12345
```

### Option 5: Web Terminal (Browser-Based)

Serve the game through a web browser using terminal emulation:

**Create Web Server:**
```bash
# Install additional dependencies
pip install flask flask-socketio pyxtermjs

# Create web_server.py
cat > web_server.py << 'EOF'
from flask import Flask, render_template
from flask_socketio import SocketIO
import subprocess
import pty
import os
import select
import termios
import struct
import fcntl

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Black Sails MUD</title>
        <link rel="stylesheet" href="https://unpkg.com/xterm/css/xterm.css" />
        <script src="https://unpkg.com/xterm/lib/xterm.js"></script>
        <script src="https://unpkg.com/xterm-addon-fit/lib/xterm-addon-fit.js"></script>
        <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
        <style>
            body { 
                margin: 0; 
                padding: 20px; 
                background: #1e1e1e;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            #terminal {
                width: 80%;
                height: 80%;
            }
        </style>
    </head>
    <body>
        <div id="terminal"></div>
        <script>
            const term = new Terminal({
                cursorBlink: true,
                theme: {
                    background: '#1e1e1e',
                    foreground: '#d4d4d4'
                }
            });
            const fitAddon = new FitAddon.FitAddon();
            term.loadAddon(fitAddon);
            
            const socket = io();
            
            term.open(document.getElementById('terminal'));
            fitAddon.fit();
            
            term.onData(data => {
                socket.emit('input', data);
            });
            
            socket.on('output', data => {
                term.write(data);
            });
            
            socket.on('connect', () => {
                socket.emit('start_game');
            });
            
            window.addEventListener('resize', () => {
                fitAddon.fit();
            });
        </script>
    </body>
    </html>
    '''

@socketio.on('start_game')
def start_game():
    # Start the game process
    master, slave = pty.openpty()
    p = subprocess.Popen(
        ['python', 'run_mud.py'],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        preexec_fn=os.setsid
    )
    
    # Store process info in session
    session['pid'] = p.pid
    session['fd'] = master
    
    # Start output thread
    socketio.start_background_task(read_and_forward_output, master)

def read_and_forward_output(fd):
    while True:
        socketio.sleep(0.01)
        timeout_sec = 0
        (data_ready, _, _) = select.select([fd], [], [], timeout_sec)
        if data_ready:
            output = os.read(fd, 1024).decode()
            socketio.emit('output', output)

@socketio.on('input')
def handle_input(data):
    fd = session.get('fd')
    if fd:
        os.write(fd, data.encode())

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
EOF

# Run the web server
python web_server.py
```

**Players Access:**
```
Open browser to: http://your-server:5000
```

### Option 6: Docker Container

**Create Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements_mud.txt .
RUN pip install -r requirements_mud.txt

# Copy game files
COPY black_sails_mud/ ./black_sails_mud/
COPY run_mud.py .
COPY demo_mud.py .

# Expose game port
EXPOSE 9999

# Run the game server
CMD ["python", "run_mud.py", "server", "--port", "9999"]
```

**Build and Run:**
```bash
# Build container
docker build -t black-sails-mud .

# Run server
docker run -p 9999:9999 black-sails-mud

# Run interactive single player
docker run -it black-sails-mud python run_mud.py
```

### Option 7: SystemD Service (Linux)

**Create Service File:**
```bash
sudo cat > /etc/systemd/system/black-sails-mud.service << EOF
[Unit]
Description=Black Sails MUD Server
After=network.target

[Service]
Type=simple
User=blacksails-mud
WorkingDirectory=/home/blacksails-mud/black-sails-game
ExecStart=/usr/bin/python3 /home/blacksails-mud/black-sails-game/run_mud.py server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable black-sails-mud
sudo systemctl start black-sails-mud
```

## Advanced Configurations

### Multiple Game Instances

Run multiple game worlds on different ports:

```bash
# World 1: The Caribbean
python run_mud.py server --port 9001 --world caribbean

# World 2: Tortuga
python run_mud.py server --port 9002 --world tortuga

# World 3: Port Royal  
python run_mud.py server --port 9003 --world port-royal
```

### Load Balancing Multiple Servers

Using nginx for TCP load balancing:

```nginx
stream {
    upstream mud_servers {
        server localhost:9001;
        server localhost:9002;
        server localhost:9003;
    }
    
    server {
        listen 9999;
        proxy_pass mud_servers;
    }
}
```

### Monitoring & Logging

```bash
# Run with logging
python run_mud.py server 2>&1 | tee -a mud-server.log

# Monitor connections
watch 'netstat -an | grep :9999'

# Monitor game process
htop -p $(pgrep -f "run_mud.py server")
```

### Security Considerations

1. **Firewall Rules:**
```bash
# Allow game port
sudo ufw allow 9999/tcp

# Limit connection rate
sudo iptables -A INPUT -p tcp --dport 9999 -m limit --limit 5/min -j ACCEPT
```

2. **SSL/TLS for Web Version:**
```bash
# Use Let's Encrypt for HTTPS
sudo certbot --nginx -d your-mud-server.com
```

3. **Resource Limits:**
```bash
# Limit memory/CPU for game process
systemd-run --uid=blacksails-mud --gid=blacksails-mud \
    --property=MemoryMax=500M \
    --property=CPUQuota=50% \
    python run_mud.py server
```

## Troubleshooting

### Common Issues

1. **"Connection Refused"**
   - Check firewall settings
   - Verify server is running: `ps aux | grep run_mud.py`
   - Check correct IP/port

2. **"Rich not found"**
   - Install dependencies: `pip install rich`

3. **Performance Issues**
   - Limit concurrent connections
   - Use connection pooling
   - Enable game caching

### Debug Mode

```bash
# Run with debug output
PYTHONUNBUFFERED=1 python run_mud.py server --debug

# Test connection
nc -zv localhost 9999
```

## Client Configuration

### Custom Client Script

```bash
#!/bin/bash
# save as: blacksails-connect.sh

echo "Black Sails MUD Client"
echo "====================="
echo "1. Local Game"
echo "2. Connect to Server"
echo "3. List Servers"

read -p "Choice: " choice

case $choice in
    1) python run_mud.py ;;
    2) read -p "Server address: " server
       python run_mud.py connect $server ;;
    3) echo "Available servers:"
       echo "- official.blacksails-mud.com:9999"
       echo "- caribbean.blacksails-mud.com:9001"
       ;;
esac
```

## Performance Tuning

### For High-Traffic Servers

1. **Use PyPy for better performance:**
```bash
pypy3 run_mud.py server
```

2. **Enable connection pooling:**
```python
# In server config
MAX_PLAYERS = 100
CONNECTION_TIMEOUT = 300  # 5 minutes
```

3. **Database optimization (when implemented):**
```bash
# Use Redis for session storage
export REDIS_URL=redis://localhost:6379
```

## Contributing

To add new server modes or connection types:

1. Fork the repository
2. Add your server implementation to `black_sails_mud/server/`
3. Update `run_mud.py` with new connection options
4. Submit a pull request

## Support

- **Discord**: [Join our server](#)
- **Forums**: [community.blacksails-mud.com](#)
- **Wiki**: [wiki.blacksails-mud.com](#)

Happy pirating! 🏴‍☠️