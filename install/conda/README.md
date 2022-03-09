# Conda

## Install on Windows Subsystem for Linux

### Step 1. Install Ubuntu 18.04 WSL

https://docs.microsoft.com/en-us/windows/wsl/install



### Step 2. Launch Ubuntu Shell



### Step 3. Install conda

Go to https://docs.conda.io/en/latest/miniconda.html#linux-installers and get url for latest 3.7 Python installer

In Ubuntu shell wget the installer

```
> wget https://repo.anaconda.com/miniconda/Miniconda3-py37_4.11.0-Linux-x86_64.sh
```

Set the script as executable

```
> sudo chmod +x Miniconda3-py37_4.11.0-Linux-x86_64.sh
```

Run the installer

```
> ./Miniconda3-py37_4.11.0-Linux-x86_64.sh
```

After it completes close Ubuntu shell and then reopen it

Download conda-wepppy-env.yaml file

```
> wget https://raw.githubusercontent.com/rogerlew/wepppy/master/install/conda/conda-wepppy-env.yaml
```


