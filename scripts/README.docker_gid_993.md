# Docker GID 993 Enforcement

## Background

The docker-compose.dev.yml configuration uses `GID=${GID:-993}` to ensure containers run with the docker group GID. This must match the actual docker group GID on the host systems.

## Affected Systems

- forest1
- nuc1.local
- nuc2.local
- nuc3.local

## Usage

### Check all systems (read-only)
```bash
./scripts/ensure_docker_gid_993.sh check
```

### Fix systems that need adjustment
```bash
./scripts/ensure_docker_gid_993.sh fix
```

## What the fix does

1. Stops docker service (containers will stop)
2. Changes docker group GID to 993 using `groupmod`
3. Restarts docker service
4. Verifies the change

## Manual verification

On each system, check the docker GID:
```bash
getent group docker | cut -d: -f3
```

Should return: `993`

## Manual fix (if needed)

On a system that needs fixing:
```bash
# Stop docker
sudo systemctl stop docker.socket docker.service

# Change GID
sudo groupmod -g 993 docker

# Start docker
sudo systemctl start docker.service

# Verify
getent group docker
```

## Why GID 993?

The GID 993 ensures:
- Consistent permissions across dev/prod environments
- Bind-mounted volumes work correctly with docker socket access
- Non-root container users can interact with docker when needed
- Matches the GID specified in docker-compose.dev.yml

## After changing GID

You may need to:
1. Re-add users to docker group: `sudo usermod -aG docker $USER`
2. Log out and back in for group changes to take effect
3. Restart containers: `wctl restart`
4. Verify with: `id -nG | grep docker`
