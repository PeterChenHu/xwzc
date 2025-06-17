#!/bin/bash
if [ "$(id -u)" != 0 ]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

read -p "Enter the service name: " SERVICE_NAME
read -p "Enter the path to Python script: " SCRIPT_PATH`
read -p "Enter the user to run the service: " SERVICE_USER

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Script file does not exist: $SCRIPT_PATH" 1>&2
    exit 1
fi
if [ -z "$SERVICE_NAME" ] || [ -z "$SCRIPT_PATH" ] || [ -z "$SERVICE_USER" ]; then
    echo "All fields are required." 1>&2
    exit 1
fi
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
echo "Creating service file at $SERVICE_FILE"
cat > "$SERVICE_FILE" << EOF

[Unit]
Description=$SERVICE_NAME Service
After=network.target
[Service]
User=$SERVICE_USER
ExecStart=/usr/bin/python3 $SCRIPT_PATH
Restart=always
[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize the new service
systemctl daemon-reload

systemctl enable "$SERVICE_NAME".service
systemctl start "$SERVICE_NAME".service
echo "Service $SERVICE_NAME has been created and started."
systemctl status "$SERVICE_NAME".service

# you can check real time logs with:
echo "You can check the logs with:"
echo "journalctl -u $SERVICE_NAME.service -f"