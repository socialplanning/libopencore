import datetime
import time

def parse_listen_settings(ini):
    ini = ini.strip()
    settings = {}
    section = None
    for line in ini.splitlines():
        line = line.strip()
        if not line: continue
        if line == "[info]":
            section = "info"
            settings['info'] = {}
            continue
        elif line == "[preferences]":
            section = "preferences"
            settings['preferences'] = {}
            continue
        elif line == "[managers]":
            section = "managers"
            settings['managers'] = []
            continue
        elif line == "[description]":
            section = "description"
            settings['description'] = ''
            continue

        if section == "managers":
            settings[section].append(line)
            continue
        if section == "description":
            settings['description'] += line.strip() + " "
            continue

        assert "=" in line, line
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "created_on":
            format = "%Y-%m-%d %H:%M:%S"
            value = datetime.datetime(*(time.strptime(value, format)[0:6]))
        settings[section][key] = value
    settings['description'] = settings['description'].strip()
    return settings
