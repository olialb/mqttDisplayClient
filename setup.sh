#!/bin/bash
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
abort()
{
   echo "
###########################
Abort!!        
###########################
An error occured Exiting..." >&2
   exit 1
}
trap 'abort' 0
#exit on error
set -e

##################
#options
##################
pyautogui=disabled
bh1750=disabled
backlight=enabled

while getopts "f:" opt; do
	case $opt in
		f)
			if [ $OPTARG = pyautogui ]
			then
				echo "Install pyautogui!"
				pyautogui=enabled
			fi
			if [ $OPTARG = backlight ]
			then
				echo "Install backlight support!"
				bh1750=enabled
			fi
			if [ $OPTARG = haDiscover ]
			then
				echo "Activate home assistant discovery!"
				haDiscover=enabled
			fi
			;;
	esac
done

echo "#########################################"
echo "Create virtual environment"
echo "#########################################"
python3 -m venv venv
source venv/bin/activate

if [ $pyautogui = enabled ]
then	
	echo "###########################################################################"
	echo "Install required libs for pyautogui feature"
	echo "###########################################################################"
	sudo apt-get update
	sudo apt-get install -y build-essential libsqlite3-dev   libpng-dev libjpeg-dev
	sudo apt-get install -y  python3-tk python3-dev
	python -m pip install --upgrade pip
	python -m pip install --upgrade Pillow
	pip install pyautogui
fi

if [ $backlight = enabled ]
then	
	echo "###########################################################################"
	echo "Backlight control enabled"
	echo "###########################################################################"
	#nothing to install
fi
echo "#########################################"
echo "Install the required python packages..."
echo "#########################################"
echo ""
pip install gpiozero
pip install rpi.gpio
pip install rpi.lgpio
pip install validators
pip install paho-mqtt

echo "#########################################"
echo "Fill templates"
echo "#########################################"
echo ""
eval "echo \"$(cat mqttDisplayClient.ini.template)\"" >mqttDisplayClient.ini
python openhabFillThingsTemplate.py 
 
echo "################################################"
echo "Install systemd serice..."
echo "service name: mqttDisplayClient"
eval "echo \"user        : $USER\""
echo "################################################"
echo ""
#chmod +x mqttDisplayClient
eval "echo \"$(cat mqttDisplayClient.service.template)\"" >mqttDisplayClient.service
sudo mv mqttDisplayClient.service /lib/systemd/system/mqttDisplayClient.service
sudo chmod 644 /lib/systemd/system/mqttDisplayClient.service
sudo systemctl daemon-reload
#sudo systemctl status mqttDisplayClient
sudo systemctl enable mqttDisplayClient

echo "################################################"
echo "Stop the service with:"
echo "sudo systemctl stop mqttDisplayClient"
echo ""
echo "Start the service with:"
echo "sudo systemctl start mqttDisplayClient"
echo "################################################"
trap - 0
