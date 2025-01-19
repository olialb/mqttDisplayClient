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
import time
import gpiozero
import json
import subprocess
import threading
import os
#used to validate URLs:
import validators
from paho.mqtt import client as mqtt_client

#
#initialize logger
#
log = logging.getLogger('MQTTClient')
logging.basicConfig()

#
#global constants
#
SWVERSION='V0.1'
CONFIG_FILE = 'mqttDisplayClient.ini' #name of the ini file
PANEL_DEFAULT = 'DEFAULT' #keyword to set the website back to the configured FullPageOS default
PANEL_SHOW_URL = 'URL' #keyword to set website as panel set over url topic
PANEL_BLANK_URL = 'about:blank' #URL of the blank web page
    
#import from the configuration file only the feature configuraion
_featureCfg_ = configparser.ConfigParser()

#try to open ini file
try:
    if os.path.exists(CONFIG_FILE) == False:
        log.critical(f"Config file not found '{CONFIG_FILE}'!")
    else:
        _featureCfg_.read(CONFIG_FILE)
except:
    log.error(f"Error while reading ini file: {CONFIG_FILE}")
    exit()

#read ini file values
try:
    #read logging config
    logLevel = _featureCfg_['logging']['level']
    log.setLevel (logLevel)

    #read features status
    _backlight_ = False
    if 'backlight' in _featureCfg_['feature']:
         if _featureCfg_['feature']['backlight'].upper() == 'ENABLED':
            _backlight_ = True

    _pyautogui_ = False    
    if 'pyautogui' in _featureCfg_['feature']:
        if _featureCfg_['feature']['pyautogui'].upper() == 'ENABLED':
            _pyautogui_ = True
                
except Exception as inst:
    log.error(f"Error while reading ini file: {inst}")
    exit()

#import the functions zo control the display with autogui 
if _pyautogui_: 
    os.environ['DISPLAY'] = ':0' #environment variable needed for pyautogui
    import pyautogui
    #local imports:
    from autoguiCommands import call_autogui_cmd_list, autogui_log_level
    #set loglevel of autogui
    autogui_log_level( logLevel )

#
#global settings
#
class MqttDisplayClient:    
    def __init__(self, configFile):
        #Global config:
        self.configFile = configFile        
        
        #other global attributes
        self.default_url=None #default url from FullPageOS config file
        self.displayID =None #Touch display ID
        self.reconnect_delay=5 #retry in seconds to try to reconnect mgtt broker
        self.publish_delay=3 #delay between two publish loops in seconds
        self.full_publish_cycle=20 #Every publishcycle*fullPublishCycle will be all topics published even if no data changed:
        self.topicRoot = None#Root path for all topics
        self.brightness=-1 #display brightness which was last published
        self.backlight=None #backlight status
        self.backlightPublished=None #backlight status which was last published
        self.unpublished=True #set to true if the topics are not published yet
        self.current_url=None #current shown website
        self.published_url=None #url which was last published to broker
        self.backlight=None #Last Backlight state
        self.client =None #mqtt client
        self.blankPageStatus='OFF' #status of blank page
        self.blankPageStatusPulished=None #last published status of blank page
        self.autoguiFeedback='NONE' #feedback on last macro call
        self.autoguiFeedbackPublished=None #last pubished feedback on last macro call
        self.autoguiCommands=None #commands which will be performt when current website is loaded
        self.currentPanel=PANEL_DEFAULT #Panel which is currently shown
        self.currentPanelPublished=None #Panel which was last publised to broker
        self.reservedPanelNames = [PANEL_DEFAULT, PANEL_SHOW_URL ]
        
        #broker config:
        self.broker=None
        self.port=1883
        self.username=""
        self.password=""
        
        #topic configuration
        self.tConfig = { 
            'brightness': { 'topic': 'brightness_percent', 'publish': self.publish_brightness, 'set': self.set_brightness },
            'backlight': { 'topic': 'backlight', 'publish': self.publish_backlight, 'set': self.set_backlight },        
            'system': { 'topic': 'system', 'publish': self.publish_system, 'set': self.system_command }, 
            'url': { 'topic' : 'url', 'publish': self.publish_url, 'set': self.set_url },
            'panel': { 'topic' : 'panel', 'publish': self.publish_panel, 'set': self.set_panel },
            'blank': {'topic':'blank_page', 'publish' : self.publish_blank_page_status, 'set':self.set_blank_page },
            'autogui' : {'topic':'autogui', 'publish' : self.publish_autogui_results, 'set':self.set_autogui },
            'status' : {'topic':'status', 'publish' : self.publish_status }
            }
        self.read_config_file()
        self.read_default_url()
        
    def read_config_file(self):
        #read ini file
        config = configparser.ConfigParser()
        #try to open ini file
        try:
            if os.path.exists(self.configFile) == False:
                log.critical(f"Config file not found '{self.configFile}'!")
            else:
                config.read(self.configFile)
        except:
            log.error(f"Error while reading ini file: {self.configFile}")
            exit()
        
        #read ini file values
        try:
            #read server config
            self.broker = config['global']['broker']
            self.port = int(config['global']['port']) 
            self.username = config['global']['username']
            self.password = config['global']['password']
            self.displayID= config['global']['displayID']
            self.deviceName= config['global']['deviceName']
            self.topicRoot = config['global']['topicRoot']+'/'+self.deviceName
            self.reconnect_delay = int(config['global']['reconnectDelay'])
            self.publish_delay = int(config['global']['publishDelay'])
            self.full_publish_cycle = int(config['global']['fullPublishCycle'])
            self.defaultUrlFile= config['global']['defaultUrl']
            
            #read mqtt topic config brighness
            self.tConfig['brightness']['min'] = int(config['brightness']['min'])
            self.tConfig['brightness']['max'] = int(config['brightness']['max'])
            self.tConfig['brightness']['cmd'] = config['brightness']['set']
            self.tConfig['brightness']['get'] = config['brightness']['get']
            
            #read mqtt topic config backlight
            self.tConfig['backlight']['ON'] = config['backlight']['ON']
            self.tConfig['backlight']['OFF'] = config['backlight']['OFF']
            self.tConfig['backlight']['cmd'] = config['backlight']['set']
            self.tConfig['backlight']['get'] = config['backlight']['get']
            
            #read mgtt topic config system
            self.tConfig['system']['commands'] = {}
            cmd_items = config.items( "shellCommands" )
            for key, cmd in cmd_items:
                self.tConfig['system']['commands'][key.upper()] = cmd
            #read new url command
            self.tConfig['url']['command'] = config['url']['command']        

            #read configured panels
            self.tConfig['panel']['panels'] = {}
            sites_items = config.items( "panels" )
            for key, panel in sites_items:
                if key in self.reservedPanelNames:
                    raise Exception(f"Reserved panel name not allowed: {key}")
                sList = panel.split('|')
                if validators.url( sList[0] ) == True:
                    self.tConfig['panel']['panels'][key.upper()] = panel
                else:
                    raise Exception(f"Configured URL not well formed: {key}={site}")
                    
        except Exception as inst:
            log.error(f"Error while reading ini file: {inst}")
            exit()        
 
    def read_default_url(self):
        #read the default page from FullPageOS
        try:
            with open( self.defaultUrlFile, "r") as f:
                self.default_url = str(f.read()).strip()
                if validators.url(self.default_url) == False:
                   log.warning( f"FullPageOS default page has not a well formend URL format: {self.current_url}" )
            log.info( f"FullPageOS default page: {self.default_url}" )
            self.current_url = self.default_url
        except Exception as inst:
            log.error(f"Error while reading FullPageOS web page config: {inst}")
            exit()
        
    def thread_autogui_func( self, cmds ):
        #excecute autogui commands with this website
        cmds = cmds.strip()
        feedback = call_autogui_cmd_list( cmds )
        if feedback == 'OK':
            log.info(f"Command list excecuted without error: '{cmds}'")
        else:
            log.warning(f"Command list excecuted with error: '{feedback}'")
        self.autoguiFeedback=feedback
        
    def call_autoguiCommands( self, cmds ):       
        if self.autoguiFeedback == 'EXCECUTION':
            log.warning(f"Thread allready running can not excecute: '{cmds}'")
            return
        self.autoguiFeedback = 'EXCECUTION'
        #create thread
        params=[cmds]
        thread = threading.Thread(target=self.thread_autogui_func, args=(params))
        #run the thread
        thread.start()

    @classmethod
    def on_connect(cls, client, inst, flags, rc, properties):
        if rc == 0:
            log.info("Connected to MQTT Broker!")
            #make the subscritions at the broker
            inst.subscribe()
        else:
            log.warning(f"Failed to connect, return code {rc}")

    @classmethod
    def on_disconnect(cls, client, inst, flags, rc, properties):
        log.info(f"Disconnected with result code: {rc}")
        inst.unpublished=True
        inst.brightness=-1
        while True:
            log.info(f"Reconnecting in {inst.reconnect_delay} seconds...")
            time.sleep(inst.reconnect_delay)

            try:
                client.reconnect()
                log.info("Reconnected successfully!")
                return
            except Exception as err:
                log.warning(f"{err}. Reconnect failed. Retrying...")

    @classmethod
    def on_message(cls, client, inst, msg):
        log.info(f"Received `{msg.payload.decode().strip()}` from `{msg.topic}` topic")
        
        #check received topic syntax
        if msg.topic[0:len(inst.topicRoot)] == inst.topicRoot:
            topic = msg.topic[len(inst.topicRoot):len(msg.topic)]
            topic = topic.split('/')
            if topic[2] != 'set':
                log.info(f"Wrong topic syntax received from broker {msg.topic}")
                return
            #search for topic:
            topicKey = None
            for key,t in inst.tConfig.items():
                if t['topic'] == topic[1]:
                    topicKey = key
                    break
                    
            if topicKey != None:
                #call the configured command
                if 'set' in inst.tConfig[topicKey]:
                    inst.tConfig[topicKey]['set'](inst.tConfig[topicKey],msg.payload.decode())
                else:
                    log.info(f"Command for topic without command received from broker {msg.topic}")                    
            else:
                log.info(f"Command for unknown topic received from broker {msg.topic}")
        else:
            log.info(f"Wrong topic syntax received from broker {msg.topic}")                    

    def connect(self) -> mqtt_client:    
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        if self.username != "":
            self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = MqttDisplayClient.on_connect
        self.client.on_disconnect = MqttDisplayClient.on_disconnect
        while True:
            try:
                self.client.connect(self.broker, self.port)
            except Exception as inst:
                log.warning(f"Error while connect to server {broker}:{port}: {inst}")
                time.sleep(self.reconnect_delay)
                continue
            break
        #set user data for call backs
        self.client.user_data_set( self )
    
        #start main loop of mqtt client
        self.client.loop_start()
        
    def set_website( self, url ):
        #set a defined given website
        err, msg = subprocess.getstatusoutput( self.tConfig['url']['command'].format(url=url) )
        if err != 0: 
            log.error(f"Error {err} executing command: {msg}")
        return err


    def set_brightness( self, myConfig, msg ):
        if _backlight_ == False:
            #feature is switched off
            log.warning(f"Error brightness command received but backlight feature is not enabled!")
            return
        #Synax OK we can call the command to set the brightness
        msg = msg.strip()
        min = myConfig['min']
        max = myConfig['max']
        try:
            value = int((float(msg)) / (100/(max-min)))+min
            if value > max: value = max
            if value < min: value = min
        except Exception as inst:
            log.warning(f"Error in brightness payload {msg}: {inst}")
            return

        #call command to set the brightness
        log.debug(myConfig['cmd'].format(value=value, displayID=self.displayID))
        err, msg = subprocess.getstatusoutput( myConfig['cmd'].format(value=value, displayID=self.displayID) )
        if err != 0:
            log.error(f"Error {err} executing command: {msg}")

    def set_backlight( self, myConfig, msg ):
        if _backlight_ == False:
            #feature is switched off
            log.warning(f"Error backlight command received but feature is not enabled!")
            return
        #Synax OK we can call the command to set the backlight status
        msg = msg.strip()
        if msg.upper() == 'ON' or msg.upper() == 'OFF':
            value = myConfig[msg]
        else:
            log.warning(f"Error in backlight payload: {msg}")
            return

        #call command to set the backlight
        if msg != self.backlight: 
            log.debug(myConfig['cmd'].format(value=value, displayID=self.displayID))
            err, ret = subprocess.getstatusoutput( myConfig['cmd'].format(value=value, displayID=self.displayID) )
            if err != 0:
                log.error(f"Error {err} executing command: {ret}")
            else:
                self.backlight=msg
    
    def system_command( self, myConfig, msg ):
        msg = msg.strip().upper()
        if msg.upper() in myConfig['commands']:
            #call the configured command
            log.debug(f"Call command: {myConfig['commands'][msg]}")
            err, msg = subprocess.getstatusoutput( myConfig['commands'][msg] )
            if err != 0:
                log.error(f"Error {err} executing command: {msg}")
        else:
            log.info(f"Unknown command payload received: '{msg}'")                    

    def set_url( self, myConfig, msg ):
        msg=msg.strip()
        if validators.url( msg ):
            newsite = msg
        else:
            log.info(f"Received url has no valid format: '{msg}'")                    
            return
                    
        if self.blankPageStatus == 'OFF' and self.currentPanel == PANEL_SHOW_URL:
            #set the new url in browser:
            err, msg = subprocess.getstatusoutput( myConfig['command'].format(url=newsite) )
            if err != 0: 
                log.error(f"Error {err} executing command: {msg}")
                self.autoguiCommands=None
                return
            self.current_url = newsite
            if self.autoguiCommands != None and _pyautogui_==True:
                self.call_autoguiCommands( self.autoguiCommands )
        else:
            self.current_url = newsite

    def set_panel( self, myConfig, msg ):
        msg=msg.strip()
        newsite=None
        if msg.upper() == PANEL_DEFAULT:
            newsite=self.default_url
            self.currentPanel = PANEL_DEFAULT
            self.autoguiCommads=None
        else:
            if msg.upper() == PANEL_SHOW_URL:
                newsite=self.current_url
                self.currentPanel = PANEL_SHOW_URL
                self.autoguiCommads=None
            else:
                if msg.upper() in myConfig['panels']:
                    definition = myConfig['panels'][msg.upper()]
                    self.currentPanel = msg.upper()
                    #does the definition contain autogui commands?
                    index = definition.find('|')
                    if index > 0:
                        self.autoguiCommands=definition[index+1:]
                        newsite = definition[0:index]
                    else:
                        newsite = definition
                else:
                    log.info(f"Received panel name is not configured: '{msg.upper()}'")                    
                    return                
                
        if self.blankPageStatus == 'OFF':
            #set the new url in browser:
            err, msg = subprocess.getstatusoutput( self.tConfig['url']['command'].format(url=newsite) )
            if err != 0: 
                log.error(f"Error {err} executing command: {msg}")
                self.autoguiCommands=None
                return
            self.current_url = newsite
            if self.autoguiCommands != None and _pyautogui_==True:
                self.call_autoguiCommands( self.autoguiCommands )
        else:
            self.current_url = newsite
 

    def set_blank_page( self, myConfig, msg ):
        #Synax OK we can call the command to set the backlight status
        msg = msg.strip()
        if msg.upper() == 'ON':
            if self.blankPageStatus != 'ON':
                #set blank page
                self.set_website( PANEL_BLANK_URL )
        else:
            if msg.upper() == 'OFF':
                if self.blankPageStatus != 'OFF':
                    self.set_website( self.current_url )
                    if self.autoguiCommands != None and _pyautogui_==True:
                        self.call_autoguiCommands( self.autoguiCommands )
            else:
                log.warning(f"Error in blank_page payload: '{msg}'")
                return
        self.blankPageStatus = msg.upper()
        
    def set_autogui( self, myConfig, msg ):
        if _pyautogui_ == True:
            self.call_autoguiCommands( msg )
                        
    def subscribe(self):
        #Subscribe to all configured topics
        for key in self.tConfig:
            if 'topic' in self.tConfig[key]:
                topic = self.topicRoot + f"/{self.tConfig[key]['topic']}/set"
                self.client.subscribe(topic)
                log.debug(f"Subscribe to: {topic}")
        self.client.on_message = MqttDisplayClient.on_message


    def publish_status(self, topic, myConfig):
        #publich online status
        #send message to broker
        if self.unpublished == True:
            result = self.client.publish(topic, "online")
            # result: [0, 1]
            status = result[0]
            if status == 0:
                log.debug(f"Send 'online' to topic {topic}")
            else:
                log.error(f"Failed to send message to topic {topic}")

    def publish_system(self, topic, myConfig):
        #collect system info
        systemInfo = {}
        systemInfo['cpu_temp'] = gpiozero.CPUTemperature().temperature
        systemInfo['cpu_load'] = int(gpiozero.LoadAverage().load_average*100)
        systemInfo['disk_usage'] = gpiozero.DiskUsage().usage 
        if _pyautogui_ == True:
            systemInfo['mouse_position'] = pyautogui.position()
            systemInfo['display_size'] = pyautogui.size()
        systemInfo['default_url'] = self.default_url
        #create a json out of it
        msg=json.dumps(systemInfo)
        #send message to broker
        result = self.client.publish(topic, msg)
        # result: [0, 1]
        status = result[0]
        if status == 0:
            log.debug(f"Send '{msg}' to topic {topic}")
        else:
            log.error(f"Failed to send message to topic {topic}")

    def publish_brightness(self, topic, myConfig):
        if _backlight_ == False:
            #feature is switched off
            return
        #call command to read the brightness
        err, msg = subprocess.getstatusoutput( myConfig['get'].format(displayID=self.displayID) )
        if not err:
            min = myConfig['min']
            max = myConfig['max']
            msg = int(float(msg) * (100/(max-min)))
            #send message to broker
            if self.brightness != msg or self.unpublished == True:
                result = self.client.publish(topic, msg)
                # result: [0, 1]
                status = result[0]
                if status == 0:
                    log.debug(f"Send '{msg}' to topic {topic}")
                    self.brightness = msg
                else:
                    log.error(f"Failed to send message to topic {topic}")
        else:
            log.error(f"Error reading display brightness: {err}")

    def publish_backlight(self, topic, myConfig):
        if _backlight_ == False:
            #feature is switched off
            return
        #call command to read the backlight state
        err, msg = subprocess.getstatusoutput( myConfig['get'].format(displayID=self.displayID) )
        if not err:
            on = myConfig['ON']
            off = myConfig['OFF']
            msg = msg.strip()
            if msg == on:
                value = 'ON'
            else:
                value = 'OFF'
            #send message to broker
            if self.backlightPublished != value or self.unpublished == True:
                result = self.client.publish(topic, value)
                # result: [0, 1]
                status = result[0]
                if status == 0:
                    log.debug(f"Send '{value}' to topic {topic}")
                    self.backlight = value
                    self.backlightPublished = value
                else:
                    log.error(f"Failed to send message to topic {topic}")
        else:
            log.error(f"Error reading display backlight status: {err}")

    def publish_url(self, topic, myConfig):
        if self.published_url != self.current_url or self.unpublished == True:
            result = self.client.publish(topic, self.current_url)
            # result: [0, 1]
            status = result[0]
            if status == 0:
                log.debug(f"Send '{self.current_url}' to topic {topic}")
                self.published_url = self.current_url
            else:
                log.error(f"Failed to send message to topic {topic}")
                
    def publish_panel(self, topic, myConfig):
        if self.currentPanel != self.currentPanelPublished or self.unpublished == True:
            result = self.client.publish(topic, self.currentPanel)
            # result: [0, 1]
            status = result[0]
            if status == 0:
                log.debug(f"Send '{self.currentPanel}' to topic {topic}")
                self.currentPanelPublished = self.currentPanel
            else:
                log.error(f"Failed to send message to topic {topic}")
                
    def publish_blank_page_status(self, topic, myConfig):
        #publish status of blank page
        if self.unpublished == True or self.blankPageStatusPulished != self.blankPageStatus:
            result = self.client.publish(topic, self.blankPageStatus)
            # result: [0, 1]
            status = result[0]
            if status == 0:
                log.debug(f"Send '{self.blankPageStatus}' to topic {topic}")
                self.blankPageStatusPulished = self.blankPageStatus
            else:
                log.error(f"Failed to send message to topic {topic}")
                
    def publish_autogui_results(self, topic, myConfig):
        #publish result of last autogui commads
        if _pyautogui_ == True:
            if self.unpublished == True or self.autoguiFeedback != self.autoguiFeedbackPublished:
                result = self.client.publish(topic, self.autoguiFeedback)
                # result: [0, 1]
                status = result[0]
                if status == 0:
                    log.debug(f"Send '{self.autoguiFeedback}' to topic {topic}")
                    self.autoguiFeedbackPublished = self.autoguiFeedback
                else:
                    log.error(f"Failed to send message to topic {topic}")
                
    def publish_loop(self):
        #endless publish loop
        self.unpublished=True
        loopCounter=0
        while True:
            for key in self.tConfig:
                if 'publish' in self.tConfig[key]:
                    topic = f"{self.topicRoot}/{self.tConfig[key]['topic']}"
                    self.tConfig[key]['publish'](topic, self.tConfig[key])
            #mark the topics as published
            self.unpublished=False
            #delay until next loo starts
            time.sleep(self.publish_delay)
            loopCounter += 1
            if loopCounter > self.full_publish_cycle:
                loopCounter = 0
                self.unpublished=True
            
        
def mqtt_display_client():
    mqttDisplayClient = MqttDisplayClient( CONFIG_FILE )
    mqttDisplayClient.connect()
    mqttDisplayClient.publish_loop()

if __name__ == '__main__':
    mqtt_display_client()
