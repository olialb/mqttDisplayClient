#python
#
 # This file is part of the mqttDisplayClient distribution:
 # (https://github.com/olialb/mqttDisplayClient.
 # Copyright (c) 2025 Oliver Albold.
 #
 # This program is free software: you can redistribute it and/or modify
 # it under the terms of the GNU General Public License as published by
 # the Free Software Foundation, version 3.
 #
 # This program is distributed in the hope that it will be useful, but
 # WITHOUT ANY WARRANTY; without even the implied warranty of
 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 # General Public License for more details.
 #
 # You should have received a copy of the GNU General Public License
 # along with this program. If not, see <http://www.gnu.org/licenses/>.
 #
"""Module providing a function to fill an openhab things template"""

import configparser
import logging
import os
import sys
#
#initialize logger
#
LOG = logging.getLogger('OHThinksTemplate')
logging.basicConfig()

#
#global constants
#
CONFIG_FILE = 'mqttDisplayClient.ini' #name of the ini file

#import from the configuration file only the feature configuraion
CFG = configparser.ConfigParser()

#try to open ini file
try:
    if os.path.exists(CONFIG_FILE) is False:
        LOG.critical("Config file not found '%s'!", CONFIG_FILE )
    else:
        CFG.read(CONFIG_FILE)
except OSError:
    LOG.error("Error while reading ini XXX file: %s", {CONFIG_FILE})
    sys.exit()

#read ini file values
try:
#read logging config
    logLevel = CFG['logging']['level']
    if logLevel in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        LOG.setLevel (logLevel)
    else:
        raise KeyError(logLevel)

    deviceName= CFG['global']['deviceName']
    topicRoot = CFG['global']['topicRoot']

except KeyError as error:
    LOG.error("Error while reading ini file: %s", error)
    sys.exit()

with open("kioskdisplay.things.template",encoding="utf-8") as f:
    s = f.read()

s = s.format(name=deviceName, baseTopic=topicRoot)

with open("kioskdisplay.things", "w", encoding="utf-8") as text_file:
    text_file.write(s)
