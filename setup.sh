#!/bin/bash
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

while getopts "f:" opt; do
	case $opt in
		f)
			if [ $OPTARG = pyautogui ]
			then
				echo "Install pyautogui!"
				pyautogui=enabled
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
	echo "!!Please remember to enable the feature in the mqttDisplayClient.ini file!!"
	echo "###########################################################################"
	sudo apt-get update
	sudo apt-get install -y build-essential libsqlite3-dev   libpng-dev libjpeg-dev
	sudo apt-get install -y  python3-tk python3-dev
	python -m pip install --upgrade pip
	python -m pip install --upgrade Pillow
	pip install pyautogui
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
