#!/usr/bin/env python3
#
# Copyright (C) 2019 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import sys
import os
import time
import syslog as sl
import subprocess

from vyos.config import Config
from vyos import ConfigError

# Define for recovering
gl_ipsec_conf = None

def get_config():
  c = Config()
  config_data = {
    'qat_conf'     : None,
    'ipsec_conf'   : None,
    'openvpn_conf' : None,
  }

  if c.exists('system acceleration qat'):
    config_data['qat_conf'] = True
    
  if c.exists('vpn ipsec '):
    gl_ipsec_conf = True
    config_data['ipsec_conf'] = True

  if c.exists('interfaces openvpn'):
    config_data['openvpn_conf'] = True

  return config_data

# Control configured VPN service which can use QAT 
def vpn_control(action):
  if action == 'restore' and gl_ipsec_conf:
    ret = subprocess.Popen(['sudo', 'ipsec', 'start'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output, err) = ret.communicate()
    return

  ret = subprocess.Popen(['sudo', 'ipsec', action], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  (output, err) = ret.communicate()

def verify(c):
  print(c)
  # Check if QAT service installed
  if not os.path.exists('/etc/init.d/qat_service'):
    raise ConfigError("Warning: QAT init file not found")

  if c['qat_conf'] == None:
    return

def apply(c):
  if c['ipsec_conf']:
    # Shutdown VPN service which can use QAT
    vpn_control('stop')

  # Disable QAT service
  if c['qat_conf'] == None:
    ret = subprocess.Popen(['sudo', '/etc/init.d/qat_service', 'stop'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output, err) = ret.communicate()
    sl.syslog(sl.LOG_NOTICE, "QAT acceleration service terminated")
    vpn_control('start')
    return

  # Run qat init.d script
  ret = subprocess.Popen(['sudo', '/etc/init.d/qat_service', 'start'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  (output, err) = ret.communicate()

  if c['ipsec_conf']:
    # Recovery VPN service
    vpn_control('start')

if __name__ == '__main__':
  try:
    c = get_config()
    verify(c)
    apply(c)
  except ConfigError as e:
    print(e)
    vpn_control('restore')
    sys.exit(1)
