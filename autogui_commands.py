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
"""
Module implements helper functions to execute autogui commands from a command sting
Format: cmd1(x,y);cmd2(z)...
"""

import time
import logging
import os

os.environ["DISPLAY"] = ":0"  # environment variable needed for pyautogui
import pyautogui  # pylint: disable=wrong-import-position

# switch off Fail Safe
# pydirectinput.FAILSAFE = False
pyautogui.FAILSAFE = False

#
# initialize logger
#
LOG = logging.getLogger("AutoGUICommands")
logging.basicConfig()


def autogui_log(level, handler):
    """
    set the log level of the module
    """
    LOG.setLevel(level)
    LOG.addHandler( handler )


#########################
# Parameter interpreters:
#########################


def ag_par_string(s):
    """
    Check a string paramter: "string" or 'string'
    """
    # check string parameter

    s.strip()
    if s[0] == '"' and s[-1] == '"':
        return "OK", s[1:-1]
    if s[0] == "'" and s[-1] == "'":
        return "OK", s[1:-1]
    err = f"Error in string parameter. No quotes: {s}"
    LOG.debug(err)
    return err, s


def ag_par_x(s):
    """
    Check a single integer parameter
    """
    # interpret x paramater
    err = "OK"
    x = 0
    try:
        x = int(s)
    except ValueError as error:
        err = f"Error in parameter syntax: {error}"
        LOG.debug(err)
    return err, x


def ag_par_xy(s):
    """
    Check two integer parameters
    """
    # interpret x,y paramater
    coordinates = s.split(",")
    err = "OK"
    x = 0
    y = 0
    if len(coordinates) == 2:
        try:
            x = int(coordinates[0])
            y = int(coordinates[1])
        except ValueError as error:
            err = f"Error in parameter syntax: {error}"
            LOG.debug(err)
    else:
        err = f"Error in parameter syntax: {s}"
        LOG.debug(err)
    return err, x, y


#########################
# Parameter interpreters:
#########################


def ag_cmd_key(func, cmd, s):
    """
    Call an autogui function with string as keyboard key as parameter
    """
    # calls pyautogui function with parameter (x)
    err, s = ag_par_string(s)
    s = s.strip()
    if err == "OK":
        if s not in pyautogui.KEYBOARD_KEYS:
            err = f"Parameter not in KEYBOARD_KEYS: {s}"
            LOG.debug(err)
        else:
            try:
                func(s)
            except Exception as error: # pylint: disable=broad-exception-caught
                err = f"Error calling pyautogui.{cmd} with ({s}): {error}"
                LOG.debug(err)
    return err


def ag_cmd_string(func, cmd, s):
    """
    Call an autogui function with string as parameter
    """
    # calls pyautogui function with parameter (x)
    err, s = ag_par_string(s)
    if err == "OK":
        try:
            func(s)
        except Exception as error: # pylint: disable=broad-exception-caught
            err = f"Error calling pyautogui.{cmd} with ({s}): {error}"
            LOG.debug(err)
    return err


def ag_cmd_x(func, cmd, s):
    """
    Call an autogui function with integer as parameter
    """
    # calls pyautogui function with parameter (x)
    err, x = ag_par_x(s)
    if err == "OK":
        try:
            func(x)
        except Exception as error: # pylint: disable=broad-exception-caught
            err = f"Error calling pyautogui.{cmd} with ({x}): {error}"
            LOG.debug(err)
    return err


def ag_cmd_ms(func, cmd, s):
    """
    Call an autogui function with milli seconds as parameter
    """
    # calls pyautogui function with parameter (x)/1000
    err, x = ag_par_x(s)
    if err == "OK":
        try:
            x = float(x) / 1000
            func(x)
        except Exception as error: # pylint: disable=broad-exception-caught
            err = f"Error calling pyautogui.{cmd} with ({x}): {error}"
            LOG.debug(err)
    return err


def ag_cmd_xy(func, cmd, s):
    """
    Call an autogui function with two integers as parameter
    """
    # calls pyautogui function with parameter (x,y)
    err, x, y = ag_par_xy(s)
    if err == "OK":
        try:
            func(x, y)
        except Exception as error: # pylint: disable=broad-exception-caught
            err = f"Error calling pyautogui.{cmd} with ({x},{y}): {error}"
            LOG.debug(err)
    return err


def ag_cmd_xy_right(func, cmd, s):
    """
    Call an autogui function with two integers as parameters (right mouse button)
    """
    # calls pyautogui function with parameter (x,y)
    err, x, y = ag_par_xy(s)
    if err == "OK":
        try:
            func(x, y, button="right")
        except Exception as error: # pylint: disable=broad-exception-caught
            err = f"Error calling pyautogui.{cmd} with ({x},{y},button='right'): {error}"
            LOG.debug(err)
    return err


def ag_cmd_xy_middle(func, cmd, s):
    """
    Call an autogui function with two integers as parameters (middle mouse button)
    """
    # calls pyautogui function with parameter (x,y)
    err, x, y = ag_par_xy(s)
    if err == "OK":
        try:
            func(x, y, button="middle")
        except Exception as error: # pylint: disable=broad-exception-caught
            err = (
                f"Error calling pyautogui.{cmd} with ({x},{y},button='middle'): {error}"
            )
            LOG.debug(err)
    return err


def ag_cmd(func, cmd):
    """
    Call an autogui function withou any parameter
    """
    # calls pyautogui function withour parameter
    err = "OK"
    try:
        func()
    except Exception as error: # pylint: disable=broad-exception-caught
        err = f"Error calling pyautogui.{cmd}: {error}"
        LOG.debug(err)
    return err


def ag_cmd_right(func, cmd):
    """
    Call an autogui function without parameter (right mouse button)
    """
    # calls pyautogui function withour parameter
    err = "OK"
    try:
        func(button="right")
    except Exception as error: # pylint: disable=broad-exception-caught
        err = f"Error calling pyautogui.{cmd}: {error}"
        LOG.debug(err)
    return err


def ag_cmd_middle(func, cmd):
    """
    Call an autogui function without parameter (middle mouse button)
    """
    # calls pyautogui function withour parameter
    err = "OK"
    try:
        func(button="middle")
    except Exception as error: # pylint: disable=broad-exception-caught
        err = f"Error calling pyautogui.{cmd}: {error}"
        LOG.debug(err)
    return err


#########################
# Command dispacher
#########################

# dictionary with command with parameters
commandsWithPar = {
    "click": {"interpreter": ag_cmd_xy, "autogui": pyautogui.click},
    "clickright": {"interpreter": ag_cmd_xy_right, "autogui": pyautogui.click},
    "clickmiddle": {"interpreter": ag_cmd_xy_middle, "autogui": pyautogui.click},
    "moveto": {"interpreter": ag_cmd_xy, "autogui": pyautogui.moveTo},
    "move": {"interpreter": ag_cmd_xy, "autogui": pyautogui.move},
    "dragto": {"interpreter": ag_cmd_xy, "autogui": pyautogui.dragTo},
    "dragtoright": {"interpreter": ag_cmd_xy_right, "autogui": pyautogui.dragTo},
    "dragtomiddle": {"interpreter": ag_cmd_xy_middle, "autogui": pyautogui.dragTo},
    "scroll": {"interpreter": ag_cmd_x, "autogui": pyautogui.scroll},
    "hscroll": {"interpreter": ag_cmd_x, "autogui": pyautogui.hscroll},
    "wait": {"interpreter": ag_cmd_ms, "autogui": time.sleep},
    "write": {"interpreter": ag_cmd_string, "autogui": pyautogui.write},
    "press": {"interpreter": ag_cmd_key, "autogui": pyautogui.press},
    "keydown": {"interpreter": ag_cmd_key, "autogui": pyautogui.keyDown},
}

# list of commads without parameters
commands = {
    "click": {"interpreter": ag_cmd, "autogui": pyautogui.click},
    "doubleclick": {"interpreter": ag_cmd, "autogui": pyautogui.doubleClick},
    "clickright": {"interpreter": ag_cmd_right, "autogui": pyautogui.click},
    "clickmiddle": {"interpreter": ag_cmd_middle, "autogui": pyautogui.click},
    "mousedown": {"interpreter": ag_cmd, "autogui": pyautogui.mouseDown},
    "mousedownright": {"interpreter": ag_cmd_right, "autogui": pyautogui.mouseDown},
    "mousedownmiddle": {"interpreter": ag_cmd_middle, "autogui": pyautogui.mouseDown},
    "mouseup": {"interpreter": ag_cmd, "autogui": pyautogui.mouseUp},
    "mouseupright": {"interpreter": ag_cmd_right, "autogui": pyautogui.mouseUp},
    "mouseupmiddle": {"interpreter": ag_cmd_middle, "autogui": pyautogui.mouseUp},
}


def call_autogui(cmd, params):
    """
    Call a single autogui command
    """
    # functions interpreter for autogui commands
    cmd = cmd.strip().lower()
    if len(params) > 0:
        # its a command with parameter
        if cmd in commandsWithPar:
            return commandsWithPar[cmd]["interpreter"](
                commandsWithPar[cmd]["autogui"], cmd, params.strip()
            )
        return f"Unknown command: '{cmd}({params})'"
    # its a command without parameter
    if cmd in commands:
        return commands[cmd]["interpreter"](commands[cmd]["autogui"], cmd)
    return f"Unknown command: '{cmd}'"

#Define states of autogui syntax parser:
S_CMD_NAME = 0 # state=0: concat command name characters
S_PARAMS = 1 # state=1: concat parameter characters
S_STRING1 = 2 # state=2: concat a string in ' character in parameters
S_STRING2 = 3 # state=3: concat a string in " character in parameters
S_CMD_END = 4 # state=4: command end reached
S_STRING_END = 5 # state=5: string parameter end reached

def call_autogui_cmd_list(msg): # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
    """
    Call a list of autogui commands seperated by ';'
    """
    # Execute an autogui command list separated by ';'
    cmd = ""
    params = ""
    state = S_CMD_NAME
    esc = False  # previous caracter was an escape character \ in a string
    msg = msg.strip()
    feedback = "OK"  # last command feedback
    for c in msg:
        if esc is True:
            # just take the current character
            params += c
            esc = False
            continue
        if c == "(" and state == S_CMD_NAME:
            # switch to parameters state
            state = S_PARAMS
            continue
        if c == ")" and state in (S_PARAMS,S_STRING_END):
            # switch to parameters state
            state = S_CMD_END
            continue
        if c == '"':
            if state not in (S_CMD_NAME,S_CMD_END,S_STRING_END):
                if state == S_STRING2:
                    # end of string with ":
                    state = S_STRING_END
                else:
                    if state == S_PARAMS:
                        # start of string with ":
                        state = S_STRING2
                params += c
                continue
            return (
                f'Syntax error. Character " is not allowed here: {cmd}({params}).'
            )
        if c == "'":
            if state not in (S_CMD_NAME,S_CMD_END,S_STRING_END):
                if state == S_STRING1:
                    # end of string with ':
                    state = S_STRING_END
                else:
                    if state == S_PARAMS:
                        # start of string with ':
                        state = S_STRING1
                params += c
                continue
            return (
                f"Syntax error. Character ' is not allowed here: {cmd}({params})."
            )
        if c == ";":
            if state in (S_CMD_NAME,S_CMD_END):
                # end of command reached
                LOG.info("Excecute command: '%s(%s)'", cmd, params)
                feedback = call_autogui(cmd, params)
                if feedback != "OK":
                    if state == S_CMD_NAME:
                        return f"Error with command: '{cmd}':{feedback}. Stop."
                    return f"Error with command: '{cmd}({params})':{feedback}. Stop."
                cmd = ""
                params = ""
                state = S_CMD_NAME
                continue
            if state == S_PARAMS:
                return f"Error missing closing bracket: '{cmd}':{feedback}. Stop."
        if c == ',':
            if state == S_STRING_END:
                #next parameter starts
                state = S_PARAMS
        if c == "\\":
            if state in (S_STRING1,S_STRING2):
                # escape caracter in string
                esc = True
                continue
            if state == S_CMD_NAME:
                return f"Esc char outside strings not allowed: '{cmd}'."
            return f"Esc char outside strings not allowed: '{cmd}({params})'."

        # add this character to the command or params
        if state == S_CMD_NAME:
            if c.isdigit() or c.isalpha() or c == "_":
                cmd += c
            else:
                return f"Not allowed character in command name: '{cmd}{c}'. Stop."
        else:
            if state not in [S_CMD_END,S_STRING_END]:
                params += c
            else:
                if not c.isspace():
                    return (
                        f"Wrong character after: '{cmd}({params}){c}'. Stop."
                    )

    # excecute the last cmd
    if len(cmd) > 0 and feedback == "OK":
        if state == S_CMD_NAME:
            LOG.info("Excecute command: '%s'",cmd)
            return call_autogui(cmd, params)
        if state == S_CMD_END:
            LOG.info("Excecute command: '%s(%s)'",cmd,params)
            return call_autogui(cmd, params)
        return (
            f"Syntax error with command. Unterminated string: '{cmd}({params})'"
        )
    return feedback
