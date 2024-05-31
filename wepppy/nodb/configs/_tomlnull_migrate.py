# This script is used to migrate the old config files to the new format

from glob import glob


def isfloat(x):
    try:
        float(x)
        return True
    except ValueError:
        return False
    
cfgs = glob('*.cfg')


for cfg in cfgs[0:]:
    with open(cfg) as f:
        lines = f.readlines()

    with open(cfg, 'w') as f:
        for i, line in enumerate(lines):
            line = line.replace('True', 'true') \
                       .replace('False', 'false') \
                       .replace('None', 'None') \
                       .replace('none', 'None') \
                       .replace("'", '"') \
                       .replace(",)", ",]") \
                       .replace('("', '["') \
                       .replace('")', '"]')
            if '=' in line:
                key, value = line.split('=')
                v = value.lower().strip()
                if v in ['none', 'false', 'true']:
                    pass
                elif v.startswith('['):
                    pass
                elif isfloat(v):
                    pass
                elif v.startswith('"') and v.endswith('"'):
                    pass
                else:
                    if v == '':
                        v = "None"
                    line = f'{key} = "{v}"\n'
                
            f.write(line)