#!/bin/bash
# install in /usr/local/bin
# https://gist.github.com/KartikTalwar/4393116
rsync -aHAXxv --numeric-ids --delete --progress -e "ssh -T -o Compression=no -x" \
roger@wepp1.nkn.uidaho.edu:/geodata/weppcloud_runs/$1 /geodata/weppcloud_runs/$1