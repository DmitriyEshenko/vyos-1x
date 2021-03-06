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

import sys
import jinja2
import copy
import os
import vyos.validate

from vyos import ConfigError
from vyos.config import Config

config_file = r'/tmp/bfd.frr'

# Please be careful if you edit the template.
config_tmpl = """
!
bfd
{% for peer in old_peers -%}
 no peer {{ peer }}
{% endfor -%}
!
{% for peer in new_peers -%}
 peer {{ peer.remote }}{% if peer.multihop %} multihop{% endif %}{% if peer.src_addr %} local-address {{ peer.src_addr }}{% endif %}{% if peer.src_if %} interface {{ peer.src_if }}{% endif %}
 detect-multiplier {{ peer.multiplier }}
 receive-interval {{ peer.rx_interval }}
 transmit-interval {{ peer.tx_interval }}
 {% if not peer.shutdown %}no {% endif %}shutdown
{% endfor -%}
!
"""

default_config_data = {
    'new_peers': [],
    'old_peers' : []
}

def get_config():
    bfd = copy.deepcopy(default_config_data)
    conf = Config()
    if not (conf.exists('protocols bfd') or conf.exists_effective('protocols bfd')):
        return None
    else:
        conf.set_level('protocols bfd')

    # as we have to use vtysh to talk to FRR we also need to know
    # which peers are gone due to a config removal - thus we read in
    # all peers (active or to delete)
    bfd['old_peers'] = conf.list_effective_nodes('peer')

    for peer in conf.list_nodes('peer'):
        conf.set_level('protocols bfd peer {0}'.format(peer))
        bfd_peer = {
            'remote': peer,
            'shutdown': False,
            'src_if': '',
            'src_addr': '',
            'multiplier': '3',
            'rx_interval': '300',
            'tx_interval': '300',
            'multihop': False
        }

        # Check if individual peer is disabled
        if conf.exists('shutdown'):
            bfd_peer['shutdown'] = True

        # Check if peer has a local source interface configured
        if conf.exists('source interface'):
            bfd_peer['src_if'] = conf.return_value('source interface')

        # Check if peer has a local source address configured - this is mandatory for IPv6
        if conf.exists('source address'):
            bfd_peer['src_addr'] = conf.return_value('source address')

        # Tell BFD daemon that we should expect packets with TTL less than 254
        # (because it will take more than one hop) and to listen on the multihop
        # port (4784)
        if conf.exists('multihop'):
            bfd_peer['multihop'] = True

        # Configures the minimum interval that this system is capable of receiving
        # control packets. The default value is 300 milliseconds.
        if conf.exists('interval receive'):
            bfd_peer['rx_interval'] = conf.return_value('interval receive')

        # The minimum transmission interval (less jitter) that this system wants
        # to use to send BFD control packets.
        if conf.exists('interval transmit'):
            bfd_peer['tx_interval'] = conf.return_value('interval transmit')

        # Configures the detection multiplier to determine packet loss. The remote
        # transmission interval will be multiplied by this value to determine the
        # connection loss detection timer. The default value is 3.
        if conf.exists('interval multiplier'):
            bfd_peer['multiplier'] = conf.return_value('interval multiplier')

        bfd['new_peers'].append(bfd_peer)

    return bfd

def verify(bfd):
    if bfd is None:
        return None

    for peer in bfd['new_peers']:
        # Bail out early if peer is shutdown
        if peer['shutdown']:
            continue

        # IPv6 peers require an explicit local address/interface combination
        if vyos.validate.is_ipv6(peer['remote']):
            if not (peer['src_if'] and peer['src_addr']):
                raise ConfigError('BFD IPv6 peers require explicit local address/interface setting')

        # multihop doesn't accept interface names
        if peer['multihop'] and peer['src_if']:
            raise ConfigError('multihop does not accept interface names')


    return None

def generate(bfd):
    if bfd is None:
        return None

    return None

def apply(bfd):
    if bfd is None:
        return None

    tmpl = jinja2.Template(config_tmpl)
    config_text = tmpl.render(bfd)
    with open(config_file, 'w') as f:
        f.write(config_text)

    os.system("sudo vtysh -d bfdd -f " + config_file)
    if os.path.exists(config_file):
        os.remove(config_file)

    return None

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        sys.exit(1)
