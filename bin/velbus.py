#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Velbus usb support
=> based on rfxcom plugin

@author: Maikel Punie <maikel.punie@gmail.com>
@copyright: (C) 2007-20012 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.common.plugin import Plugin
from domogikmq.message import MQMessage
from domogik_packages.plugin_velbus.lib.velbus import VelbusException
from domogik_packages.plugin_velbus.lib.velbus import VelbusDev
import threading
import re

class VelbusManager(Plugin):
    """
	Managages the velbus domogik plugin
    """
    def __init__(self):
        """ Init plugin
        """
        Plugin.__init__(self, name='velbus')
        # register helpers
        self.register_helper('scan', 'test help', 'scan')

        # check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return

        # get the config values
        device_type = self.get_config("connection-type")
        if device_type == None:
            self.log.error('Devicetype is not configured, exitting') 
            print('Devicetype is not configured, exitting')
            self.force_leave()
            return
        device = self.get_config("device")
        #device = '192.168.1.101:3788'
        if device == None:
            self.log.error('Device is not configured, exitting') 
            print('Device is not configured, exitting')
            self.force_leave()
            return
        # validate the config vars
        if (device_type != 'serial') and (device_type != 'socket'):
            self.log.error('Devicetype must be socket or serial, exitting') 
            print('Devicetype must be socket or serial, exitting')
            self.force_leave()
            return
        if device_type == 'socket' and not re.match('[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}:[0-9]+', device):
            self.log.error('A socket device is in the form of <ip>:<port>, exitting') 
            print('A socket device is in the form of <ip>:<port>, exitting')
            self.force_leave()
            return

        # Init RFXCOM
        self.manager = VelbusDev(self.log, self.send_sensor, self.get_stop())
        self.add_stop_cb(self.manager.close)
        self._sens, self._cmds = self._parseDevices(self.get_device_list(quit_if_no_device = True))
        # try opening
        try:
            self.manager.open(device, device_type)
        except VelbusException as ex:
            self.log.error(ex.value)
            self.force_leave()
            return
            
        # Start reading thread
        listenthread = threading.Thread(None,
                                   self.manager.listen,
                                   "velbus-process-reader",
                                   (self.get_stop(),),
                                   {})
        self.register_thread(listenthread)
        listenthread.start()

	# start scanning the bus
        self.manager.scan()

	# notify ready
        self.ready()

    def scan(self, test1, test2):
        return "{0}-{1}".format(test1, test2)

    def on_mdp_request(self, msg):
        Plugin.on_mdp_request(self, msg)
        if msg.get_action() == "client.cmd":
            data = msg.get_data()
            index = self._cmds[data['device_id'],data['command_id']]
            addr = index['dev']
            chan = index['chan']
            del index
            if 'level' in data:
                self.manager.send_level( addr, chan, data['level'])
                self.send_sensor(addr, chan, ["DT_Scaling" "DT_Switch"], data['level'])
            if 'command' in data:
                if data['command'] == 'up':
                    self.log.debug("set shutter up")
                    self.manager.send_shutterup( addr, chan )
                    self.send_sensor(addr, chan, "DT_UpDown", 0)
                if data['command'] == 'down':
                    self.log.debug("set shutter down")
                    self.manager.send_shutterdown( addr, chan )
                    self.send_sensor(addr, chan, "DT_UpDown", 1)
            reply_msg = MQMessage()
            reply_msg.set_action('client.cmd.result')
            reply_msg.add_data('status', True)
            reply_msg.add_data('reason', None)
            self.reply(reply_msg.get())

    def send_sensor(self, dev, chan, dt_type, value):
        # find the sensor
        if type(dt_type) == list:
            for dt in dt_type:
                ind = (str(dev),str(chan),str(dt_type))
                if ind in self._sens.keys():
                    break
        else:
            ind =  (str(dev),str(chan),str(dt_type))
        if ind in self._sens.keys():
            sen = self._sens[ind]
            self.log.info("Sending MQ status: dev:{0} chan:{1} dt:{2} sen:{3} value:{4}".format(dev, chan, dt_type, sen, value))
            self._pub.send_event('client.sensor',
                         {sen : value})
        else:
            self.log.error("Can not Send MQ status, sensor not found")
            self.log.debug("device: {0} channel: {1} dt: {2}".format(dev, chan, dt_type))

    def _parseDevices(self, devices):
        sensors = {}
        commands = {}
        for dev in devices:
            if 'device' in dev['parameters'] and 'channel' in dev['parameters']:
                for cmdn in dev['commands']:
                    cmd = dev['commands'][cmdn]
                    commands[dev['id'],cmd['id']] = { 'dev': dev['parameters']['device']['value'], 'chan': dev['parameters']['channel']['value'] }
                for senn in dev['sensors']:
                    sen = dev['sensors'][senn]
                    ind = (str(dev['parameters']['device']['value']),str(dev['parameters']['channel']['value']),str(sen['data_type']))
                    sensors[ind] = sen['id']
        return sensors, commands
       
if __name__ == "__main__":
    VelbusManager()
