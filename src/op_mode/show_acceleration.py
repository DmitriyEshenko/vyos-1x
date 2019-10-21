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
import argparse

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("--hw", action="store_true", help="Show Intel QAT HW")
group.add_argument("--fw", action="store_true", help="Show Intel QAT flows")
group.add_argument("--intr", action="store_true", help="Show Intel QAT interrupts")
group.add_argument("--status", action="store_true", help="Show Intel QAT status")

args = parser.parse_args()

if args.hw:
    os.system('sudo lspci -nn | egrep -e \'8086:37c8|8086:19e2|8086:0435|8086:6f54\'')
elif args.fw:
    print("FW")
elif args.intr:
    os.system('sudo cat /proc/interrupts | grep qat_')
elif args.status:
    print("STATUS")
    os.system('sudo /etc/init.d/qat_service status')
else:
    parser.print_help()
    sys.exit(1)
