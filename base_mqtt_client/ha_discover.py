# python
#
# This file is part of the mqttDisplayClient distribution:
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
"""Module implements a class for home assistant discovery content
in  mqtt topics
"""

import uuid
import json
import os

#File to store the home assistant discovery uid
UUID_FILE = ".ha_uuid"

#
# this file defines everthing whats needed to publish
# the topics for homeassitant device discovery
#


class HADiscovery:
    """Implements methods to create content for home assitant
    auto discovery mqtt topics"""

    def __init__(
        self,
        device_name="MyDevice",
        base="homeassitant",
        manufacturer="MyCompany",
        model="MyModel",
    ):
        """Create class default values"""
        if os.path.isfile(UUID_FILE):
            with open(UUID_FILE, "r", encoding="utf-8") as f:
                self.uid = str(f.read()).strip()
        else:
            self.uid = "_" + str(hex(uuid.getnode())).replace("0x", "") + "_"
            with open(UUID_FILE, "w", encoding="utf-8") as f:
                f.write(self.uid)
        self.device_name = device_name
        self.base = base
        self.manufacturer = manufacturer
        self.model = model

    def device(self):
        """json content of a device"""
        js = {}
        js["name"] = self.device_name
        js["identifiers"] = self.device_name + "_" + self.uid
        js["manufacturer"] = self.manufacturer
        js["model"] = self.model
        return js

    def sensor( # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        name,
        state_topic,
        value_template=None,
        device_class=None,
        unit=None,
        icon=None
    ):
        """json content of a sensor"""
        uid = self.uid
        topic = self.base + "/sensor/" + uid + "/" + name.replace(" ", "_") + "/config"
        js = {}
        js["name"] = name
        js["unique_id"] = self.uid + "_" + name.replace(" ", "_")
        js["state_topic"] = state_topic
        if unit is not None:
            js["unit_of_measurement"] = unit
        if value_template is not None:
            js["value_template"] = "{{ value_json." + value_template + " }}"
        if device_class is not None:
            js["device_class"] = device_class
        if icon is not None:
            js['icon'] = "mdi:"+icon
        js["device"] = self.device()
        return topic, json.dumps(js)

    def switch(self, name, state_topic, value_template=None):
        """json content of a switch"""
        uid = self.uid
        topic = self.base + "/switch/" + uid + "/" + name.replace(" ", "_") + "/config"
        js = {}
        js["name"] = name
        js["unique_id"] = self.uid + "_" + name.replace(" ", "_")
        js["command_topic"] = state_topic + "/set"
        js["state_topic"] = state_topic
        js["payload_on"] = "ON"
        js["payload_off"] = "OFF"
        js["state_on"] = "ON"
        js["state_off"] = "OFF"
        if value_template is not None:
            js["value_template"] = "{{ value_json." + value_template + " }}"
        js["device"] = self.device()
        return topic, json.dumps(js)

    def text(self, name, state_topic, value_template=None):
        """json content of a text entity"""
        uid = self.uid
        topic = self.base + "/text/" + uid + "/" + name.replace(" ", "_") + "/config"
        js = {}
        js["name"] = name
        js["unique_id"] = self.uid + "_" + name.replace(" ", "_")
        js["command_topic"] = state_topic + "/set"
        js["state_topic"] = state_topic
        if value_template is not None:
            js["value_template"] = "{{ value_json." + value_template + " }}"
        js["device"] = self.device()
        return topic, json.dumps(js)

    def select(self, name, state_topic, options, value_template=None):
        """json content of a select entity"""
        uid = self.uid
        topic = self.base + "/select/" + uid + "/" + name.replace(" ", "_") + "/config"
        js = {}
        js["name"] = name
        js["unique_id"] = self.uid + "_" + name.replace(" ", "_")
        js["command_topic"] = state_topic + "/set"
        js["state_topic"] = state_topic
        js["options"] = options
        if value_template is not None:
            js["value_template"] = "{{ value_json." + value_template + " }}"
        js["device"] = self.device()
        return topic, json.dumps(js)

    def light( # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        name,
        state_topic,
        brightness_topic,
        value_template_state=None,
        value_tmpl_brightness=None,
        brightness_scale=100,
    ):
        """json content of a light"""
        uid = self.uid
        topic = self.base + "/light/" + uid + "/" + name.replace(" ", "_") + "/config"
        js = {}
        js["name"] = name
        js["unique_id"] = self.uid + "_" + name.replace(" ", "_")
        js["command_topic"] = state_topic + "/set"
        js["state_topic"] = state_topic
        js["payload_on"] = "ON"
        js["payload_off"] = "OFF"
        js["state_on"] = "ON"
        js["state_off"] = "OFF"
        js["brightness_scale"] = brightness_scale
        js["brightness_command_topic"] = brightness_topic + "/set"
        js["brightness_state_topic"] = brightness_topic
        if value_template_state is not None:
            js["state_value_template"] = "{{ value_json." + value_template_state + " }}"
        if value_tmpl_brightness is not None:
            js["brightness_value_template"] = (
                "{{ value_json." + value_tmpl_brightness + " }}"
            )
        js["device"] = self.device()
        return topic, json.dumps(js)
