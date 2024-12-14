#python

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
