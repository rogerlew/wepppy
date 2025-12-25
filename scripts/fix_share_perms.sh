#!/bin/bash
# Fix permissions for shared directories

for dir in /geodata/share /geodata/islay.ceoas.oregonstate.edu /geodata/revegetation /geodata/mtbs; do
    if [ -d "$dir" ]; then
        echo "Fixing $dir"
        sudo chgrp -R docker "$dir"
        sudo chmod -R g+w "$dir"
        sudo find "$dir" -type d -exec chmod g+s {} \;
    fi
done

# Remove the empty index.html
sudo rm /geodata/share/index.html

echo "Done! Users in docker group can now add files to these directories."
