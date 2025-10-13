#!/bin/bash

# The absolute path to your project's root directory
PROJECT_DIR="/workdir/wepppy"

# Change to the project directory. Exit if the directory doesn't exist.
cd "$PROJECT_DIR" || exit

# Execute the docker compose command with your specific files,
# forwarding all arguments ($@) passed to this script.
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml "$@"
