#!/usr/bin/env bash

set -e

# -----------------------------------------------------------------------------
# Replace env variables in the service_conf.yaml file
# -----------------------------------------------------------------------------
CONF_DIR="/ragflow/conf"
TEMPLATE_FILE="${CONF_DIR}/service_conf.yaml.template"
CONF_FILE="${CONF_DIR}/service_conf.yaml"

rm -f "${CONF_FILE}"
while IFS= read -r line || [[ -n "$line" ]]; do
    eval "echo \"$line\"" >> "${CONF_FILE}"
done < "${TEMPLATE_FILE}"

export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu/"
PY=python3

# -----------------------------------------------------------------------------
# Start nginx and the FastAPI server
# -----------------------------------------------------------------------------
echo "Starting nginx..."
/usr/sbin/nginx

echo "Starting FastAPI server..."
"$PY" api/fastapi_server.py 