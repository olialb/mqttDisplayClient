# python
#
# This file is part of the mqttDisplayClient distribution
# (https://github.com/olialb/mqttDisplayClient).
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
"""
Module to test the MQTT client for FullPageOS

This are integration test which test the functionality against a mqtt broker 
triggered by a test client

pyautogui is used to make screenshots of the screen content
"""

import configparser
#import logging
#import logging.handlers
import time
import json
import subprocess
#import threading
import os
import glob
#import signal
import sys

# used to validate URLs:
#import validators
import gpiozero
from paho.mqtt import client as mqtt_client
#from ha_discover import HADiscovery

#import py autogui $DISPLAY must be set
os.environ["DISPLAY"] = ":0"  # environment variable needed for pyautogui
import pyautogui

#import test object
sys.path.append(os.path.abspath("./"))
import mqtt_display_client as MDC

#
# global constants
#
WAIT_FOR_URL_LOADED = 3
#
# initialize logger
#
#LOG = logging.getLogger("MQTTClient")
#logging.basicConfig()

#
# define test client
#
class TestMqttDisplayClient:
    """
    Main class of MQTT display client for FullPageOS
    """
    #prevent pytest to collect somthing from this class
    __test__ = False
    def __init__(self, config_file):
        """
        Constructor takes config file as parameter (ini file) and defines global atrributes
        """
        # Global config:
        self.config_file = config_file

        # other global attributes
        self.default_url = None  # default url from FullPageOS config file
        self.display_id = None  # Touch display ID
        self.reconnect_delay = 5  # retry in seconds to try to reconnect mgtt broker
        self.publish_delay = 3  # delay between two publish loops in seconds
        self.full_publish_cycle = 20  # Every publishcycle*fullPublishCycle
        # will be all topics published even if no data changed
        self.topic_root = None  # Root path for all topics
        self.brightness = -1  # display brightness which was last published
        self.backlight = None  # backlight status
        self.client = None  # mqtt client
        self.current_panel = MDC.PANEL_DEFAULT  # Panel which is currently shown
        self.current_panel_published = None  # Panel which was last publised to broker
        self.reserved_panel_names = [MDC.PANEL_DEFAULT, MDC.PANEL_SHOW_URL]
        self.shell_cmd = MDC.IDLE
        self.published_shell_cmd = None
        
        #connection state
        self.connected = False
        self.offline = True

        # broker config:
        self.broker = None
        self.port = 1883
        self.username = ""
        self.password = ""

        # topic configuration
        self.topic_config = None

        # topic data
        self.topic_data = {}
        
    def read_config_file(self):
        """
        Reads the configured ini file and sets attributes based on the config
        """
        # read ini file
        config = configparser.ConfigParser()
        # try to open ini file
        try:
            if os.path.exists(self.config_file) is False:
                print("Config file not found '%s'!" % self.config_file)
            else:
                config.read(self.config_file)
        except OSError:
            print("Error while reading ini file: %s" % self.config_file)
            sys.exit()

        # read in+i file values
        try:
            # read server config
            self.broker = config["global"]["broker"]
            self.port = int(config["global"]["port"])
            self.username = config["global"]["username"]
            self.password = config["global"]["password"]
            self.display_id = config["global"]["displayID"]
            self.device_name = config["global"]["deviceName"]
            self.topic_root = config["global"]["topicRoot"] + "/" + self.device_name
            self.reconnect_delay = int(config["global"]["reconnectDelay"])
            self.publish_delay = int(config["global"]["publishDelay"])
            self.full_publish_cycle = int(config["global"]["fullPublishCycle"])
            self.default_url_file = config["global"]["defaultUrl"]

            # read mqtt topic config brighness
            self.topic_config["brightness"]["min"] = int(config["brightness"]["min"])
            self.topic_config["brightness"]["max"] = int(config["brightness"]["max"])
            self.topic_config["brightness"]["cmd"] = config["brightness"]["set"]
            self.topic_config["brightness"]["get"] = config["brightness"]["get"]

            # read mqtt topic config backlight
            self.topic_config["backlight"]["ON"] = config["backlight"]["ON"]
            self.topic_config["backlight"]["OFF"] = config["backlight"]["OFF"]
            self.topic_config["backlight"]["cmd"] = config["backlight"]["set"]
            self.topic_config["backlight"]["get"] = config["backlight"]["get"]

            # read config system commands
            self.topic_config["shell"]["commands"] = {}
            cmd_items = config.items("shellCommands")
            for key, cmd in cmd_items:
                self.topic_config["shell"]["commands"][key.upper()] = cmd

            # read configured panels
            self.topic_config["panel"]["panels"] = {}
            sites_items = config.items("panels")
            for key, panel in sites_items:
                if key in self.reserved_panel_names:
                    raise RuntimeError(f"Reserved panel name not allowed: {key}")
                s_list = panel.split("|")
                self.topic_config["panel"]["panels"][key.upper()] = panel

            # read config HADiscovery
            self.ha_device_name = config["haDiscover"]["deviceName"]
            self.ha_base = config["haDiscover"]["base"]

        except (KeyError, RuntimeError) as error:
            print("Error while reading ini file: %s" % error)
            sys.exit()

    def read_default_url(self):
        """
        Reads configures default url of FullPageOS
        """
        # read the default page from FullPageOS
        try:
            with open(self.default_url_file, "r", encoding="utf-8") as f:
                self.default_url = str(f.read()).strip()
            print("FullPageOS default page: %s" % self.default_url)
        except OSError as error:
            print("Error while reading FullPageOS web page config: %s" % error)
            sys.exit()

    @classmethod
    def on_connect(cls, client, inst, flags, rc, properties): # pylint: disable=too-many-positional-arguments,too-many-arguments,unused-argument
        """
        method is colled when the mqtt client connects to the broker
        """
        if rc == 0:
            print("Connected to MQTT Broker!")
            # make the subscritions at the broker
            inst.subscribe()
            inst.connected = True
        else:
            print("Failed to connect, return code %s" % rc)

    @classmethod
    def on_disconnect(cls, client, inst, flags, rc, properties): # pylint: disable=too-many-positional-arguments,too-many-arguments,unused-argument
        """
        method is called when the mqtt client disconnects from the server
        """
        print("Disconnected with result code: %s" % rc)
        inst.connected = False
        while inst.offline is False:
            print("Reconnecting in %s seconds..." % inst.reconnect_delay)
            time.sleep(inst.reconnect_delay)

            try:
                client.reconnect()
                print("Reconnected successfully!")
                return
            except OSError as err:
                print("%s. Reconnect failed. Retrying..." % err)

    @classmethod
    def on_message(cls, client, inst, msg): # pylint: disable=unused-argument
        """
        method is called when the cleint receives a message from the broker
        """
        print(
            "Received `%s` from `%s` topic" % (msg.payload.decode().strip(), msg.topic)
        )

        # just store the eceived data
        inst.topic_data[msg.topic] = msg.payload.decode()

    def connect(self) -> mqtt_client:
        """
        Method to connect to the mqtt broker
        """
        self.offline = False
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        if self.username != "":
            self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = TestMqttDisplayClient.on_connect
        self.client.on_disconnect = TestMqttDisplayClient.on_disconnect
        while True:
            try:
                self.client.connect(self.broker, self.port)
            except OSError as error:
                print(
                    "Error while connect to server %s:%s: %s" %
                    (self.broker,
                    self.port,
                    error)
                )
                time.sleep(self.reconnect_delay)
                continue
            break
        # set user data for call backs
        self.client.user_data_set(self)

        # start main loop of mqtt client
        self.client.loop_start()
        
    def disconnect(self):
        """
        Disconnect from broker
        """
        self.offline = True
        self.client.disconnect()
        print("Disconnect from MQTT broker")

    def subscribe(self):
        """
        method to subscribe to all the configured topics at the broker
        """
        # Subscribe to all configured topics
        for topic_config in self.topic_config.values():
            if "topic" in topic_config:
                topic = self.topic_root + f"/{topic_config['topic']}"
                self.client.subscribe(topic)
                print("Subscribe to: %s" % topic)
        self.client.on_message = TestMqttDisplayClient.on_message

    def get_data( self, topic ):
        """
        returns data which was received for this topic or None
        """
        topic = self.topic_root+'/'+topic
        if topic in self.topic_data:
            return self.topic_data[topic]
        return None
    
    def wait_for_data( self, topic, data):
        """
        wait that a topic has a specific content
        """
        topic = self.topic_root+'/'+topic
        count=0
        topic_data=None
        while topic_data != data and count < (self.full_publish_cycle*self.publish_delay)+2:
            count +=1
            time.sleep(1)
            if topic in self.topic_data:
                topic_data = self.topic_data[topic]
        return topic_data == data
    
    def send_cmd(self, topic, msg):
        """
        Sends a message to a command topic
        """
        topic = self.topic_root+'/'+topic+'/set'
        result = self.client.publish(topic, msg)
        # result: [0, 1]
        status = result[0]
        if status != 0:
            print("Failed to send message to topic %s" % topic)

    def get_backlight_status(self):
        err, msg = subprocess.getstatusoutput(
            self.topic_config["backlight"]["get"].format(displayID=self.display_id)
        )
        if not err:
            on = self.topic_config["backlight"]["ON"]
            msg = msg.strip()
            if msg == on:
                return "ON"
            return "OFF"
        return None
        
    def get_brightness(self):
        err, msg = subprocess.getstatusoutput(
            self.topic_config["brightness"]["get"].format(displayID=self.display_id)
        )
        if not err:
            bmin = self.topic_config["brightness"]["min"]
            bmax = self.topic_config["brightness"]["max"]
            return int(float(msg) * (100 / (bmax - bmin)))
        return None
    
    def calc_brightness(self, percent):
        bmin = self.topic_config["brightness"]["min"]
        bmax = self.topic_config["brightness"]["max"]
        value = int((float(percent)) / (100 / (bmax - bmin))) + bmin
        value = min(bmax, max( bmin, value ))
        return int(float(value) * (100 / (bmax - bmin)))
 
        
DUMMY_CLIENT = MDC.MqttDisplayClient( MDC.CONFIG_FILE )

TST_CLIENT = TestMqttDisplayClient(MDC.CONFIG_FILE)
TST_CLIENT.topic_config = DUMMY_CLIENT.topic_config
TST_CLIENT.read_config_file()
TST_CLIENT.read_default_url()

TST_CLIENT.connect()

#
# test case section
#

#
# Test preparation...
#
def test_ini_file_exits():
    assert os.path.exists(MDC.CONFIG_FILE) is not False
    
# import from the configuration file only the feature configuraion
FEATURE_CFG = configparser.ConfigParser()

def test_ini_file_can_be_read(): 
    FEATURE_CFG.read(MDC.CONFIG_FILE)

# read ini file values
def test_ini_log_level():
    # read logging config
    LOG_LEVEL = FEATURE_CFG["logging"]["level"]
    assert LOG_LEVEL.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


def test_default_url():
    assert DUMMY_CLIENT.default_url == TST_CLIENT.default_url

def test_wait_connect_broker():
    count=0
    while TST_CLIENT.connected is False and count <= 5:
        time.sleep(1)
        count += 1
        print ("Wait connect to broker..." )
    assert TST_CLIENT.connected is True
    
def test_test_object_connected():
    count=0
    data=None
    while data is None and count <= TST_CLIENT.publish_delay*2:
        print(TST_CLIENT.topic_data)
        data = TST_CLIENT.get_data('system')
        time.sleep(1)
        count+=1
    assert data != None, "No data received! mqttDisplayClient not running?"

def test_delete_old_screenshots():
    for screenshot in glob.glob('tst_*.png'):
        os.remove(screenshot)
#
# Everything is prepared
# Functional testing standard features...
#
def test_start_screen():
    pyautogui.screenshot( 'tst_start.png')

def test_system_content_basic():
    data = json.loads(TST_CLIENT.get_data('system'))
    assert 'cpu_temp' in data
    cpu_temp = float(data['cpu_temp'])
    ct = gpiozero.CPUTemperature().temperature
    assert cpu_temp*0.9 < ct and cpu_temp*1.1 > ct, "Strange cpu temperature received"
    assert 'cpu_load' in data
    cpu_load = float(data['cpu_load'])
    cl = gpiozero.LoadAverage().load_average * 100
    assert cpu_load*0.9 < cl and cpu_load*1.1 > cl, "Strange cpu load received"
    assert 'disk_usage' in data
    disk_usage = float(data['disk_usage'])
    du = gpiozero.DiskUsage().usage
    assert disk_usage*0.9 < du and disk_usage*1.1 > du, "Strange disk_usage received"
    assert 'default_url' in data
    assert data['default_url'] == TST_CLIENT.default_url.strip()

def test_shell_content():
    assert TST_CLIENT.wait_for_data( 'shell', MDC.IDLE), "Shell contains no idle content"

def test_shell_command():
    #cleanup test file:
    if os.path.isfile ('test.txt'):
        os.remove('test.txt')
    TST_CLIENT.send_cmd('shell', 'Test') #send special test command
    assert TST_CLIENT.wait_for_data('shell', 'Test'), "Test command not excecuted. Is it configured in ini file?"
    assert os.path.isfile ('test.txt'), "test file not created"
    assert TST_CLIENT.wait_for_data( 'shell', MDC.IDLE), "shell not returning to idle content"
    assert not os.path.isfile ('test.txt'), "test file not deleted"

def test_set_url():
    TST_CLIENT.send_cmd('url', 'https://www.google.com/')
    assert TST_CLIENT.wait_for_data( 'url', 'https://www.google.com/' )
    assert TST_CLIENT.wait_for_data( 'panel', MDC.PANEL_SHOW_URL.capitalize()), "Panel does not switch to URL"
    time.sleep(WAIT_FOR_URL_LOADED)
    pyautogui.screenshot( 'tst_google1.png')
    
def test_set_default():
    TST_CLIENT.send_cmd('panel', MDC.PANEL_DEFAULT)
    assert TST_CLIENT.wait_for_data( 'panel', MDC.PANEL_DEFAULT.capitalize()), "Panel does not switch to DEFAULT"
    assert TST_CLIENT.wait_for_data( 'url', TST_CLIENT.default_url.strip() )
    time.sleep(WAIT_FOR_URL_LOADED)
    pyautogui.screenshot( 'tst_default1.png')

def test_set_configured_panels():
    for panel, url in TST_CLIENT.topic_config['panel']['panels'].items():
        TST_CLIENT.send_cmd('panel', panel)
        assert TST_CLIENT.wait_for_data( 'panel', panel.capitalize()), "Panel does not switch"
        url = url.split('|')[0].strip()
        assert TST_CLIENT.wait_for_data( 'url', url )
        time.sleep(WAIT_FOR_URL_LOADED)
        pyautogui.screenshot( 'tst_'+panel.lower()+'.png')

def test_blank_page():
    TST_CLIENT.send_cmd('panel', MDC.PANEL_BLANK)
    assert TST_CLIENT.wait_for_data( 'panel', MDC.PANEL_BLANK.capitalize()), "Panel does not switch to BLANK"
    assert TST_CLIENT.wait_for_data( 'url', MDC.PANEL_BLANK_URL )
    time.sleep(WAIT_FOR_URL_LOADED)
    pyautogui.screenshot( 'tst_blank_page.png')

def test_set_url_back():
    TST_CLIENT.send_cmd('panel', MDC.PANEL_SHOW_URL)
    assert TST_CLIENT.wait_for_data( 'url', 'https://www.google.com/' )
    assert TST_CLIENT.wait_for_data( 'panel', MDC.PANEL_SHOW_URL.capitalize()), "Panel does not switch"
    time.sleep(WAIT_FOR_URL_LOADED)
    pyautogui.screenshot( 'tst_google2.png')

#
# Test backlight features:
#
def test_backlight_status():
    TST_CLIENT.send_cmd('backlight', "OFF")
    assert TST_CLIENT.wait_for_data( 'backlight', "OFF"), "backlight  does not switch off"
    assert TST_CLIENT.get_backlight_status() == 'OFF'
    TST_CLIENT.send_cmd('backlight', "ON")
    assert TST_CLIENT.wait_for_data( 'backlight', "ON"), "backlight does not switch on"
    assert TST_CLIENT.get_backlight_status() == 'ON'

def test_brightness():
    TST_CLIENT.send_cmd('brightness_percent', "0")
    assert TST_CLIENT.wait_for_data( 'brightness_percent', str(TST_CLIENT.calc_brightness(0)))
    assert TST_CLIENT.get_brightness() == TST_CLIENT.calc_brightness(0)
    TST_CLIENT.send_cmd('brightness_percent', "100")
    assert TST_CLIENT.wait_for_data( 'brightness_percent', str(TST_CLIENT.calc_brightness(100)))
    assert TST_CLIENT.get_brightness() == TST_CLIENT.calc_brightness(100)
    TST_CLIENT.send_cmd('brightness_percent', "-1")
    assert TST_CLIENT.wait_for_data( 'brightness_percent', str(TST_CLIENT.calc_brightness(0)))
    assert TST_CLIENT.get_brightness() == TST_CLIENT.calc_brightness(0)
    TST_CLIENT.send_cmd('brightness_percent', "200")
    assert TST_CLIENT.wait_for_data( 'brightness_percent', str(TST_CLIENT.calc_brightness(100)))
    assert TST_CLIENT.get_brightness() == TST_CLIENT.calc_brightness(100)
    TST_CLIENT.send_cmd('brightness_percent', "50")
    assert TST_CLIENT.wait_for_data( 'brightness_percent', str(TST_CLIENT.calc_brightness(50)))
    assert TST_CLIENT.get_brightness() == TST_CLIENT.calc_brightness(50)
#    
# Test autogui features
#
def test_system_content_autogui():
    data = json.loads(TST_CLIENT.get_data('system'))
    assert 'mouse_position' in data
    pos = pyautogui.position()
    assert data['mouse_position'][0] == pos[0] and data['mouse_position'][1] == pos[1]
    assert 'display_size' in data
    size = pyautogui.size()
    assert data['display_size'][0] == size[0] and data['display_size'][1] == size[1]

def test_autogui_wrong_syntax_01():
    TST_CLIENT.send_cmd('autogui', "test")
    assert TST_CLIENT.wait_for_data( 'autogui', "Unknown command: 'test'")

def test_autogui_wrong_syntax_02():
    TST_CLIENT.send_cmd('autogui', "test_()")
    assert TST_CLIENT.wait_for_data( 'autogui', "Unknown command: 'test_'")

def test_autogui_wrong_syntax_03():
    TST_CLIENT.send_cmd('autogui', "scroll()")
    assert TST_CLIENT.wait_for_data( 'autogui', "Unknown command: 'scroll'")

def test_autogui_wrong_syntax_04():
    TST_CLIENT.send_cmd('autogui', "test(;")
    assert TST_CLIENT.wait_for_data( 'autogui', "Error missing closing bracket: 'test':OK. Stop.")

def test_autogui_wrong_syntax_05():
    TST_CLIENT.send_cmd('autogui', "test(")
    assert TST_CLIENT.wait_for_data( 'autogui', "Syntax error with command. Unterminated string: 'test()'")

def test_autogui_wrong_syntax_06():
    TST_CLIENT.send_cmd('autogui', "scroll(5);test(;scroll(2)")
    assert TST_CLIENT.wait_for_data( 'autogui', "Error missing closing bracket: 'test':OK. Stop.")

def test_autogui_wrong_syntax_07():
    TST_CLIENT.send_cmd('autogui', "test-")
    assert TST_CLIENT.wait_for_data( 'autogui', "Not allowed character in command name: 'test-'. Stop.")

def test_autogui_wrong_syntax_08():
    TST_CLIENT.send_cmd('autogui', "scroll(5),")
    assert TST_CLIENT.wait_for_data( 'autogui', "Wrong character after: 'scroll(5),'. Stop.")

def test_autogui_wrong_syntax_09():
    TST_CLIENT.send_cmd('autogui', "test'")
    assert TST_CLIENT.wait_for_data( 'autogui', "Syntax error. Character ' is not allowed here: test().")

def test_autogui_wrong_syntax_10():
    TST_CLIENT.send_cmd('autogui', "scroll(5)  +")
    assert TST_CLIENT.wait_for_data( 'autogui', "Wrong character after: 'scroll(5)+'. Stop.")

def test_autogui_wrong_syntax_11():
    TST_CLIENT.send_cmd('autogui', 'test"')
    assert TST_CLIENT.wait_for_data( 'autogui', 'Syntax error. Character " is not allowed here: test().')

def test_autogui_wrong_syntax_12():
    TST_CLIENT.send_cmd('autogui', "test(\\")
    assert TST_CLIENT.wait_for_data( 'autogui', "Esc char outside strings not allowed: 'test()'.")

def test_autogui_wrong_syntax_13():
    TST_CLIENT.send_cmd('autogui', "test\\")
    assert TST_CLIENT.wait_for_data( 'autogui', "Esc char outside strings not allowed: 'test'.")
 
def test_autogui_wrong_syntax_14():
    TST_CLIENT.send_cmd('autogui', "test() \\")
    assert TST_CLIENT.wait_for_data( 'autogui', "Esc char outside strings not allowed: 'test()'.")

def test_autogui_wrong_syntax_15():
    TST_CLIENT.send_cmd('autogui', "test(\"\"\")")
    assert TST_CLIENT.wait_for_data( 'autogui', 'Syntax error. Character " is not allowed here: test("").')

def test_autogui_wrong_syntax_16():
    TST_CLIENT.send_cmd('autogui', "test("")")
    assert TST_CLIENT.wait_for_data( 'autogui', "Unknown command: 'test'")

#
# Test finsh...
#
def test_disconnect_broker():
    TST_CLIENT.disconnect()

#    mqtt_display_client.ha_discover()
#    mqtt_display_client.publish_loop()
#
#for i in range(5):
#    time.sleep(1)