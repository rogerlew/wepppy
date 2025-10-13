## **wctl (weppcloud control)**

### **Overview**

wctl is a command-line wrapper script designed to simplify the management of the wepppy Docker Compose development environment.  
The primary purpose of this tool is to provide a global command that executes docker compose with the project-specific configuration files, regardless of the user's current working directory. It eliminates the need to repeatedly cd into the project folder (/workdir/wepppy) and type the full docker compose command with its environment and file flags.

### **How It Works**

The wctl script is a simple yet powerful Bash script that performs the following actions in sequence:

1. **Sets Project Directory:** It contains a hardcoded variable for the project's root directory: /workdir/wepppy.  
2. **Changes Directory:** It immediately changes its execution context to that project directory. This ensures that all relative paths within the docker-compose.dev.yml file are resolved correctly.  
3. **Executes Docker Compose:** It runs the docker compose command, explicitly pointing to the development environment file (docker/.env) and the development compose file (docker/docker-compose.dev.yml).  
4. **Forwards Arguments:** Any arguments or commands you pass to wctl (e.g., up \-d, down, logs) are appended to the end of the docker compose command using the $@ shell parameter.

This allows a command like wctl ps to be translated seamlessly into:

```Bash
# (executed from within the /workdir/wepppy directory)  
docker compose \--env-file docker/.env \-f docker/docker-compose.dev.yml ps
```

### **Installation**

To install wctl and make it available system-wide, follow these three steps.

#### Instanllation**

To make the command available from any location, create a symbolic link (symlink) to it from a directory in your system's PATH, such as /usr/local/bin.

```Bash
sudo ln -s /workdir/wepppy/wctl/wctl.sh /usr/local/bin/wctl
```

You can verify the installation by running which wctl, which should return /usr/local/bin/wctl. You are now ready to use the command.
