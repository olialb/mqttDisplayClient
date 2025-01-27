# FullPageOS MQTT client

## Purpose of this project
[FullPageOS](https://github.com/guysoft/FullPageOS) is a Raspberry PI OS to support touch displays in full screen mode for kiosk applications to control your smart home.
This MQTT client is extending the [FullPageOS](https://github.com/guysoft/FullPageOS) with a MQTT client to allows the control of the Display from remote. That means your smart home system can set:

* The brighness and backlight status of the Kioskdisplay
* Set and change panel content with remote commands
* Reboot and Shutown the Kioskdisplay
* Read status like CPU temparature, CPU load,....

**Home Assistant discovery** can be activated for all MQTT the topics.

The configuration is done over an ini file and allows you to adapt the commands to your needs. As default it is configured for an official Raspberry PI 7 inch Touch Display 2. How to setup this display with [FullPageOS](https://github.com/guysoft/FullPageOS) you can read here: [Installation and config of FullPageOS](https://albold-home.de/part-1-installation-and-config-of-fullpage-os/)

## Implementation notes

The project in implemented and tested with [Python 3.11](https://www.python.org/downloads/) and runs as systemd service for standard user *pi* in [FullPageOS](https://github.com/guysoft/FullPageOS).

The implementaion is using the folling python libraries, which need to be installed:
* [paho-mqtt](https://pypi.org/project/paho-mqtt/) to implement the mqtt client
* [gpiozero](https://gpiozero.readthedocs.io/en/latest/) to read system status values
* [validators](https://pypi.org/project/validators/) to validate the semantical correctness of the configured web page URLs

Optional to control the mouse and send keyboard commands:
* [pyautogui](https://pyautogui.readthedocs.io/en/latest/) Needs also [Pillow](https://github.com/python-pillow/Pillow)

All this libraries are installed with the `setup.sh` shell script, which is part of this project. See next section [Installation](#installation)

All the other used python libraries are standard in latest Raspbery PI OS and should be available without installation.
 

## Installation 
**Precondition**: [FullPageOS](https://github.com/guysoft/FullPageOS) is installed on your Raspberry PI and up and running.
#### Step 1:
Login with ssh to your kioskdisplay with user *pi*
#### Step 2:
Clone this project with: 
```
git clone https://github.com/olialb/mqttDisplayClient
``` 
and go inside the project directory: 
```
cd mqttDisplayClient
```
#### Step 3:
Call setup: 
```
bash setup.sh
```
As an alternative you can add optional features during with the setup.sh call:
```
bash setup.sh -f pyautogui -f backlight -f haDiscover
```
This installs the required python packages and configures a systemd service which is atomatically running the mqtt client after startup. The systemd service is started with the current user rights.

#### Step 4:
Configure the ini file for your personal needs: 
```
nano mqttDisplayClient.ini 
```
Details of the configuration you can find in next section: [Configuration](#configuration)


#### In case of problems:

If you have issues with your configuration and the service is not running as expected you can stop the service with:
```bash
sudo systemctl stop mqttDisplayClient
```
Adapt the ini file in section [[logging]](#section-logging) and enable *DEBUG* logging level. Than activate the virtual python environment and start the service by hand:
```bash
source venv/bin/activate
python mqttDisplayClient.py
```
Check the logging output. After everything is fixed, set the logging level back to *ERROR*, deactivate the virtual environment and start the systemd service again with:
```bash
deactivate
sudo systemctl start mqttDisplayClient
```

## Configuration
In the project directory you find the configuration *mqtt-display-client.ini*. Adapt this file with an editor like *nano*:
```bash
nano mqttDisplayClient.ini
```
The file has different sections. Most of the configuration you can keep untouched. The only thing which you need to adapt to your specific environment are:

* Address of your mqtt broker in section [[global]](#section-global)
* Username and password of your mqtt broker, if needed. In section [[global]](#section-global)
* ID of your display in section [[global]](#section-global)

This configuration you find in the first section of the ini file: [[global]](#section-global). You can also setup some url shortcuts in the [[panels]](#section-panels) section. This makes it afterwards easier to open a webpage via a mqtt command in your kioskdisplay.

#### Section **[global]**
This is the main configuration section. This is the only section where you need to adapt somthing to your environment. 
* *broker=* Set here your mqtt broker address. Apapt the ip address or use url like *myLocalMQTTBroker.local*
* *port=* You can keep the standard port 1883 if you do not have a special setup
* *username=* Set here your user name for the broker. Keep it empty if no username is configured
* *password=* Password of your mqtt broker
* *topicRoot=* configuration of the root path of the published topics
* *deviceName=* Unique name of this device
* *displayID=* Display id of your display in file system. Check with `ls /sys/class/backlight`
* *reconnectDelay*= Retry delay in seconds if connection is lost to broker
* *publishDelay*= Publish cycle in seconds for topics
* *fullPublishCycle*= Publish cycle even if topic content is not changed. Cycle is *fullPublishCycle* multiplied with *publishCycle* in seconds
* *defaultUrl*= Path to FullPageOS config file for default URL after startup

#### Section **[logging]**
Configuration of the python logger which is used to log events

* *level*= configuration of the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  
#### Section **[feature]**
Section to enable and diable additional features

* *pyautogui*= enables or disables autogui feature to control the GUI remotly (possible values: *enabled* or *disabled*)
* *backlight*= enables or disables feature to control brightness and backlight ON/OFF state remotly (possible values: *enabled* or *disabled*). Default configuraion in the ini file is for Raspberry PI Touch Panel 2.
* *haDiscover*= enables or disables Home Assistant auto discover feature (possible values: *enabled* or *disabled*). Thanks to that you can automatically see new entity for you kiosk instance in MQTT integration.
  
#### Section **[brightness]**
This section configure the shell commands which are needed to read and set the display brightness. By default the section is configured for an original raspberry pi 7 inch touch display 2. Even if you use this display you may need to adapt the display ID in the commands. You can find your local ID with:

* *min=* minumum brightness value of your display
* *max=* maximum brightness value of your display

This values are used to calculate the brighness from 0% to 100% in the MQTT topics.

* *set=* shell command to set the display brightness. String '{value}' and '{displayID}' will be replaced by configured values
* *get=* shell command to read the display brightness. String '{displayID}' will be replaced by the configured value

#### Section **[backlight]**
This section configure the shell commands which are needed to switch the display backlight on and off. By default the section is configured for an original raspberry pi 7 inch touch display 2. Even if you use this display you may need to adapt the display ID in the commands. You can find your local ID with:

* *ON=* on value
* *OFF=* off value

This values are used to calculate the brighness from 0% to 100% in the MQTT topics.

* *set=* shell command to set the backlight on or off. String '{value}' and '{displayID}' will be replaced by configured values
* *get=* shell command to read the display backlight status. String '{displayID}' will be replaced by the configured value

#### Section **[url]**
Normally you don't need to adapt this section. It is used to define the shell command to call a webpage in chromium browser.
```ini
command=chromium {URL}
```
The strong '{URL}' is replaced with the website which the mqtt client set over the command topic */url/set*.

#### Section **[panels]**
All entries in this section are website shortcuts which you can use to open a webpage in your kioskdisplay with the mptt command topic *url*
Format is:
```ini
panelName=full qualified url|optional autogui command list separated by semicolon
```
Examples:
```ini
clock=https://uhr.ptb.de|wait(1000);click(517,56)
tagesschau=https://tagesschau.de

```

The *shortcuts* are **not** case sensitive in mqtt commands.

#### Section **[shellCommands]**
In this section are the systen shell commands configured which you can call with the mqtt command topic. By default a command to reboot and a command to shutdown the system is configured. You can add more commands, if needed. The syntax is:
```ini
keyword=put your shell command
```
Example:
```ini
reboot=sudo reboot
```
The keyword *REBOOT* is later used to call the command over mqtt with command topic *system/set*. The *keywords* are **not** case sensitive in mqtt commands.

#### Section **[haDiscover]**
This section configures the home assistant auto dicovery topics
* *deviceName=* name of this display device in the discovery topics
* *base=* root name of all discovery topics. Keep this to *homeasstant*. This is default configuration of home assistant


## Exposed MQTT topics and usage

The MQTT client is exposing the following topics:

### brigtness (numeric)
The current brightness of the display is exposed with the topic brightness `kiosk/01/display/brightness`. The value is a percentage value from 0 to 100. A new brigtness value can be set over the command topic `kiosk/01/display/brightness/set`

### backlight (switch)
The expose the status if the backlight is swithed on or off: `kiosk/01/*deviceName*//backlight`. The backlight can be switched on/off over the command topic `kiosk/01/display/brightness/set`. Payload is `ON` or `OFF`.

### system (string)
The system topic is exposing an json string with some system information. It has the following content: 

* `{'cpu_temp': X}`: X is the CPU temperature in celsius
* `{'cpu_load': X}`: X is the average CPU load in percent
* `{'disk_usage': X}`: X is the current disc usage in percent
* `{'default_url': 'url'}`: 'url' is the default url after startup which is configured for FullPageOS
  
### shell (string)
The shell topic is a command topic. Over `kiosk/01/display/shell/set` it is possible to call shell commands which are configured in the ini file in section [[shellCommands]](#section-shellCommands). Payload is the configured keyword for each command. By default are the keywords `REBOOT` and `SHUTDOWN`supported

The topic `kiosk/01/display/shell` exposes a prompt '>_' when no command is executed. While the command is executed it exposes the keyword of the command

### url (string)
The url topic `kiosk/01/display/url` exposes the url of the website which is currently shown in the display.
With the command topic `kiosk/01/display/url/set` can an individual URL set. To show this URL you must set panel command topic to **Url**! (see next section):

* *url*: Any valid full qualified url including `http://` or `https://`. If the URL is not fully qualified the command is ignored. For pages in your local network use the ip address or mypage.local as address!

### panel (string)
The panel topic `kiosk/01/display/panel` exposes the url of the website which is currently shown in the display.
With the command topic `kiosk/01/display/panel/set` can the url be changed. The payload can have the following content:

* `DEFAULT`: Set the panel back to the [FullPageOS](https://github.com/guysoft/FullPageOS) default page
* `URL`: Set the url in the display which was set over the url command topic (previous section).
* *panelName*: Set the website to the URL which is configured for this *panelName* in the ini file section [[panels]](#section-panels).

## Feature *pyautogui*
The *autogui* feature allows the control of the website which is shown in the dsiplay over mouse and keyboard commmands. 
The feature can be enabled in the [[feature]](#section-feature) section. 
The feature uses the [pyautogui](https://pyautogui.readthedocs.io/en/latest/) project to send mouse or keyboard commmands over mqtt to the diplay

### Exposed MQTT topics and usage

The MQTT client is exposing the following topics when the feature *pyautogui* is enabled:

#### autogui (numeric)
This topic  `kiosk/01/display/autogui` shows the last result of an autogui command string. If everything worked fine 'OK' is exposed. In case of an error, the error message is exposed.
A list of autogui commands seperated by semicolon can be send over the command topic `kiosk/01/display/autogui/set`
The following command can be send:

* **click(x,y)** Performs a left [mouse click](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-clicks) on x,y postition
* **clickright(x,y)** Performs a [right mouse](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-clicks) click on x,y position
* **clickmiddle(x,y)** Performs a middle [mouse click](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-clicks) on x,y position
* **click()** Performs a left [mouse click](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-clicks) on current postition
* **clickright()** Performs a right [mouse click](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-clicks) on current postition
* **clickmiddle()** Performs a middle [mouse click](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-clicks) on current postition
* **mousedown()** press left [mouse botton](https://pyautogui.readthedocs.io/en/latest/mouse.html#the-mousedown-and-mouseup-functions) on current postition
* **mousedownright()** press right [mouse botton](https://pyautogui.readthedocs.io/en/latest/mouse.html#the-mousedown-and-mouseup-functions) on current postition
* **mousedownmiddle()** press middle [mouse botton](https://pyautogui.readthedocs.io/en/latest/mouse.html#the-mousedown-and-mouseup-functions) on current postition
* **mouseup()** release left [mouse botton](https://pyautogui.readthedocs.io/en/latest/mouse.html#the-mousedown-and-mouseup-functions) on current postition
* **mouseupight()** release right [mouse botton](https://pyautogui.readthedocs.io/en/latest/mouse.html#the-mousedown-and-mouseup-functions) on current postition
* **mouseupmiddle()** release middle [mouse botton](https://pyautogui.readthedocs.io/en/latest/mouse.html#the-mousedown-and-mouseup-functions) on current postition
* **moveto(x,y)** [moves mouse](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-movement) coursor to x,y position
* **move(x,y)** [moves mouse](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-movement) relative by x,y position
* **dragto(x,y)** [drag mouse](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-drags) pressing left button to x,y position
* **dragtoright(x,y)** [drag mouse](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-drags) pressing right button to x,y position
* **dragtomiddle(x,y)** [drag mouse](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-drags) pressing middle button to x,y position
* **scroll(x)** [scroll](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-scrolling) screen vertical by x
* **scrollh(x)** [scroll](https://pyautogui.readthedocs.io/en/latest/mouse.html#mouse-scrolling) screen horizontal by x
* **wait(x)** wait x milliseconds
* **write('...')** [write](https://pyautogui.readthedocs.io/en/latest/keyboard.html#the-write-function) the given string over the keyboard
* **press(XXX)** Press the given [key](https://pyautogui.readthedocs.io/en/latest/keyboard.html#keyboard-keys)
* **keydown(XXX)** Hold the given [key](https://pyautogui.readthedocs.io/en/latest/keyboard.html#keyboard-keys) down

#### system (string)
The system topic is exposing an json string. *autogui* feature adds the following data:

* `{'mouse_postion': [x,y]}`: current x,y postition of the mouse cursor
* `{'display_size': [width,hight]}`: wutdth and hight of the used display
  
