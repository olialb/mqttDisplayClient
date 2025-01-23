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
import logging
import uuid
import json

#
#initialize logger
#
log = logging.getLogger('HADiscovery')
logging.basicConfig()

#
# this file defines everthing whats needed to publish
# the topics for homeassitant device discovery
#

class HADiscovery:
    def __init__(self, deviceName="MyDevice", base="homeassitant", manufacturer="MyCompany", model="MyModel"):
        self.uid = "_"+str(hex(uuid.getnode())).replace("0x","")+"_"
        self.deviceName = deviceName
        self.base = base
        self.manufacturer = manufacturer
        self.model = model
        
    def device(self):
        js = {}
        js['name'] = self.deviceName
        js['identifiers'] = self.deviceName+"_"+self.uid
        js['manufacturer'] = self.manufacturer
        js['model'] = self.model        
        return js
        
    def sensor( self, name, state_topic, valueTemplate=None , deviceClass=None, unit=None ):
        uid = self.uid
        topic = self.base+"/sensor/"+uid+"/"+name.replace(" ", "_")+"/config"
        js ={}
        js['name'] = name
        js['unique_id'] = self.uid+"_"+name.replace(" ", "_")
        js['state_topic'] = state_topic
        if unit != None:
            js['unit_of_measurement'] = unit
        if valueTemplate != None:
            js['value_template'] = "{{ value_json."+valueTemplate+" }}"
        if deviceClass != None:
            js['device_class'] = deviceClass
        js['device'] = self.device()
        return topic, json.dumps( js )
        
    def switch( self, name, state_topic, valueTemplate=None ):
        uid = self.uid
        topic = self.base+"/switch/"+uid+"/"+name.replace(" ", "_")+"/config"
        js ={}
        js['name'] = name
        js['unique_id'] = self.uid+"_"+name.replace(" ", "_")
        js['command_topic'] = state_topic+"/set"
        js['state_topic'] = state_topic
        js['payload_on'] = "ON"
        js['payload_off'] = "OFF"    
        js['state_on'] = "ON"
        js['state_off'] = "OFF"        
        if valueTemplate != None:
            js['value_template'] = "{{ value_json."+valueTemplate+" }}"
        js['device'] = self.device()
        return topic, json.dumps( js )

    def text( self, name, state_topic, valueTemplate=None ):
        uid = self.uid
        topic = self.base+"/text/"+uid+"/"+name.replace(" ", "_")+"/config"
        js ={}
        js['name'] = name
        js['unique_id'] = self.uid+"_"+name.replace(" ", "_")
        js['command_topic'] = state_topic+"/set"
        js['state_topic'] = state_topic
        if valueTemplate != None:
            js['value_template'] = "{{ value_json."+valueTemplate+" }}"
        js['device'] = self.device()
        return topic, json.dumps( js )

    def select( self, name, state_topic, options, valueTemplate=None ):
        uid = self.uid
        topic = self.base+"/select/"+uid+"/"+name.replace(" ", "_")+"/config"
        js ={}
        js['name'] = name
        js['unique_id'] = self.uid+"_"+name.replace(" ", "_")
        js['command_topic'] = state_topic+"/set"
        js['state_topic'] = state_topic
        js['options'] = options
        if valueTemplate != None:
            js['value_template'] = "{{ value_json."+valueTemplate+" }}"
        js['device'] = self.device()
        return topic, json.dumps( js )

    def light( self, name, state_topic, brightness_topic, valueTemplateState=None, valueTemplateBrightness=None, brightnessScale=100 ):
        uid = self.uid
        topic = self.base+"/light/"+uid+"/"+name.replace(" ", "_")+"/config"
        js ={}
        js['name'] = name
        js['unique_id'] = self.uid+"_"+name.replace(" ", "_")
        js['command_topic'] = state_topic+"/set"
        js['state_topic'] = state_topic
        js['payload_on'] = "ON"
        js['payload_off'] = "OFF"        
        js['state_on'] = "ON"
        js['state_off'] = "OFF"  
        js['brightness_scale'] = brightnessScale  
        js['brightness_command_topic'] = brightness_topic+"/set"                  
        js['brightness_state_topic'] = brightness_topic                  
        if valueTemplateState != None:
            js['state_value_template'] = "{{ value_json."+valueTemplateState+" }}"
        if valueTemplateBrightness != None:
            js['brightness_value_template'] = "{{ value_json."+valueTemplateBrightness+" }}"
        js['device'] = self.device()
        return topic, json.dumps( js )
        
    
   