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
 
import time
import logging
import os
os.environ['DISPLAY'] = ':0' #environment variable needed for pyautogui
import pyautogui
#switch off Fail Safe
#pydirectinput.FAILSAFE = False
pyautogui.FAILSAFE = False

#
#initialize logger
#
log = logging.getLogger('AutoGUICommands')
logging.basicConfig()

def autogui_log_level( level ):
    log.setLevel (level)

#########################
#Parameter interpreters:
#########################

def ag_par_string( str ):
    #check string parameter
    
    str.strip()
    if str[0] == '"' and str[-1] == '"':        
        return 'OK', str[1:-1]
    if str[0] == "'" and str[-1] == "'":        
        return 'OK', str[1:-1]
    err = f"Error in string parameter. No quotes: {str}"
    log.debug( err )
    return err, str
    
def ag_par_x( str ):
    #interpret x paramater
    err = 'OK'
    x=0
    try:
        x = int(str)
    except Exception as inst:
        err = f"Error in parameter syntax: {inst}"
        log.debug( err )
    return err,x
    
def ag_par_xy( str ):
    #interpret x,y paramater
    coordinates = str.split(',')
    err = 'OK'
    x=0
    y=0
    if len(coordinates) == 2:
        try:
            x = int(coordinates[0])
            y = int(coordinates[1])
        except Exception as inst:
            err = f"Error in parameter syntax: {inst}"
            log.debug( err )
    else:
        err = f"Error in parameter syntax: {str}"
        log.debug( err )
    return err,x,y
    
#########################
#Parameter interpreters:
#########################
   
def ag_cmd_key( func, cmd, str ):
    #calls pyautogui function with parameter (x)
    err, str  = ag_par_string( str )
    str=str.strip()
    if err == 'OK':
        if str not in pyautogui.KEYBOARD_KEYS:
            err = f"Parameter not in KEYBOARD_KEYS: {str}"
            log.debug( err )
        else:
            try:
                func(str)
            except Exception as inst:
                err = f"Error calling pyautogui.{cmd} with ({str}): {inst}"
                log.debug( err )
    return err

def ag_cmd_string( func, cmd, str ):
    #calls pyautogui function with parameter (x)
    err, str  = ag_par_string( str )
    if err == 'OK':
        try:
            func(str)
        except Exception as inst:
            err = f"Error calling pyautogui.{cmd} with ({str}): {inst}"
            log.debug( err )
    return err

def ag_cmd_x( func, cmd, str ):
    #calls pyautogui function with parameter (x)
    err, x  = ag_par_x( str )
    if err == 'OK':
        try:
            func(x)
        except Exception as inst:
            err = f"Error calling pyautogui.{cmd} with ({x}): {inst}"
            log.debug( err )
    return err

def ag_cmd_ms( func, cmd, str ):
    #calls pyautogui function with parameter (x)/1000
    err, x  = ag_par_x( str )
    if err == 'OK':
        try:
            x=float(x)/1000
            func(x)
        except Exception as inst:
            err = f"Error calling pyautogui.{cmd} with ({x}): {inst}"
            log.debug( err )
    return err
    
def ag_cmd_xy( func, cmd, str ):
    #calls pyautogui function with parameter (x,y)
    err, x, y = ag_par_xy( str )
    if err == 'OK':
        try:
            func(x, y)
        except Exception as inst:
            err = f"Error calling pyautogui.{cmd} with ({x},{y}): {inst}"
            log.debug( err )
    return err

def ag_cmd_xy_right( func, cmd, str ):
    #calls pyautogui function with parameter (x,y)
    err, x, y = ag_par_xy( str )
    if err == 'OK':
        try:
            func(x, y, button='right')
        except Exception as inst:
            err = f"Error calling pyautogui.{cmd} with ({x},{y},button='right'): {inst}"
            log.debug( err )
    return err

def ag_cmd_xy_middle( func, cmd, str ):
    #calls pyautogui function with parameter (x,y)
    err, x, y = ag_par_xy( str )
    if err == 'OK':
        try:
            func(x, y, button='middle')
        except Exception as inst:
            err = f"Error calling pyautogui.{cmd} with ({x},{y},button='middle'): {inst}"
            log.debug( err )
    return err

def ag_cmd( func, cmd ):
    #calls pyautogui function withour parameter
    err = 'OK'
    try:
        func()
    except Exception as inst:
        err = f"Error calling pyautogui.{cmd}: {inst}"
        log.debug( err )
    return err

def ag_cmd_right( func, cmd ):
    #calls pyautogui function withour parameter
    err = 'OK'
    try:
        func(button='right')
    except Exception as inst:
        err = f"Error calling pyautogui.{cmd}: {inst}"
        log.debug( err )
    return err

def ag_cmd_middle( func, cmd ):
    #calls pyautogui function withour parameter
    err = 'OK'
    try:
        func(button='middle')
    except Exception as inst:
        err = f"Error calling pyautogui.{cmd}: {inst}"
        log.debug( err )
    return err


#########################
#Command dispacher
#########################

#dictionary with command with parameters
commandsWithPar = { 'click':        { 'interpreter': ag_cmd_xy, 'autogui': pyautogui.click },
                    'clickright':   { 'interpreter': ag_cmd_xy_right, 'autogui': pyautogui.click },               
                    'clickmiddle':  { 'interpreter': ag_cmd_xy_middle, 'autogui': pyautogui.click },               
                    'moveto':       { 'interpreter': ag_cmd_xy, 'autogui': pyautogui.moveTo },
                    'move':         { 'interpreter': ag_cmd_xy, 'autogui': pyautogui.move },
                    'dragto':       { 'interpreter': ag_cmd_xy, 'autogui': pyautogui.dragTo },
                    'dragtoright':  { 'interpreter': ag_cmd_xy_right, 'autogui': pyautogui.dragTo },
                    'dragtomiddle': { 'interpreter': ag_cmd_xy_middle, 'autogui': pyautogui.dragTo },
                    'scroll':       { 'interpreter': ag_cmd_x, 'autogui': pyautogui.scroll },
                    'hscroll':      { 'interpreter': ag_cmd_x, 'autogui': pyautogui.hscroll },
                    'wait':         { 'interpreter': ag_cmd_ms, 'autogui': time.sleep },
                    'write':        { 'interpreter': ag_cmd_string, 'autogui': pyautogui.write },
                    'press':        { 'interpreter': ag_cmd_key, 'autogui': pyautogui.press },
                    'keydown':      { 'interpreter': ag_cmd_key, 'autogui': pyautogui.keyDown }
}

#list of commads without parameters
commands = { "click":           { 'interpreter': ag_cmd, 'autogui': pyautogui.click },
             "doubleclick":     { 'interpreter': ag_cmd, 'autogui': pyautogui.doubleClick },
             "clickright":      { 'interpreter': ag_cmd_right, 'autogui': pyautogui.click },   
             "clickmiddle":     { 'interpreter': ag_cmd_middle, 'autogui': pyautogui.click },   
             "mousedown":       { 'interpreter': ag_cmd, 'autogui': pyautogui.mouseDown },   
             "mousedownright":  { 'interpreter': ag_cmd_right, 'autogui': pyautogui.mouseDown },   
             "mousedownmiddle": { 'interpreter': ag_cmd_middle, 'autogui': pyautogui.mouseDown },   
             "mouseup":         { 'interpreter': ag_cmd, 'autogui': pyautogui.mouseUp },   
             "mouseupright":    { 'interpreter': ag_cmd_right, 'autogui': pyautogui.mouseUp },   
             "mouseupmiddle":   { 'interpreter': ag_cmd_middle, 'autogui': pyautogui.mouseUp }
}

def call_autogui( cmd, params ):
    #functions interpreter for autogui commands
    cmd=cmd.strip().lower()
    if len(params) > 0:
        #its a command with parameter
        if cmd in commandsWithPar:
            return commandsWithPar[cmd]['interpreter'](commandsWithPar[cmd]['autogui'],cmd, params.strip())
        else:
            return f"Unknown command: '{cmd}({params})'"
    else:
        #its a command without parameter
        if cmd in commands:
            return commands[cmd]['interpreter'](commands[cmd]['autogui'],cmd)
        else:
            return f"Unknown command: '{cmd}'"
            
def call_autogui_cmd_list( msg ):
    #Execute an autogui command list separated by ';'
    cmd=""
    params=""
    state=0 #state=0: concat command name characters
            #state=1: concat parameter characters
            #state=2: concat a string in ' character in parameters
            #state=3: concat a string in " character in parameters
            #state=4: command end reached
    esc=False #previous caracter was an escape character \ in a string 
    msg=msg.strip()
    feedback = 'OK' #last command feedback
    for c in msg:
        if esc == True:
            #just take the current character
            params += c
            esc=False
            continue
        if c == '(' and state==0:
            #switch to parameters state
            state=1
            continue
        if c == ')' and state==1:
            #switch to parameters state
            state=4
            continue
        if c == '"' and state != 0:
            if state == 3:
                #end of string with ":
                state = 1
            else:
                #start of string with ":
                state = 3
            params += c
            continue
        else:
            if c == '"':
                return f'Syntax error in commad name. character " is not allowed: {cmd}"'
        if c == "'" and state != 0:
            if state == 2:
                #end of string with ':
                state = 1
            else:
                #start of string with ':
                state = 2
            params += c
            continue
        else:
            if c == "'":
                return f"Syntax error in commad name. character ' is not allowed: {cmd}'"
        if c == ';' and (state==0 or state==4):
            #end of command reached
            log.info(f"Excecute command: '{cmd}({params})'")
            feedback = call_autogui(cmd, params)
            if feedback != 'OK':
                if state==0:
                    return f"Error with command: '{cmd}':{feedback}. Stop excecution"
                else:
                    return f"Error with command: '{cmd}({params})':{feedback}. Stop excecution"
                return feedback
            cmd=""
            params=""
            state=0
            continue
        else:
            if c == ';' and state==1:
                return f"Error missing closing bracket: '{cmd}':{feedback}. Stop excecution"
        if c == '\\' and (state==2 or state==3):
            #escape caracter in string
            esc = True
            continue
        else:
            if c == '\\':
                if state == 0:
                    return f"Escape character outside strings not allowed: '{cmd}\\'. Stop excecution"
                else:
                    return f"Escape character outside strings not allowed: '{cmd}({params})\\'. Stop excecution"

        #just add this character to the command or params
        if state==0:
            if c.isdigit() or c.isalpha() or c == '_':
                cmd+=c
            else:
                return f"Not allowed character in command name: '{cmd}{c}'. Stop excecution"
        else:
            if state != 4:
                params+=c
            else:
                if not c.isspace():
                    return f"Wrong character after: '{cmd}({params}){c}'. Stop excecution"
            
    #excecute the last cmd
    if len(cmd) > 0 and feedback == 'OK':
        if state==0:
            log.info(f"Excecute command: '{cmd}'")
            return call_autogui(cmd,params)
        else:
            if state==4:
                log.info(f"Excecute command: '{cmd}({params})'")
                return call_autogui(cmd,params)
            else:
                return f"Syntax error with command. Untermnated string: '{cmd}({params})'"
    else:
        return feedback
