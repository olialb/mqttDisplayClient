# python
# because of smbus usage:
# pylint: disable=c-extension-no-member
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
Module implements a base class for MQTT clients based on paho.mqtt
"""

import configparser
import logging
import logging.handlers
import os
import sys
import time
from paho.mqtt import client as mqtt_client
from base_mqtt_client import ha_discover as HA

#
# global constants
#
LOG_FILE_PATH = "log"
LOG_FILE_NAME = None
LOG_FILE_HANDLER = None
LOG_ROTATE_WHEN = "midnight"
LOG_BACKUP_COUNT = 5
MANUFACTURER = "githab olialb"
MODEL = "FullPageOS"

#
# class definitions
#
class BaseMqttClient: #pylint: ...disable=too-many-instance-attributes
    """Implements a base classe for an mqtt client based on paho-mqtt"""
    def __init__(self, config_file):
        """
        Constructor takes config file as parameter (ini file) and defines global atrributes
        """
        # Global config:
        self.config_file = config_file

        # other global attributes
        self.reconnect_delay = 5  # retry in seconds to try to reconnect mgtt broker
        self.publish_delay = 3  # delay between two publish loops in seconds
        self.full_publish_cycle = 20  # Every publishcycle*fullPublishCycle
        self.topic_root = None  # Root path for all topics
        self.unpublished = True  # set to true if the topics are not published yet
        self.client = None  # mqtt client

        # broker config:
        self.broker = None
        self.port = 1883
        self.username = ""
        self.password = ""

        # initialize logger
        self.log = logging.getLogger("MQTTClient")
        self.log_level = None
        self.log_file_handler = None
        logging.basicConfig()

        # topic configuration
        self.topic_config = None

        #ha discovery configuration
        self.manufacturer = MANUFACTURER
        self.model = MODEL

        #read ini file
        self.read_config_file()

        #create ha discovery class
        self.ha = HA.HADiscovery(self.ha_device_name, self.ha_base, self.manufacturer, self.model)

    def read_logging_config(self, config):
        """Read logging config from ini file"""
        self.log_level = config["logging"]["level"]
        if self.log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            self.log.setLevel(self.log_level.upper())
        else:
            raise KeyError(self.log_level)

        #set default values
        log_file_path = LOG_FILE_PATH
        log_file_name = LOG_FILE_NAME
        log_file_backup = LOG_BACKUP_COUNT
        log_file_rotate = LOG_ROTATE_WHEN

        if "path" in config["logging"]:
            log_file_path = config["logging"]["path"]
        if "file" in config["logging"]:
            log_file_name = config["logging"]["file"]
        if "backup" in config["logging"]:
            log_file_backup = config["logging"]["backup"]
        if "rotate" in config["logging"]:
            log_file_rotate = config["logging"]["rotate"]

        if log_file_name is not None and log_file_name != "":
            #create log file path and file logger
            try:
                os.makedirs(log_file_path)
                self.log.debug("Logging directory created: ./%s", log_file_path)

                # create time rotating logger for log files
                self.log_file_handler = logging.handlers.TimedRotatingFileHandler(
                    os.path.join(log_file_path, log_file_name),
                    when=log_file_rotate,
                    backupCount=log_file_backup
                )
                # Set the formatter for the logging handler
                self.log_file_handler.setFormatter(
                    logging.Formatter("%(asctime)s-%(name)s-%(levelname)s-%(message)s")
                )
                self.log.addHandler(self.log_file_handler)
            except FileExistsError:
                self.log.info("Logging directory exist already: ./%s", log_file_path)
            except OSError:
                self.log.error("Can not create Logging directory: ./%s", log_file_path)

    def read_config_file(self):
        """
        Reads the configured ini file and sets attributes based on the config
        and set up the logger and broker data
        """
        # read ini file
        config = configparser.ConfigParser()

        # try to open ini file
        try:
            if os.path.exists(self.config_file) is False:
                self.log.critical("Config file not found '%s'!", self.config_file)
            else:
                config.read(self.config_file)
        except OSError:
            self.log.error("Error while reading ini file: %s", self.config_file)
            sys.exit()

        # read ini file values
        try:
            # read logging config
            self.read_logging_config(config)

            # read broker config
            self.broker = config["global"]["broker"]
            self.port = int(config["global"]["port"])
            self.username = config["global"]["username"]
            self.password = config["global"]["password"]
            self.topic_root = (
                config["global"]["topicRoot"] + "/" + config["global"]["deviceName"]
            )
            self.reconnect_delay = int(config["global"]["reconnectDelay"])
            self.publish_delay = int(config["global"]["publishDelay"])
            self.full_publish_cycle = int(config["global"]["fullPublishCycle"])

            # read config HADiscovery
            self.ha_dc = False
            if "haDiscover" in config["feature"]:
                if config["feature"]["haDiscover"].upper() == "ENABLED":
                    self.ha_dc = True
            self.ha_device_name = config["haDiscover"]["deviceName"]
            self.ha_base = config["haDiscover"]["base"]
            if "model" in config["haDiscover"]:
                self.model = config["haDiscover"]["model"]
            if "manufacturer" in config["haDiscover"]:
                self.manufacturer = config["haDiscover"]["manufacturer"]

            #call call back for addition config data
            self.read_client_config( config )

        except KeyError as inst:
            self.log.error("Error while reading ini file: %s", inst)
            sys.exit()

    def read_client_config( self, config):
        """This method can be overwritten to read more config data from ini file"""

    @classmethod
    def on_connect(cls, client, inst, flags, rc, properties): #pylint: disable=too-many-arguments,too-many-positional-arguments,unused-argument
        """Method called on connect to broker"""
        if rc == 0:
            inst.log.info("Connected to MQTT Broker!")
            # make the subscritions at the broker
            inst.subscribe()
        else:
            inst.log.warning("Failed to connect, return code %s", rc)

    @classmethod
    def on_disconnect(cls, client, inst, flags, rc, properties): #pylint: disable=too-many-arguments,too-many-positional-arguments,unused-argument
        """Method called on disconnect from broker"""
        inst.log.info("Disconnected with result code: %s", rc)
        inst.unpublished = True
        inst.brightness = -1
        while True:
            inst.log.info("Reconnecting in %s seconds...", inst.reconnect_delay)
            time.sleep(inst.reconnect_delay)

            try:
                client.reconnect()
                inst.log.info("Reconnected successfully!")
                return
            except OSError as err:
                inst.log.warning("%s. Reconnect failed. Retrying...", err)

    @classmethod
    def on_message(cls, client, inst, msg):  # pylint: disable=unused-argument
        """
        method is called when the cleint receives a message from the broker
        """
        inst.log.info(
            "Received `%s` from `%s` topic", msg.payload.decode().strip(), msg.topic
        )

        # check received topic syntax
        if msg.topic[0 : len(inst.topic_root)] == inst.topic_root:
            topic = msg.topic[len(inst.topic_root) : len(msg.topic)]
            topic = topic.split("/")
            if topic[2] != "set":
                inst.log.info("Wrong topic syntax received from broker %s", msg.topic)
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
                    inst.log.info(
                        "Command for topic without command received from broker %s",
                        msg.topic,
                    )
            else:
                inst.log.info("Command for unknown topic received from broker %s", msg.topic)
        else:
            inst.log.info("Wrong topic syntax received from broker %s", msg.topic)

    def connect(self) -> mqtt_client:
        """
        Method to connect to the mqtt broker
        """
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        if self.username != "":
            self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = BaseMqttClient.on_connect
        self.client.on_disconnect = BaseMqttClient.on_disconnect
        while True:
            try:
                self.client.connect(self.broker, self.port)
            except OSError as error:
                self.log.warning(
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

    def subscribe(self):
        """
        method to subscribe to all the configured topics at the broker
        """
        # Subscribe to all configured topics
        for topic_config in self.topic_config.values():
            if "topic" in topic_config:
                topic = self.topic_root + f"/{topic_config['topic']}/set"
                self.client.subscribe(topic)
                self.log.debug("Subscribe to: %s", topic)
        self.client.on_message = BaseMqttClient.on_message

    def ha_publish(self, topic, payload):
        """Publish ha discovery topics"""
        if self.ha_dc is True:
            # publish new entity
            result = self.client.publish(topic, payload, retain=True)
        else:
            # delete entity
            result = self.client.publish(topic, "", retain=True)
        status = result[0]
        if status == 0:
            self.log.debug("Send '%s' to topic %s", payload, topic)
        else:
            self.log.error("Failed to send message to topic %s", topic)

    def ha_discover(self):
        """
        publish all topics needed for the home assistant mqtt discovery
        this method must be implemented by the child class
        """

    def publish_loop_callback(self):
        """
        This call back is called by publish loop and can be overwritten by child class
        """

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
                # call publish loop call back to allow child class to add additional cyclic stuff
                self.publish_loop_callback()
                # call time time tick of chrome pages
                loop_counter += 1
                if loop_counter > self.full_publish_cycle:
                    loop_counter = 0
                    self.unpublished = True
        except KeyboardInterrupt:
            self.log.warning("Keyboard interrupt receiced. Stop client...")
