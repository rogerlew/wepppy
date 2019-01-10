import os
import fnmatch

def find_maps():
    maps = []
    for root, dirnames, filenames in os.walk('./'):
        for filename in fnmatch.filter(filenames, '*.img'):
            maps.append(os.path.join(root, filename))
    return maps

maps = find_maps()

fid = open('map_list.txt', 'w')

for map in maps:
    fid.write('%s\n' %map)

fid.close()
