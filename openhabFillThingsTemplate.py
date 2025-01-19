#python
# 
 # This file is part of the mqttDisplayClient distribution (https://github.com/olialb/mqttDisplayClient).
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

import configparser
import logging
import os
#
#initialize logger
#
log = logging.getLogger('OHThinksTemplate')
logging.basicConfig()

#
#global constants
#
CONFIG_FILE = 'mqttDisplayClient.ini' #name of the ini file
    
#import from the configuration file only the feature configuraion
_cfg_ = configparser.ConfigParser()

#try to open ini file
try:
    if os.path.exists(CONFIG_FILE) == False:
        log.critical(f"Config file not found '{CONFIG_FILE}'!")
    else:
        _cfg_.read(CONFIG_FILE)
except:
    log.error(f"Error while reading ini XXX file: {CONFIG_FILE}")
    exit()

#read ini file values
#try:
#read logging config
logLevel = _cfg_['logging']['level']
log.setLevel (logLevel)

deviceName= _cfg_['global']['deviceName']
topicRoot = _cfg_['global']['topicRoot']

#except Exception as inst:
#    log.error(f"Error while reading ini file: {inst}")
#    exit()

with open("kioskdisplay.things.template") as f:
    str = f.read()
    
str = str.format(name=deviceName, baseTopic=topicRoot)

with open("kioskdisplay.things", "w") as text_file:
    text_file.write(str)
