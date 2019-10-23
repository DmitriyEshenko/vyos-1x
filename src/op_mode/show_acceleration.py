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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import os
import re
import argparse
import subprocess
from vyos.config import Config

def detect_qat_dev():
    ret = subprocess.Popen(['sudo', 'lspci',  '-nn'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output, err) = ret.communicate()
    if not err:
        data = re.findall('(8086:19e2)|(8086:37c8)|(8086:0435)|(8086:6f54)', output.decode("utf-8"))
        #If QAT devices found
        if data:
            return
    print("\t No QAT device found")
    sys.exit(1)

def show_qat_status():
    detect_qat_dev()

    # Check QAT service
    if not os.path.exists('/etc/init.d/vyos-qat-utilities'):
        print("\t QAT service not installed")
        sys.exit(1)

    # Show QAT service
    os.system('sudo /etc/init.d/vyos-qat-utilities status')

# Return QAT path in sysfs
def get_qat_proc_path():
    q_type = ""
    q_bsf  = ""
    ret = subprocess.Popen(['sudo', '/etc/init.d/vyos-qat-utilities',  'status'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output, err) = ret.communicate()
    if not err:
        # Parse QAT service output
        data_st = output.decode("utf-8").split(",  ")
        for elm in range(len(data_st)):
            elm_list = data_st[elm].split(": ")
            if re.search('type', elm_list[0]):
                q_type=elm_list[1]
            elif re.search('bsf', elm_list[0]):
                q_bsf=elm_list[1]

        return "/sys/kernel/debug/qat_"+q_type+"_"+q_bsf+"/"

# Check if QAT service confgured
def check_qat_if_conf():
    if not Config().exists_effective('system acceleration qat'):
        print("\t system acceleration qat is not configured")
        sys.exit(1)

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("--hw", action="store_true", help="Show Intel QAT HW")
group.add_argument("--flow", action="store_true", help="Show Intel QAT flows")
group.add_argument("--intr", action="store_true", help="Show Intel QAT interrupts")
group.add_argument("--status", action="store_true", help="Show Intel QAT status")
group.add_argument("--conf", action="store_true", help="Show Intel QAT configuration")

args = parser.parse_args()

if args.hw:
    detect_qat_dev()
    # Show availible Intel QAT devices
    os.system('sudo lspci -nn | egrep -e \'8086:37c8|8086:19e2|8086:0435|8086:6f54\'')
elif args.flow:
    check_qat_if_conf()
    os.system('sudo cat '+get_qat_proc_path()+"fw_counters")
elif args.intr:
    check_qat_if_conf()
    os.system('sudo cat /proc/interrupts | grep qat')
elif args.status:
    check_qat_if_conf()
    show_qat_status()
elif args.conf:
    check_qat_if_conf()
    os.system('sudo cat '+get_qat_proc_path()+"dev_cfg")
else:
    parser.print_help()
    sys.exit(1)