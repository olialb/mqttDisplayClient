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
Module implements a MQTT client for FullPageOS
"""

import configparser
import logging
import logging.handlers
import time
import json
import subprocess
import threading
import os
import signal
import sys

# used to validate URLs:
import validators
import gpiozero
from paho.mqtt import client as mqtt_client
from ha_discover import HADiscovery
from chrome_tab_api import ChromeTabAPI

#
# global constants
#
SWVERSION = "V0.1"
CONFIG_FILE = "mqttDisplayClient.ini"  # name of the ini file
PANEL_DEFAULT = (
    "DEFAULT"  # keyword to set the website back to the configured FullPageOS default
)
PANEL_SHOW_URL = "URL"  # keyword to set website as panel set over url topic
PANEL_BLANK_URL = "about:blank"  # URL of the blank web page
PANEL_BLANK = "BLANK" #show a blank panel
MANUFACTURER = "githab olialb"
MODEL = "FullPageOS"
IDLE = ">_"
LOG_ROTATE_WHEN='midnight'
LOG_BACKUP_COUNT=5
LOG_FILE_PATH="log"
LOG_FILE_NAME='mqttDisplayClient.log'
LOG_FILE_HANDLER = None
#
# initialize logger
#
LOG = logging.getLogger("MQTTClient")
logging.basicConfig()

# import from the configuration file only the feature configuraion
FEATURE_CFG = configparser.ConfigParser()

# try to open ini file
try:
    if os.path.exists(CONFIG_FILE) is False:
        LOG.critical("Config file not found '%s'!", CONFIG_FILE)
    else:
        FEATURE_CFG.read(CONFIG_FILE)
except OSError:
    LOG.error("Error while reading ini file: %s", CONFIG_FILE)
    sys.exit()

# read ini file values
try:
    # read logging config
    LOG_LEVEL = FEATURE_CFG["logging"]["level"]
    if LOG_LEVEL.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        LOG.setLevel (LOG_LEVEL.upper())
    else:
        raise KeyError(LOG_LEVEL)

    if "path" in FEATURE_CFG["logging"]:
        LOG_FILE_PATH = FEATURE_CFG["logging"]["path"]
    if "file" in FEATURE_CFG["logging"]:
        LOG_FILE_NAME = FEATURE_CFG["logging"]["file"]
    try:
        os.makedirs( LOG_FILE_PATH )
        LOG.debug( "Logging directory created: ./%s", LOG_FILE_PATH )
    except FileExistsError:
        LOG.info( "Logging directory exist already: ./%s", LOG_FILE_PATH )
    except OSError:
        LOG.error( "Can not create Logging directory: ./%s", LOG_FILE_PATH )

    #create time rotating logger for log files
    LOG_FILE_HANDLER = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_FILE_PATH,LOG_FILE_NAME),
        when=LOG_ROTATE_WHEN,
        backupCount=LOG_BACKUP_COUNT
        )
    # Set the formatter for the logging handler
    LOG_FILE_HANDLER.setFormatter(
        logging.Formatter('%(asctime)s-%(name)s-%(levelname)s-%(message)s')
    )
    LOG.addHandler( LOG_FILE_HANDLER )

    # read features status
    BACKLIGHT = False
    if "backlight" in FEATURE_CFG["feature"]:
        if FEATURE_CFG["feature"]["backlight"].upper() == "ENABLED":
            BACKLIGHT = True

    PYAUTOGUI = False
    if "pyautogui" in FEATURE_CFG["feature"]:
        if FEATURE_CFG["feature"]["pyautogui"].upper() == "ENABLED":
            PYAUTOGUI = True

    HADISCOVER = False
    if "haDiscover" in FEATURE_CFG["feature"]:
        if FEATURE_CFG["feature"]["haDiscover"].upper() == "ENABLED":
            HADISCOVER = True

except KeyError as error:
    LOG.error("Error while reading ini file: %s", error)
    sys.exit()
# import the functions zo control the display with autogui
if PYAUTOGUI:
    os.environ["DISPLAY"] = ":0"  # environment variable needed for pyautogui
    import pyautogui

    # local imports:
    from autogui_commands import call_autogui_cmd_list, autogui_log

    # set loglevel of autogui
    autogui_log(LOG_LEVEL, LOG_FILE_HANDLER)

#
# define main class
#
class MqttDisplayClient: # pylint: disable=too-many-instance-attributes
    """
    Main class of MQTT display client for FullPageOS
    """
    def __init__(self, config_file):
        """
        Constructor takes config file as parameter (ini file) and defines global atrributes
        """
        # Global config:
        self.config_file = config_file

        # other global attributes
        self.default_url_file = None  # default FullPageOS config file for url
        self.display_id = None  # Touch display ID
        self.reconnect_delay = 5  # retry in seconds to try to reconnect mgtt broker
        self.publish_delay = 3  # delay between two publish loops in seconds
        self.full_publish_cycle = 20  # Every publishcycle*fullPublishCycle
        # will be all topics published even if no data changed
        self.topic_root = None  # Root path for all topics
        self.brightness = -1  # display brightness which was last published
        self.backlight = None  # backlight status
        self.backlight_published = None  # backlight status which was last published
        self.unpublished = True  # set to true if the topics are not published yet
        self.published_url = None  # url which was last published to broker
        self.client = None  # mqtt client
        self.autogui_feedback = "OK"  # feedback on last macro call
        self.autogui_feedback_published = (
            None  # last pubished    feedback on last macro call
        )
        self.autogui_commands = (
            None  # commands which will be performt when current website is loaded
        )
        self.current_panel = PANEL_DEFAULT  # Panel which is currently shown
        self.current_panel_published = None  # Panel which was last publised to broker
        self.reserved_panel_names = [PANEL_DEFAULT, PANEL_SHOW_URL, PANEL_BLANK]
        self.shell_cmd = IDLE
        self.published_shell_cmd = None
        #chrome api attributes
        self.chrome_pages = None
        self.chrome_port = 9222
        self.chrome_tab_timeout = 600
        self.chrome_reload_timeout = 3600

        # broker config:
        self.broker = None
        self.port = 1883
        self.username = ""
        self.password = ""

        # topic configuration
        self.topic_config = {
            "brightness": {
                "topic": "brightness_percent",
                "publish": self._publish_brightness,
                "set": self._set_brightness,
            },
            "backlight": {
                "topic": "backlight",
                "publish": self._publish_backlight,
                "set": self._set_backlight,
            },
            "system": {"topic": "system", "publish": self._publish_system},
            "shell": {
                "topic": "shell",
                "publish": self._publish_shell_cmd,
                "set": self._set_shell_cmd,
            },
            "url": {"topic": "url", "publish": self._publish_url, "set": self._set_url},
            "panel": {
                "topic": "panel",
                "publish": self._publish_panel,
                "set": self._set_panel,
            },
            "autogui": {
                "topic": "autogui",
                "publish": self._publish_autogui_results,
                "set": self._set_autogui,
            },
        }
        #read the ini file
        self.read_config_file()
        #read default config of FullPageOS
        self.read_default_url()
        #after default url of FullPageOS is known add it to topic config
        self.topic_config["panel"]["panels"][PANEL_DEFAULT] = self.default_url
        self.topic_config["panel"]["panels"][PANEL_SHOW_URL] = self.default_url
        self.topic_config["panel"]["panels"][PANEL_BLANK] = PANEL_BLANK_URL

    def init_chrome_api( self, config ):
        """Chreate to class for the chrome api"""
        # read chrome config
        try:
            self.chrome_port = config["chrome"]["port"]
            self.chrome_tab_timeout = int(config["chrome"]["pageTimeout"])
            self.chrome_reload_timeout = int(config["chrome"]["reloadTimeout"])
        except (KeyError, ValueError):
            LOG.warning("[chrome] section not specified in ini file! Default values used" )

        self.chrome_pages = ChromeTabAPI(
            self.publish_delay,
            self.chrome_port,
            (self.chrome_tab_timeout, self.chrome_reload_timeout)
        )
        self.chrome_pages.set_log(LOG_LEVEL, LOG_FILE_HANDLER)
        self.chrome_pages.sync()
        self.chrome_pages.set_reload_callback( self.autogui_panel_cmds )

    def read_config_file(self):
        """
        Reads the configured ini file and sets attributes based on the config
        """
        # read ini file
        config = configparser.ConfigParser()
        # try to open ini file
        try:
            if os.path.exists(self.config_file) is False:
                LOG.critical("Config file not found '%s'!", self.config_file)
            else:
                config.read(self.config_file)
        except OSError:
            LOG.error("Error while reading ini file: %s", self.config_file)
            sys.exit()

        # read ini file values
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

            #create chrome Page class
            self.init_chrome_api(config)

            # read configured panels
            sites_items = config.items("panels")
            self.topic_config["panel"]["panels"] = {}
            for key, panel in sites_items:
                if key in self.reserved_panel_names:
                    raise RuntimeError(f"Reserved panel name not allowed: {key}")
                s_list = panel.split("|")
                if validators.url(s_list[0]) is True:
                    self.topic_config["panel"]["panels"][key.upper()] = panel
                else:
                    raise RuntimeError(f"Configured URL not well formed: {key}={s_list[0]}")

            # read config HADiscovery
            self.ha_device_name = config["haDiscover"]["deviceName"]
            self.ha_base = config["haDiscover"]["base"]

        except (KeyError, RuntimeError) as error:
            LOG.error("Error while reading ini file: %s", error)
            sys.exit()

    def read_default_url(self):
        """
        Reads configures default url of FullPageOS
        """
        # read the default page from FullPageOS
        try:
            with open(self.default_url_file, "r", encoding="utf-8") as f:
                self.default_url = str(f.read()).strip()
                if validators.url(self.default_url) is False:
                    LOG.warning(
                        "FullPageOS default page has not a well formend URL format: %s",
                        self.default_url
                    )
            LOG.info("FullPageOS default page: %s", self.default_url)
        except OSError as error:
            LOG.error("Error while reading FullPageOS web page config: %s", error)
            sys.exit()

    def thread_autogui_func(self, cmds):
        """
        Thread which is executing a string with autogui commands
        """
        # excecute autogui commands with this website
        cmds = cmds.strip()
        feedback = call_autogui_cmd_list(cmds) # pylint: disable=possibly-used-before-assignment
        if feedback == "OK":
            LOG.info("Command list excecuted without error: '%s'",cmds)
        else:
            LOG.warning("Command list excecuted with error: '%s'", feedback)
        self.autogui_feedback = feedback

    def call_autogui_commands(self, cmds):
        """
        Starts a thread with is excecutiong autogui commands from a string
        parallel to the client.
        """
        if self.autogui_feedback[0 : len("EXEC")] == "EXEC":
            LOG.warning("Thread allready running can not excecute: '%s'",cmds)
            return
        self.autogui_feedback = "EXEC: " + cmds
        # create thread
        params = [cmds]
        thread = threading.Thread(target=self.thread_autogui_func, args=params)
        # run the thread
        thread.start()

    @classmethod
    def on_connect(cls, client, inst, flags, rc, properties): # pylint: disable=too-many-positional-arguments,too-many-arguments,unused-argument
        """
        method is colled when the mqtt client connects to the broker
        """
        if rc == 0:
            LOG.info("Connected to MQTT Broker!")
            # make the subscritions at the broker
            inst.subscribe()
        else:
            LOG.warning("Failed to connect, return code %s", rc)

    @classmethod
    def on_disconnect(cls, client, inst, flags, rc, properties): # pylint: disable=too-many-positional-arguments,too-many-arguments,unused-argument
        """
        method is called when the mqtt client disconnects from the server
        """
        LOG.info("Disconnected with result code: %s", rc)
        inst.unpublished = True
        inst.brightness = -1
        while True:
            LOG.info("Reconnecting in %s seconds...", inst.reconnect_delay)
            time.sleep(inst.reconnect_delay)

            try:
                client.reconnect()
                LOG.info("Reconnected successfully!")
                return
            except OSError as err:
                LOG.warning("%s. Reconnect failed. Retrying...", err)

    @classmethod
    def on_message(cls, client, inst, msg): # pylint: disable=unused-argument
        """
        method is called when the cleint receives a message from the broker
        """
        LOG.info(
            "Received `%s` from `%s` topic", msg.payload.decode().strip(), msg.topic
        )

        # check received topic syntax
        if msg.topic[0 : len(inst.topic_root)] == inst.topic_root:
            topic = msg.topic[len(inst.topic_root) : len(msg.topic)]
            topic = topic.split("/")
            if topic[2] != "set":
                LOG.info("Wrong topic syntax received from broker %s", msg.topic)
                return
            # search for topic:
            topic_key = None
            for key, t in inst.topic_config.items():
                if t["topic"] == topic[1]:
                    topic_key = key
                    break

            if topic_key is not None:
                # call the configured command
                if "set" in inst.topic_config[topic_key]:
                    inst.topic_config[topic_key]["set"](
                        inst.topic_config[topic_key], msg.payload.decode()
                    )
                else:
                    LOG.info(
                        "Command for topic without command received from broker %s",
                        msg.topic
                    )
            else:
                LOG.info("Command for unknown topic received from broker %s", msg.topic)
        else:
            LOG.info("Wrong topic syntax received from broker %s", msg.topic)

    def connect(self) -> mqtt_client:
        """
        Method to connect to the mqtt broker
        """
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        if self.username != "":
            self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = MqttDisplayClient.on_connect
        self.client.on_disconnect = MqttDisplayClient.on_disconnect
        while True:
            try:
                self.client.connect(self.broker, self.port)
            except OSError as error:
                LOG.warning(
                    "Error while connect to server %s:%s: %s",
                    self.broker,
                    self.port,
                    error,
                )
                time.sleep(self.reconnect_delay)
                continue
            break
        # set user data for call backs
        self.client.user_data_set(self)

        # start main loop of mqtt client
        self.client.loop_start()

    def autogui_panel_cmds( self ):
        """call back to perform autogui commands assigned to current panel"""
        if self.autogui_commands is not None and PYAUTOGUI is True:
            self.call_autogui_commands( self.autogui_commands )

    def _set_website(self, url):
        """
        helper method to set an url in the browser
        """
        # set a defined given website
        return self.chrome_pages.activate_tab ( url )

    def _set_brightness(self, my_config, msg):
        """
        mqtt command to set the brightness
        """
        if BACKLIGHT is False:
            # feature is switched off
            LOG.warning(
                "Error brightness command received but backlight feature is not enabled!"
            )
            return
        # Synax OK we can call the command to set the brightness
        msg = msg.strip()
        bmin = my_config["min"]
        bmax = my_config["max"]
        try:
            value = int((float(msg)) / (100 / (bmax - bmin))) + bmin
            value = min(bmax, max( bmin, value ))
        except ValueError as error:
            LOG.warning("Error in brightness payload %s: %s", msg, error)
            return

        # call command to set the brightness
        LOG.debug("Call: %s",my_config["cmd"].format(value=value, displayID=self.display_id))
        err, msg = subprocess.getstatusoutput(
            my_config["cmd"].format(value=value, displayID=self.display_id)
        )
        if err != 0:
            LOG.error("Error %s executing command: %s", err, msg)

    def _set_backlight(self, my_config, msg):
        """
        mqtt command to switch the backlight on and off
        """
        if BACKLIGHT is False:
            # feature is switched off
            LOG.warning("Error backlight command received but feature is not enabled!")
            return
        # Synax OK we can call the command to set the backlight status
        msg = msg.strip()
        if msg.upper() == "ON" or msg.upper() == "OFF":
            value = my_config[msg]
        else:
            LOG.warning("Error in backlight payload: %s", msg)
            return

        # call command to set the backlight
        if msg != self.backlight:
            LOG.debug(my_config["cmd"].format(value=value, displayID=self.display_id))
            err, ret = subprocess.getstatusoutput(
                my_config["cmd"].format(value=value, displayID=self.display_id)
            )
            if err != 0:
                LOG.error("Error %s executing command: %s", err, ret)
            else:
                self.backlight = msg

    def thread_shell_cmd_func(self, cmd):
        """
        thread which executes a shell command in parallel to the client
        """
        # excecute system cmd
        err, msg = subprocess.getstatusoutput(cmd)
        if err != 0:
            LOG.error("Error %s executing command: %s", err, msg)
            self.shell_cmd = IDLE
        else:
            self.shell_cmd = IDLE

    def _set_shell_cmd(self, my_config, msg):
        """
        mqtt command to execute a shell command in a parallel thread
        """
        msg = msg.strip().upper()
        if msg.upper() in my_config["commands"]:
            if self.shell_cmd != IDLE:
                # currently is another command running. Skip this command
                LOG.warning("Shell command allready running skip: %s", msg)
                return
            # call the configured command
            LOG.debug("Call command: %s", my_config["commands"][msg])
            self.shell_cmd = msg
            # publish that the command is now executed
            self._publish_shell_cmd(
                self.topic_root + "/" + my_config["topic"], my_config
            )
            # ürepare thread
            params = [my_config["commands"][msg]]
            thread = threading.Thread(target=self.thread_shell_cmd_func, args=params)
            # run the thread
            thread.start()
        else:
            LOG.info("Unknown command payload received: '%s'", msg)

    def _set_url(self, my_config, msg): # pylint: disable=unused-argument
        """
        mqtt command to set an individual url
        """
        msg = msg.strip()
        if not validators.url(msg):
            LOG.info("Received url has no valid format: '%s'", msg)
            return

        # set the new url in browser:
        if self._set_website( msg ) is not True:
            LOG.warning("Received url could not be opened: '%s'", msg)
        else:
            self.autogui_commands = None
            self.topic_config["panel"]["panels"][PANEL_SHOW_URL] = msg

    def _set_panel(self, my_config, msg):
        """
        mqtt command to set one of the configured panel urls
        """
        msg = msg.strip()
        newsite = None
        if msg.upper() in my_config["panels"]:
            definition = my_config["panels"][msg.upper()]
            self.current_panel = msg.upper()
            # does the definition contain autogui commands?
            index = definition.find("|")
            if index > 0:
                self.autogui_commands = definition[index + 1 :]
                newsite = definition[0:index]
            else:
                newsite = definition
                self.autogui_commands = None
        else:
            LOG.info("Received panel name is not configured: '%s'", msg.upper())
            return

        # set the new url in browser:
        if self._set_website ( newsite ) is True:
            if self.autogui_commands is not None and PYAUTOGUI is True:
                self.call_autogui_commands(self.autogui_commands)
        else:
            LOG.error("Panel could not be activated: '%s'", msg.upper())

    def _set_autogui(self, my_config, msg): # pylint: disable=unused-argument
        """
        mqtt command to execute a list of autogui commands from a string
        """
        if PYAUTOGUI is True:
            self.call_autogui_commands(msg)

    def subscribe(self):
        """
        method to subscribe to all the configured topics at the broker
        """
        # Subscribe to all configured topics
        for topic_config in self.topic_config.values():
            if "topic" in topic_config:
                topic = self.topic_root + f"/{topic_config['topic']}/set"
                self.client.subscribe(topic)
                LOG.debug("Subscribe to: %s", topic)
        self.client.on_message = MqttDisplayClient.on_message

    def _publish_system(self, topic, my_config): # pylint: disable=unused-argument
        """
        publish the system topic
        """
        # collect system info
        system_info = {}
        system_info["chrome_tabs"] = self.chrome_pages.tab_count()
        system_info["cpu_temp"] = round(gpiozero.CPUTemperature().temperature, 2)
        system_info["cpu_load"] = int(gpiozero.LoadAverage().load_average * 100)
        system_info["disk_usage"] = round(gpiozero.DiskUsage().usage, 2)
        if PYAUTOGUI is True:
            system_info["mouse_position"] = pyautogui.position() # pylint: disable=possibly-used-before-assignment
            system_info["display_size"] = pyautogui.size()
        system_info["default_url"] = self.default_url
        # create a json out of it
        msg = json.dumps(system_info)
        # send message to broker
        result = self.client.publish(topic, msg)
        # result: [0, 1]
        status = result[0]
        if status == 0:
            LOG.debug("Send '%s' to topic %s", msg, topic)
        else:
            LOG.error("Failed to send message to topic %s", topic)

    def _publish_brightness(self, topic, my_config):
        """
        publish the brightness topic
        """
        if BACKLIGHT is False:
            # feature is switched off
            return
        # call command to read the brightness
        err, msg = subprocess.getstatusoutput(
            my_config["get"].format(displayID=self.display_id)
        )
        if not err:
            bmin = my_config["min"]
            bmax = my_config["max"]
            msg = int(float(msg) * (100 / (bmax - bmin)))
            # send message to broker
            if self.brightness != msg or self.unpublished is True:
                result = self.client.publish(topic, msg)
                # result: [0, 1]
                status = result[0]
                if status == 0:
                    LOG.debug("Send '%s' to topic %s", msg, topic)
                    self.brightness = msg
                else:
                    LOG.error("Failed to send message to topic %s", topic)
        else:
            LOG.error("Error reading display brightness: %s", err)

    def _publish_shell_cmd(self, topic, my_config): # pylint: disable=unused-argument
        """
        publish the shell command topic
        """
        if self.shell_cmd != self.published_shell_cmd or self.unpublished is True:
            result = self.client.publish(topic, self.shell_cmd.capitalize())
            # result: [0, 1]
            status = result[0]
            if status == 0:
                LOG.debug("Send '%s' to topic %s", self.shell_cmd, topic)
                self.published_shell_cmd = self.shell_cmd
            else:
                LOG.error("Failed to send message to topic %s", topic)

    def _publish_backlight(self, topic, my_config):
        """
        publish the backlight topic
        """
        if BACKLIGHT is False:
            # feature is switched off
            return
        # call command to read the backlight state
        err, msg = subprocess.getstatusoutput(
            my_config["get"].format(displayID=self.display_id)
        )
        if not err:
            on = my_config["ON"]
            msg = msg.strip()
            if msg == on:
                value = "ON"
            else:
                value = "OFF"
            # send message to broker
            if self.backlight_published != value or self.unpublished is True:
                result = self.client.publish(topic, value)
                # result: [0, 1]
                status = result[0]
                if status == 0:
                    LOG.debug("Send '%s' to topic %s", value, topic)
                    self.backlight = value
                    self.backlight_published = value
                else:
                    LOG.error("Failed to send message to topic %s", topic)
        else:
            LOG.error("Error reading display backlight status: %s", err)

    def _publish_url(self, topic, my_config): # pylint: disable=unused-argument
        """
        publish the url topic
        """
        #Get current url from chrome:
        current_url = self.chrome_pages.active_url()
        if self.published_url != current_url or self.unpublished is True:
            result = self.client.publish(topic, current_url)
            # result: [0, 1]
            status = result[0]
            if status == 0:
                LOG.debug("Send '%s' to topic %s",current_url, topic)
                self.published_url = current_url
            else:
                LOG.error("Failed to send message to topic %s", topic)

    def _publish_panel(self, topic, my_config): # pylint: disable=unused-argument
        """
        publish the panel topic
        """
        #try to find panel by current url from chrome:
        current_url = self.chrome_pages.active_url()
        self.current_panel = PANEL_SHOW_URL
        self.autogui_commands = None
        #search in panel configuration
        for panel_name, url in my_config['panels'].items():
            #remove autogui commands in url definition:
            if len(url.split('|')) > 1:
                cmds = url.split('|')[1]
            else:
                cmds = None
            url = url.split('|')[0]
            if current_url == url:
                self.current_panel = panel_name
                self.autogui_commands = cmds
                break
        if ( self.current_panel != self.current_panel_published or
            self.unpublished is True ):
            result = self.client.publish(topic, self.current_panel.capitalize())
            # result: [0, 1]
            status = result[0]
            if status == 0:
                LOG.debug("Send '%s' to topic %s", self.current_panel, topic)
                self.current_panel_published = self.current_panel
            else:
                LOG.error("Failed to send message to topic %s", topic)

    def _publish_autogui_results(self, topic, my_config): # pylint: disable=unused-argument
        """
        publish the autogui result topic
        """
        # publish result of last autogui commads
        if PYAUTOGUI is True:
            if (
                self.unpublished is True
                or self.autogui_feedback != self.autogui_feedback_published
            ):
                result = self.client.publish(topic, self.autogui_feedback)
                # result: [0, 1]
                status = result[0]
                if status == 0:
                    LOG.debug("Send '%s' to topic %s", self.autogui_feedback, topic)
                    self.autogui_feedback_published = self.autogui_feedback
                else:
                    LOG.error("Failed to send message to topic %s", topic)

    def _ha_publish(self, topic, payload):
        """
        publish a single topics needed for home assistant mqtt discovery
        """
        if HADISCOVER is True:
            # publish new entity
            result = self.client.publish(topic, payload, retain=True)
        else:
            # delete entity
            result = self.client.publish(topic, "", retain=True)
        status = result[0]
        if status == 0:
            LOG.debug("Send '%s' to topic %s", payload, topic)
        else:
            LOG.error("Failed to send message to topic %s", topic)

    def ha_discover(self):
        """
        piblish all ropics needed for the home assistant mqtt discovery
        """
        # pubish all topics that home assisstant can discover them
        ha = HADiscovery(self.ha_device_name, self.ha_base, MANUFACTURER, MODEL)

        # cpu temperature
        topic, payload = ha.sensor(
            "cpu temperature",
            self.topic_root + "/system",
            "cpu_temp",
            "temperature",
            "°C",
        )
        self._ha_publish(topic, payload)

        # chrome tabs
        topic, payload = ha.sensor("Active chrome tabs", self.topic_root + "/system", "chrome_tabs")
        self._ha_publish(topic, payload)

        # cpu load
        topic, payload = ha.sensor("cpu load", self.topic_root + "/system", "cpu_load")
        self._ha_publish(topic, payload)

        # disk usage
        topic, payload = ha.sensor(
            "disk usage", self.topic_root + "/system", "disk_usage", "battery", "%"
        )
        self._ha_publish(topic, payload)

        # url
        topic, payload = ha.text("URL", self.topic_root + "/url")
        self._ha_publish(topic, payload)

        # panel select
        options = list(self.topic_config["panel"]["panels"])
        for i, option in enumerate(options):
            options[i] = option.capitalize()
        topic, payload = ha.select("Panel", self.topic_root + "/panel", options)
        self._ha_publish(topic, payload)

        # shell commands
        options = [IDLE] + list(self.topic_config["shell"]["commands"].keys())
        for i, option in enumerate(options):
            options[i] = option.capitalize()
        topic, payload = ha.select("shell command", self.topic_root + "/shell", options)
        self._ha_publish(topic, payload)

        if BACKLIGHT is True:
            # backlight "light"
            topic, payload = ha.light(
                "backlight",
                self.topic_root + "/backlight",
                self.topic_root + "/brightness_percent",
            )
            self._ha_publish(topic, payload)

        if PYAUTOGUI is True:
            # mouse x position
            topic, payload = ha.sensor(
                "Mouse X Pos", self.topic_root + "/system", "mouse_position[0]"
            )
            self._ha_publish(topic, payload)
            # mouse y position
            topic, payload = ha.sensor(
                "Mouse Y Pos", self.topic_root + "/system", "mouse_position[1]"
            )
            self._ha_publish(topic, payload)
            # autogui command string
            topic, payload = ha.text("AutoGUI command", self.topic_root + "/autogui")
            self._ha_publish(topic, payload)

    def publish_loop(self):
        """
        endless main publish loop
        """
        # endless publish loop
        self.unpublished = True
        loop_counter = 0
        try:
            while True:
                for topic_config in self.topic_config.values():
                    if "publish" in topic_config:
                        topic = f"{self.topic_root}/{topic_config['topic']}"
                        topic_config["publish"](topic, topic_config)
                # mark the topics as published
                self.unpublished = False
                # delay until next loo starts
                time.sleep(self.publish_delay)
                # call time time tick of chrome pages
                self.chrome_pages.tick()
                loop_counter += 1
                if loop_counter > self.full_publish_cycle:
                    loop_counter = 0
                    self.unpublished = True
                    self.chrome_pages.sync()
        except KeyboardInterrupt:
            LOG.warning( "Keyboard interrupt receiced. Stop client...")

def signal_term_handler( sig, frame ): # pylint: disable=unused-argument
    """
    Call back to handle OS SIGTERM signal to terminate client.
    """
    LOG.warning( "Received SIGTERM. Stop client...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_term_handler )

def display_client():
    """
    main function to start the client
    """
    mqtt_display_client = MqttDisplayClient(CONFIG_FILE)
    mqtt_display_client.connect()
    mqtt_display_client.ha_discover()
    mqtt_display_client.publish_loop()


if __name__ == "__main__":
    display_client()
