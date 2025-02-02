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
"""Module implements a class to control the tabs of google chrome
over the DevTools API
"""

import json
import logging
import subprocess
import requests
from websockets.sync.client import connect

#
# global constants
#
REQ_TIMEOUT = 4 #wait 4 seconds for requests
CMD_CHROMIUM = "chromium "


class DevToolsAPI:
    """Class to make API websocket calls"""

    def __init__(self, api_id, domain):
        """Create DevTools interface for a specific domain"""
        self._id = api_id
        self._domain = domain + "."

    def call_api(self, adr, command, params):
        """Makes an websocket api call"""
        payload = {}
        payload["id"] = self._id
        payload["method"] = self._domain + command
        payload["params"] = params
        payload = json.dumps(payload)

        with connect(adr) as ws:
            ws.send(payload)
            r = ws.recv()
            return r

    def set_id( self, api_id ):
        """Set API ID"""
        self._id = api_id

    def set_domain( self, domain ):
        """Set domain"""
        self._domain = domain+"."

class ChromeTab:
    """
    implements a class to access chrome tab dictionarys
    """

    def __init__(self, tab):
        """Create class data"""
        self.t = tab
        self.api = DevToolsAPI(2, "Page")

    def id(self):
        """retuns the tab id"""
        return self.t["id"]

    def url(self):
        """retuns the tab id"""
        return self.t["url"]

    def ws_url(self):
        """retuns the websocket debug url"""
        return self.t["webSocketDebuggerUrl"]

    def navigate(self, url):
        """Navigate to a new url"""
        params = {}
        params["url"] = url
        self.api.call_api(self.ws_url(), "navigate", params)

    def bring_to_front(self):
        """Navigate to a new url"""
        params = {}
        self.api.call_api(self.ws_url(), "bringToFront", params)

    def reload(self, ignore_cache=False):
        """Navigate to a new url"""
        params = {}
        params["ignoreCache"] = ignore_cache
        self.api.call_api(self.ws_url(), "reload", params)


class ChromeTabAPI: #pylint: disable=too-many-instance-attributes
    """
    Implements methods to control the tabs of google chrome of the DevTools API
    """

    def __init__(
        self,
        time_tick=1,
        port=9222,
        timeouts=(0, 0),
        host="http://localhost:"
    ):
        """Create class default values"""
        self.time_tick = time_tick
        self.port = port
        self.page_timeout = timeouts[0]
        self.reload_timeout = timeouts[1]
        self.host = host + str(port)
        self.clear_registry()
        self.focus_tab = None
        self.focus_reload = 0
        self.reload_callback = None
        self.sync_error = False
        #
        # initialize logger
        #
        self.log = logging.getLogger("ChromeTabApi")
        logging.basicConfig()

    def set_reload_callback(self, callback):
        """Set a callback which is called on relad page"""
        self.reload_callback = callback

    def set_log(self, level, handler):
        """configure logger"""
        self.log.setLevel(level)
        self.log.addHandler(handler)

    def tab_count(self):
        """Return number of tabs in registry"""
        return len(self.tabs_by_id)

    def active_url( self ):
        """retuns the url of the tab in focus"""
        if self.focus_tab is not None:
            return self.focus_tab.url()
        return "Error!"

    def close_tab(self, tab):
        """Close a tab in chrome"""
        api_url = self.host + "/json/close/"
        try:
            r = requests.get(api_url + tab.id(), timeout=REQ_TIMEOUT)
        except requests.exceptions.RequestException as error:
            self.log.warning("Request error to chrome api: %s", error)
            return False

        if r.status_code == 200:
            self.log.info("Close Tab: %s", tab.url())
            return True
        self.log.info("Could not close tab: %d", r.status_code)
        return False

    def new_tab(self, url):
        """Opens a new tab"""
        #api_url = self.host + "/json/new?"
        #try:
        #    r = requests.put(api_url + url, timeout=REQ_TIMEOUT)
        #except (TimeoutError, RuntimeError):
        #    self.log.warning("Request timeout to chrome api!")
        #    return False
        #if r.status_code == 200:
        #    self.sync()
        #    return True
        #self.log.info("Could not open new tab: %d", r.status_code)
        #return False
        err, msg = subprocess.getstatusoutput( CMD_CHROMIUM + url)
        if err != 0:
            self.log.error("Error %s executing command: %s", err, msg)
            return False
        self.sync()
        return True

    def bring_to_front(self, tab):
        """Close a tab in chrome"""
        api_url = self.host + "/json/activate/"
        try:
            r = requests.get(api_url + tab.id(), timeout=REQ_TIMEOUT)
        except requests.exceptions.RequestException as error:
            self.log.warning("Request error to chrome api: %s", error)
            return False
        if r.status_code == 200:
            self.log.info("Tab in focus now: %s", tab.url())
            self.sync()
            return True
        self.log.info("Could not put tab in focus: %d", r.status_code)
        return False

    def activate_tab(self, url):
        """Check if a tab with this url exist already
        if yes put it in the front
        if no open a new one with this url
        """
        self.log.info("Activate tab with url: %s", url)
        tab = self.get_tab_by_url(url)
        if tab is not None:
            self.log.info("Tab with this url exists, bring it to the front: %s", tab.url())
            return self.bring_to_front(tab)
        self.log.info("No tab with this url exists, create new tab: %s", url)
        return self.new_tab(url)

    def clear_registry(self):
        """Clear complete tab registry"""
        self.focus_tab = None
        self.tabs_by_url = {}  # dictionarey with tabs. Key: url, Value id
        self.tabs_by_id = {}  # dictionary with tabs. Key: id, Value: chrome tab
        self.tabs_life_counters = (
            {}
        )  # dictionary with tab life time: Key: Id; Value: Counter (seconds)

    def register_tab(self, tab):
        """Puts a new tab to the dictionaries"""
        self.tabs_by_url[tab.url()] = tab.id()
        self.tabs_by_id[tab.id()] = tab
        self.tabs_life_counters[tab.id()] = self.page_timeout

    def deregister_tab(self, tab):
        """Removes a new tab from the dictionaries"""
        if tab.id() in self.tabs_by_id:
            old_url = self.tabs_by_id[tab.id()].url()
            del self.tabs_by_id[tab.id()]
            del self.tabs_life_counters[tab.id()]
            if old_url in self.tabs_by_url:
                del self.tabs_by_url[old_url]

    def get_tab_by_url(self, url):
        """returns the tab by url from registry"""
        if url in self.tabs_by_url:
            return self.tabs_by_id[self.tabs_by_url[url]]
        return None

    def tab_registered(self, tab):
        """Check if a tab with this id is already registered"""
        if tab.id() in self.tabs_by_id:
            return True
        return False

    def url_registered(self, tab):
        """Check if a tab with this url is already registered"""
        if tab.url() in self.tabs_by_url:
            return True
        return False

    def same_url_registered(self, tab):
        """Check if this tab is registered with the same url"""
        if self.tab_registered(tab):
            if tab.url() == self.tabs_by_id[tab.id()].url():
                return True
        return False

    def set_focus_tab( self, tab ):
        """Defines tha given tab as in focus"""
        if self.focus_tab is not None:
            if self.focus_tab.id() != tab.id():
                self.focus_tab = tab
                self.focus_reload = self.reload_timeout
                self.log.info("Page in focus: %s", tab.url())
        else:
            self.log.info("New page in focus: %s", tab.url())
            self.focus_tab = tab
            self.focus_reload = self.reload_timeout

    def sync(self):
        """
        synchronize the current status of tabs with chrome
        """
        api_url = self.host + "/json"
        try:
            r = requests.get(api_url, timeout=REQ_TIMEOUT)
        except requests.exceptions.RequestException as error:
            self.log.error("Request error to chrome api: %s", error)
            self.sync_error = True
            return False

        if r.status_code == 200:
            tabs = r.json()
            if len(tabs) > 0:
                # first tab in list is currently shown on top. Is focus changed?
                self.set_focus_tab(ChromeTab(tabs[0]))
                for tab in tabs:
                    tab = ChromeTab(tab)
                    if self.tab_registered(tab):
                        # this tab is already registered. With same url?
                        if self.same_url_registered(tab):
                            # same url => nothing to do
                            self.log.debug("Tab already registered: %s", tab.url())
                            continue
                        # tab had previously a different url.
                        # Is the new url already in dicts for another tab?
                        if self.url_registered(tab):
                            # there is another tab with this url
                            # => dublicated tab => Can be closed
                            self.close_tab(tab)
                            self.log.info(
                                "Tab url changed. Now dublicate url. Close Tab: %s",
                                tab.url(),
                            )
                        else:
                            # register as tab new
                            self.register_tab(tab)
                            self.log.info(
                                "Tab url changed. Register new: %s", tab.url()
                            )
                    else:
                        # new tab found. Is a tab with the url already in dicts?
                        if self.url_registered(tab):
                            # there is another tab with this url => dublicated url => Can be closed
                            self.close_tab(tab)
                            self.log.info(
                                "Tab with same url exist. Close tab: %s", tab.url()
                            )
                        else:
                            # new url => Register tab
                            self.register_tab(tab)
                            self.log.info(
                                "New tab with new url. Register tab: %s", tab.url()
                            )
            else:
                # No open tabs returned
                self.clear_registry()
                self.log.warning("No tabs returnd by chrome!!")

            #sync complete!
            self.sync_error = False
            return True
        self.log.error("Sync request failed. status code = %d", r.status_code)
        self.sync_error = True
        return False

    def tick(self):
        """Check lifetime of tabs in background. And reload cycle of tab in foreground"""
        if self.sync_error is True:
            #make retry
            self.log.debug("Retry sync with chrome!!")
            self.sync()
            if self.sync_error is True:
                self.log.error("Still chrome sync error!!")
                #Stil no connection to chrome
                return
            self.log.debug("Sync did work now. Chrome is connected")

        if self.page_timeout > 0:
            # timeout function is active
            tabs_to_be_closed = []
            for tab_id, counter in self.tabs_life_counters.items():
                # do not check lifetime of tab in focus
                if tab_id != self.focus_tab.id():
                    counter -= self.time_tick
                    if counter <= 0:
                        tab = self.tabs_by_id[tab_id]
                        tabs_to_be_closed.append(tab)
                    else:
                        self.tabs_life_counters[tab_id] = counter
            #close all tabs with timeout:
            for tab in tabs_to_be_closed:
                self.log.info("Close tab in background: %s", tab.url())
                self.deregister_tab(tab)
                self.close_tab(tab)

        if self.reload_timeout > 0:
            self.focus_reload -= self.time_tick
            if self.focus_reload <= 0:
                self.log.info("Reload tab in foreground: %s", self.focus_tab.url())
                self.focus_tab.reload(True)
                if self.reload_callback is not None:
                    self.reload_callback()
                self.focus_reload = self.reload_timeout
