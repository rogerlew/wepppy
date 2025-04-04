# wepppy/weppcloud on bare-metal server with conda env (wepppy310-env)

1. Install Ubuntu 24.04
1.1 Create webgroup with gid 1002 and add user to webgroup
2. Install dependendeecies based on wepppy-docker-base
3. Install libfortran3
```bash
cd ~
wget http://archive.ubuntu.com/ubuntu/pool/universe/g/gcc-6/gcc-6-base_6.4.0-17ubuntu1_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/g/gcc-6/libgfortran3_6.4.0-17ubuntu1_amd64.deb
sudo dpkg -i gcc-6-base_6.4.0-17ubuntu1_amd64.deb
sudo dpkg -i libgfortran3_6.4.0-17ubuntu1_amd64.deb
rm gcc-6-base_6.4.0-17ubuntu1_amd64.deb 
rm libgfortran3_6.4.0-17ubuntu1_amd64.deb
```

4. Install miniconda3 to /workdir/miniconda3
```bash
mkdir -p /workdir/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /workdir/miniconda3/miniconda.sh
bash /workdir/miniconda3/miniconda.sh -b -u -p /workdir/miniconda3
rm /workdir/miniconda3/miniconda.sh
conda config --add envs_dirs /workdir/miniconda3/envs
sudo chown -R roger:webgroup /workdir/miniconda3/
```

5. Build wepppy310-env conda environment
```bash
wget https://raw.githubusercontent.com/rogerlew/wepppy/refs/heads/master/wepppy310-env.yaml
conda env create -f wepppy310-env.yaml
```

6. clone wepppy
```bash
cd /workdir
git lfs install
git clone https://github.com/rogerlew/wepppy
```

7. clone all-your-base
```bash
cd /workdir/wepppy/all_your_base
rmdir all_your_base
git clone https://github.com/rogerlew/all_your_base
```

8. create wepppy.pth
```bash
echo "/workdir/wepppy/" > /workdir/miniconda3/envs/wepppy310-env/lib/python3.10/site-packages/wepppy.pth
```

9. Install rosetta
```bash
cd /workdir/miniconda3/envs/wepppy310-env/lib/python3.10/site-packages
git clone https://github.com/rogerlew/rosetta
```


10. install wepppy2
```bash
cd /workdir && git clone https://github.com/wepp-in-the-woods/wepppy2/
echo "/workdir/wepppy2/" > /workdir/miniconda3/envs/wepppy310-env/lib/python3.10/site-packages/wepp_runner.pth
```

11. install weppcloud2
```bash
cd /workdir && git clone https://github.com/wepp-in-the-woods/weppcloud2/
echo "/workdir/wepppycloud2/" > /workdir/miniconda3/envs/wepppy310-env/lib/python3.10/site-packages/weppcloud2.pth
```

12. install wepppyo3
```bash
cd /workdir && git clone https://github.com/wepp-in-the-woods/wepppyo3
rsync -av --progress /workdir/wepppyo3/release/linux/py310-wepppy310-env/wepppyo3/  /workdir/miniconda3/envs/wepppy310-env/lib/python3.10/site-packages/wepppyo3/
```


13. set permissions for miniconda
```bash
sudo chown -R roger:webgroup /workdir/miniconda3/
```

14. some additional config

14.1 OPENTOPOGRAPHY_API_KEY
you have to have the .env file. you don't have to have a key if you don't use earth


_Option 1_
```bash
scp roger@wepp.cloud:/workdir/wepppy/wepppy/locales/earth/opentopography/.env /workdir/wepppy/wepppy/locales/earth/opentopography/.env
```
_Option 2_

```bash
cd /workdir/wepppy/wepppy/locales/earth/opentopography/
vim .env
```

`.env` contents
```ini
OPENTOPOGRAPHY_API_KEY=<YOUR_KEY_HERE>
```


15. for apache2 (weppcloud webserver only)

15.1 configure mpm_event
```bash
sudo a2dismod mpm_prefork
sudo a2enmod mpm_event
```

15.1.1 other mods and confs (probably not comprehensive)
```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod rewrite
sudo a2enconf servername
```

15.2 configure site
```conf
see https://github.com/rogerlew/wepppy/blob/master/wepppy/weppcloud/_baremetal/weppcloud.conf
```

15.2.1 site requires ssl for proxing websockets

for local dev use mkcert to create self-signed certificates https://github.com/FiloSottile/mkcert

```bash
mkcert forest.local
```

15.3 build mod_wsgi (activate wepppy310-env)
```bash
conda install -c conda-forge mod_wsgi
```

verify .so
```bash
find "$CONDA_PREFIX" -name "mod_wsgi*.so"
```

should see
```bash
roger@forest:~$ find "$CONDA_PREFIX" -name "mod_wsgi*.so"
/workdir/miniconda3/envs/wepppy310-env/lib/python3.10/site-packages/mod_wsgi/server/mod_wsgi-py310.cpython-310-x86_64-linux-gnu.so
```

15.4 enable wsgi mod in apache
```bash
sudo vim /etc/apache2/mods-available/wsgi.conf
```

```conf
LoadModule wsgi_module "/workdir/miniconda3/envs/wepppy-env/lib/python3.12/site-packages/mod_wsgi/server/mod_wsgi-py312.cpython-312-x86_64-linux-gnu.so"
```

```bash
sudo a2enmod wsgi
```

15.5 sockets configuraiton

create this dir if it doesn't exist
```bash
sudo mkdir -p /var/run/apache2/wsgi
sudo chown www-data:www-data /var/run/apache2/wsgi
```

In your Apache configuration (e.g., in your VirtualHost config or in /etc/apache2/mods-available/wsgi.conf), add:
```conf
WSGISocketPrefix /var/run/apache2/wsgi
```

15.6 wsgi app file
```bash
sudo vim /var/www/weppcloud/weppcloud.wsgi
sudo chown www-data:www-data /var/www/weppcloud/weppcloud.wsgi
```

```python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/weppcloud/")

from wepppy.weppcloud import app as application
application.secret_key = <YOUR SECRET KEY HERE>
```

15.7 launch apache
```bash
sudo apachectl stop
sudo apachctl start
```

16. config for slave rq workers (not no machine with rq server)

16.1 nfs share

all workers need to find the weppcloud runs at `/wc/runs` and the archives at `/wc/archive` (as of 3-23-2025)

to share nfs

16.1.1 server

install nfs server
```bash
sudo apt install nfs-kernel-server
```

configure share by editing `/etc/exports`. my homelab has raid array mounted as `/home/`
```
/home/weppcloud  192.168.1.0/24(rw,sync,no_subtree_check)
```

16.1.2 nfs clients
edit `/etc/fstab` to mount nfs share automatically
```
192.168.1.107:/home/weppcloud /wc   nfs    vers=4.1,rw,sync,hard,timeo=600,retrans=3  0 0
```

create `/wc` folder and chown to www-data:webgroup
```bash
sudo mkdir /wc
sudo chown www-data:webgroup /wc
```

to hot-reload
```bash
sudo systemctl daemon-reload
sudo mount -a
```




16.2 rq .env ini file for rq status messenger

this is needed to proxy status messenges back to the web clients for rq worker not on master

`/workdir/wepppy/wepppy/nodb/.env`
```ini
REDIS_HOST=192.168.1.107
REDIS_URL=redis://192.168.1.107
```

17. launching rq workers


17.1 get byobu www-data shell
```bash
sudo -u www-data bash
byobu
```

make sure it is using `wepppy310-env` env

run
```bash
rq worker-pool -n 32 -u redis://192.168.1.107:6379/9 --worker-class 'wepppy.rq.WepppyRqWorker' high default low
```


18. compiling peridot from source (in wepppy310-env)
```bash
conda install -c conda-forge rust
cd /workdir
git clone https://github.com/wepp-in-the-woods/peridot
cd peridot
cargo clean
cargo build --release
```

19. f-esri for .gdb creation with gpkg export
see https://github.com/rogerlew/f-esri

20. discord bot 

TODO