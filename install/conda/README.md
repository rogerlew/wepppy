# Conda on Ubuntu GNU/Linux

### (Optional) Step 1. Install on Windows Subsystem for Linux

Ubuntu 20.04 WSL

https://docs.microsoft.com/en-us/windows/wsl/install


### Step 2. Launch Ubuntu Shell 


### Step 3. Install conda

Go to https://docs.conda.io/en/latest/miniconda.html#linux-installers and get url for latest 3.7 Python installer

In Ubuntu shell wget the installer

```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
```

Set the script as executable

```
sudo chmod +x Miniconda3-latest-Linux-x86_64.sh
```

Run the installer

```
./Miniconda3-latest-Linux-x86_64.sh
```

After it completes close Ubuntu shell and then reopen it


### Step 4. Build conda-wepppy-env

```
conda create --name wepppy-env
```

```
conda update -n base -c defaults conda
```

Activate the weppy-env

```
conda activate wepppy-env
```

Download conda-wepppy-env.yaml file

```
wget https://raw.githubusercontent.com/rogerlew/wepppy/master/install/conda/requirements.txt
```

Run

```
conda install --file requirements.txt
```


### Step 5. Install wepppy

#### Step 5.1 Clone git repo

Install git-lfs

```
sudo apt-get install git-lfs
```

Then clone wepppy repository

```
git lfs clone https://github.com/rogerlew/wepppy 
```

#### Step 5.2 Install all_your_base submodule

Need to manually clone all_your_base submodule
```
cd wepppy/wepppy
rm -R all_your_base
git clone https://github.com/rogerlew/all_your_base
```

(Verify contents exist in all_your_base folder)

#### Step 5.3 Setup scratch drive

The all_your_base submodule specifies a SCRATCH variable to be used for temporary files.

This can be setup as a ramdisk mounted to /media/ramdisk or a folder named /workdir/scratch.

The easiest solution is:
```
sudo mkdir /workdir
sudo mkdir /workdir/scratch
sudo chown <username> /workdir/scratch
```

#### Step 5.4 add to wepppy-env path
```
nano ~/miniconda3/envs/wepppy-env/lib/python3.9/site-packages/wepppy.pth
```

add the path to your wepppy git repository and save file

e.g.

```
/home/<username>/wepppy/
```


#### Step 5.5 install rosetta python package

Rosetta predicts van Genuchten soil water retention curve parameters utilizing a weighted recalibration of the Rosetta pedotransfer model with improved estimates of hydraulic parameter distributions and summary statistics. 

```
cd ~/miniconda3/envs/wepppy-env/lib/python3.9/site-packages/
```

```
git clone https://github.com/rogerlew/rosetta
```

### Step 6. Update Ubuntu and install gfortran

#### Ubuntu 18.04
```
sudo apt update
sudo apt upgrade
sudo apt install libgfortran3
```

#### Ubuntu 20.04
libfortran3 is not provided by canonical

It can be installed through the following steps:

```
sudo apt update
sudo apt upgrade
sudo apt install libquadmath0
wget https://gist.githubusercontent.com/sakethramanujam/faf5b677b6505437dbdd82170ac55322/raw/c306b71253ec50fb55d59f935885773d533b565c/install-libgfortran3.sh
sudo chmod +x install-libgfortran3.sh
sudo ./install-libgfortran3.sh
```

### Step 7. Test scripted run

```
cd ~/wepppy/wepppy/_scripts
python3 test_scripted_run.py
```

### Optional. Running WEPPcloud Flask App

#### Setup directories
```
sudo mkdir /geodata
sudo mkdir /geodata/weppcloud_runs
sudo chown <username>:<username> /geodata/weppcloud_runs
```

### Start Flask App
```
cd ~/wepppy/wepppy/weppcloud
flask run
```

You should get a messaging stating that the flask app is running and should be able to load WEPPcloud on
http://localhost:5000/

This will still query wepp.cloud webservices for DEMs, etc.

### Troubleshooting


#### forrtl: too many files open

linux has a limit on the number of files that can be open. Linux, the default is 1024 file descriptors per process. The limit is per user on a per session basis. The limit can be checked with:

~~~
ulimit -n
~~~

and set as:

~~~
ulimit -n 4096
~~~

A more persistent solution is to set the default limits via /etc/security/limits.conf
~
<username>       soft    nofile          4096
<username>       hard    nofile          4096
~

more info:
https://www.tecmint.com/increase-set-open-file-limits-in-linux/
