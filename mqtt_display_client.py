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
import json
import subprocess
import threading
import os
import signal
import sys

# used to validate URLs:
import validators
import gpiozero
from chrome_tab_api import ChromeTabAPI
from base_mqtt_client import base_mqtt_client as BMC

#
# global constants
#
CONFIG_FILE = "mqttDisplayClient.ini"  # name of the ini file
PANEL_DEFAULT = (
    "DEFAULT"  # keyword to set the website back to the configured FullPageOS default
)
PANEL_SHOW_URL = "URL"  # keyword to set website as panel set over url topic
PANEL_BLANK_URL = "about:blank"  # URL of the blank web page
PANEL_BLANK = "BLANK" #show a blank panel
IDLE = ">_"
LOG_ROTATE_WHEN='midnight'
LOG_BACKUP_COUNT=5
LOG_FILE_PATH="log"
LOG_FILE_NAME=None
LOG_FILE_HANDLER = None

# import from the configuration file only the feature configuraion
FEATURE_CFG = configparser.ConfigParser()

# try to open ini file
try:
    if os.path.exists(CONFIG_FILE) is True:
        FEATURE_CFG.read(CONFIG_FILE)
except OSError:
    print(f"Error while reading ini file: {CONFIG_FILE}")
    sys.exit()

# read features status
BACKLIGHT = False
if "backlight" in FEATURE_CFG["feature"]:
    if FEATURE_CFG["feature"]["backlight"].upper() == "ENABLED":
        BACKLIGHT = True

PYAUTOGUI = False
if "pyautogui" in FEATURE_CFG["feature"]:
    if FEATURE_CFG["feature"]["pyautogui"].upper() == "ENABLED":
        PYAUTOGUI = True

# import the functions zo control the display with autogui
if PYAUTOGUI:
    os.environ["DISPLAY"] = ":0"  # environment variable needed for pyautogui
    import pyautogui

    # local imports:
    from autogui_commands import call_autogui_cmd_list, autogui_log

#
# define main class
#
class MqttDisplayClient(BMC.BaseMqttClient): # pylint: disable=too-many-instance-attributes
    """
    Main class of MQTT display client for FullPageOS
    """
    def __init__(self, config_file):
        """
        Constructor takes config file as parameter (ini file) and defines global atrributes
        """
        # other global attributes
        self.default_url_file = None  # default FullPageOS config file for url
        self.display_id = None  # Touch display ID
        self.brightness = -1  # display brightness which was last published
        self.backlight = None  # backlight status
        self.backlight_published = None  # backlight status which was last published
        self.published_url = None  # url which was last published to broker
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
        self.chrome_topic = False

        # Global config:
        BMC.BaseMqttClient.__init__(self, config_file)

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
            self.log.warning("[chrome] section not specified in ini file! Default values used" )

        self.chrome_pages = ChromeTabAPI(
            self.publish_delay,
            self.chrome_port,
            (self.chrome_tab_timeout, self.chrome_reload_timeout)
        )
        self.chrome_pages.set_log(self.log_level, self.log_file_handler)
        self.chrome_pages.sync()
        self.chrome_pages.set_reload_callback( self.autogui_panel_cmds )

    def read_client_config(self, config):
        """
        Reads the configured ini file and sets attributes based on the config
        """
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
            "chrome": {"topic": "chrome", "publish": self._publish_chrome},
        }

        # read ini file values
        try:
            # set loglevel of autogui
            if PYAUTOGUI is True:
                autogui_log(self.log_level, self.log_file_handler) #pylint: disable=possibly-used-before-assignment

            # read server config
            self.display_id = config["global"]["displayID"]
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
            for key, cmd in config.items("shellCommands"):
                self.topic_config["shell"]["commands"][key.upper()] = cmd

            #create chrome Page class
            self.init_chrome_api(config)

            #check if special chrome topic should be enabled
            if 'chromeTopic' in config["logging"]:
                self.chrome_topic = config["logging"]["chromeTopic"]

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

        except (KeyError, RuntimeError) as error:
            self.log.error("Error while reading ini file: %s", error)
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
                    self.log.warning(
                        "FullPageOS default page has not a well formend URL format: %s",
                        self.default_url
                    )
            self.log.info("FullPageOS default page: %s", self.default_url)
        except OSError as error:
            self.log.error("Error while reading FullPageOS web page config: %s", error)
            sys.exit()

    def thread_autogui_func(self, cmds):
        """
        Thread which is executing a string with autogui commands
        """
        # excecute autogui commands with this website
        cmds = cmds.strip()
        feedback = call_autogui_cmd_list(cmds) # pylint: disable=possibly-used-before-assignment
        if feedback == "OK":
            self.log.info("Command list excecuted without error: '%s'",cmds)
        else:
            self.log.warning("Command list excecuted with error: '%s'", feedback)
        self.autogui_feedback = feedback

    def call_autogui_commands(self, cmds):
        """
        Starts a thread with is excecutiong autogui commands from a string
        parallel to the client.
        """
        if self.autogui_feedback[0 : len("EXEC")] == "EXEC":
            self.log.warning("Thread allready running can not excecute: '%s'",cmds)
            return
        self.autogui_feedback = "EXEC: " + cmds
        # create thread
        params = [cmds]
        thread = threading.Thread(target=self.thread_autogui_func, args=params)
        # run the thread
        thread.start()

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
            self.log.warning(
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
            self.log.warning("Error in brightness payload %s: %s", msg, error)
            return

        # call command to set the brightness
        self.log.debug("Call: %s",my_config["cmd"].format(value=value, displayID=self.display_id))
        err, msg = subprocess.getstatusoutput(
            my_config["cmd"].format(value=value, displayID=self.display_id)
        )
        if err != 0:
            self.log.error("Error %s executing command: %s", err, msg)

    def _set_backlight(self, my_config, msg):
        """
        mqtt command to switch the backlight on and off
        """
        if BACKLIGHT is False:
            # feature is switched off
            self.log.warning("Error backlight command received but feature is not enabled!")
            return
        # Synax OK we can call the command to set the backlight status
        msg = msg.strip()
        if msg.upper() == "ON" or msg.upper() == "OFF":
            value = my_config[msg]
        else:
            self.log.warning("Error in backlight payload: %s", msg)
            return

        # call command to set the backlight
        if msg != self.backlight:
            self.log.debug(my_config["cmd"].format(value=value, displayID=self.display_id))
            err, ret = subprocess.getstatusoutput(
                my_config["cmd"].format(value=value, displayID=self.display_id)
            )
            if err != 0:
                self.log.error("Error %s executing command: %s", err, ret)
            else:
                self.backlight = msg

    def thread_shell_cmd_func(self, cmd):
        """
        thread which executes a shell command in parallel to the client
        """
        # excecute system cmd
        err, msg = subprocess.getstatusoutput(cmd)
        if err != 0:
            self.log.error("Error %s executing command: %s", err, msg)
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
                self.log.warning("Shell command allready running skip: %s", msg)
                return
            # call the configured command
            self.log.debug("Call command: %s", my_config["commands"][msg])
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
            self.log.info("Unknown command payload received: '%s'", msg)

    def _set_url(self, my_config, msg): # pylint: disable=unused-argument
        """
        mqtt command to set an individual url
        """
        msg = msg.strip()
        if not validators.url(msg):
            self.log.info("Received url has no valid format: '%s'", msg)
            return

        # set the new url in browser:
        if self._set_website( msg ) is not True:
            self.log.warning("Received url could not be opened: '%s'", msg)
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
            self.log.info("Received panel name is not configured: '%s'", msg.upper())
            return

        # set the new url in browser:
        if self._set_website ( newsite ) is True:
            if self.autogui_commands is not None and PYAUTOGUI is True:
                self.call_autogui_commands(self.autogui_commands)
        else:
            self.log.error("Panel could not be activated: '%s'", msg.upper())

    def _set_autogui(self, my_config, msg): # pylint: disable=unused-argument
        """
        mqtt command to execute a list of autogui commands from a string
        """
        if PYAUTOGUI is True:
            self.call_autogui_commands(msg)

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
            self.log.debug("Send '%s' to topic %s", msg, topic)
        else:
            self.log.error("Failed to send message to topic %s", topic)

    def _publish_chrome(self, topic, my_config): # pylint: disable=unused-argument
        """
        publish the chrome topic
        """
        #check if chrome topic is enabled
        if self.chrome_topic is not True:
            return
        # collect system info
        chrome = {}
        active = self.chrome_pages.active()
        chrome ["active_id"] = active.id()
        chrome ["active_url"] = active.url()
        chrome ["reload"] = self.chrome_pages.focus_reload
        tabs = self.chrome_pages.tabs()
        chrome["tabs"] = {}
        for t_id, tab in tabs.items():
            jt = {}
            jt["url"] = tab.url()
            jt["timeout"] = self.chrome_pages.get_timeout(tab)
            chrome["tabs"][t_id] = jt
        # create a json out of it
        msg = json.dumps(chrome)
        # send message to broker
        result = self.client.publish(topic, msg)
        # result: [0, 1]
        status = result[0]
        if status == 0:
            self.log.debug("Send '%s' to topic %s", msg, topic)
        else:
            self.log.error("Failed to send message to topic %s", topic)

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
                    self.log.debug("Send '%s' to topic %s", msg, topic)
                    self.brightness = msg
                else:
                    self.log.error("Failed to send message to topic %s", topic)
        else:
            self.log.error("Error reading display brightness: %s", err)

    def _publish_shell_cmd(self, topic, my_config): # pylint: disable=unused-argument
        """
        publish the shell command topic
        """
        if self.shell_cmd != self.published_shell_cmd or self.unpublished is True:
            result = self.client.publish(topic, self.shell_cmd.capitalize())
            # result: [0, 1]
            status = result[0]
            if status == 0:
                self.log.debug("Send '%s' to topic %s", self.shell_cmd, topic)
                self.published_shell_cmd = self.shell_cmd
            else:
                self.log.error("Failed to send message to topic %s", topic)

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
                    self.log.debug("Send '%s' to topic %s", value, topic)
                    self.backlight = value
                    self.backlight_published = value
                else:
                    self.log.error("Failed to send message to topic %s", topic)
        else:
            self.log.error("Error reading display backlight status: %s", err)

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
                self.log.debug("Send '%s' to topic %s",current_url, topic)
                self.published_url = current_url
            else:
                self.log.error("Failed to send message to topic %s", topic)

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
                self.log.debug("Send '%s' to topic %s", self.current_panel, topic)
                self.current_panel_published = self.current_panel
            else:
                self.log.error("Failed to send message to topic %s", topic)

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
                    self.log.debug("Send '%s' to topic %s", self.autogui_feedback, topic)
                    self.autogui_feedback_published = self.autogui_feedback
                else:
                    self.log.error("Failed to send message to topic %s", topic)

    def ha_discover(self):
        """
        piblish all ropics needed for the home assistant mqtt discovery
        """
        # cpu temperature
        topic, payload = self.ha.sensor(
            "cpu temperature",
            self.topic_root + "/system",
            "cpu_temp",
            "temperature",
            "°C",
            icon="cpu-64-bit"
        )
        self.ha_publish(topic, payload)

        # chrome tabs
        topic, payload = self.ha.sensor("Active chrome tabs",
                                   self.topic_root + "/system",
                                   "chrome_tabs",
                                   icon="monitor-dashboard"
                                   )
        self.ha_publish(topic, payload)

        # cpu load
        topic, payload = self.ha.sensor("cpu load",
                                   self.topic_root + "/system",
                                   "cpu_load",
                                   icon="cpu-64-bit"
                                   )
        self.ha_publish(topic, payload)

        # disk usage
        topic, payload = self.ha.sensor(
            "disk usage", self.topic_root + "/system", "disk_usage", icon="harddisk", unit="%"
        )
        self.ha_publish(topic, payload)

        # url
        topic, payload = self.ha.text("URL", self.topic_root + "/url")
        self.ha_publish(topic, payload)

        # panel select
        options = list(self.topic_config["panel"]["panels"])
        for i, option in enumerate(options):
            options[i] = option.capitalize()
        topic, payload = self.ha.select("Panel", self.topic_root + "/panel", options)
        self.ha_publish(topic, payload)

        # shell commands
        options = [IDLE] + list(self.topic_config["shell"]["commands"].keys())
        for i, option in enumerate(options):
            options[i] = option.capitalize()
        topic, payload = self.ha.select("shell command", self.topic_root + "/shell", options)
        self.ha_publish(topic, payload)

        if BACKLIGHT is True:
            # backlight "light"
            topic, payload = self.ha.light(
                "backlight",
                self.topic_root + "/backlight",
                self.topic_root + "/brightness_percent",
            )
            self.ha_publish(topic, payload)

        if PYAUTOGUI is True:
            # mouse x position
            topic, payload = self.ha.sensor(
                "Mouse X Pos", self.topic_root + "/system", "mouse_position[0]", icon="mouse"
            )
            self.ha_publish(topic, payload)
            # mouse y position
            topic, payload = self.ha.sensor(
                "Mouse Y Pos", self.topic_root + "/system", "mouse_position[1]", icon="mouse"
            )
            self.ha_publish(topic, payload)
            # autogui command string
            topic, payload = self.ha.text("AutoGUI command", self.topic_root + "/autogui")
            self.ha_publish(topic, payload)

    def publish_loop_callback(self):
        """
        add this to endless main publish loop
        """
        # call time time tick of chrome pages
        self.chrome_pages.tick()

def display_client():
    """
    main function to start the client
    """
    client = MqttDisplayClient(CONFIG_FILE)
    client.connect()
    client.ha_discover()
    client.publish_loop()
    return client

def signal_term_handler( sig, frame ): # pylint: disable=unused-argument
    """
    Call back to handle OS SIGTERM signal to terminate client.
    """
    CLIENT.log.warning( "Received SIGTERM. Stop client...") # pylint: disable=possibly-used-before-assignment
    sys.exit(0)

if __name__ == "__main__":
    CLIENT = display_client()
    signal.signal(signal.SIGTERM, signal_term_handler )
