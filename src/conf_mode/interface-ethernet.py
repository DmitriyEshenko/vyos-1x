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

import os

from copy import deepcopy
from sys import exit

from vyos.ifconfig import EthernetIf, VLANIf
from vyos.configdict import list_diff, vlan_to_dict
from vyos.config import Config
from vyos import ConfigError

default_config_data = {
    'address': [],
    'address_remove': [],
    'description': '',
    'deleted': False,
    'dhcp_client_id': '',
    'dhcp_hostname': '',
    'dhcpv6_prm_only': False,
    'dhcpv6_temporary': False,
    'disable': False,
    'disable_link_detect': 1,
    'flow_control': 'on',
    'hw_id': '',
    'ip_arp_cache_tmo': 30,
    'ip_proxy_arp': 0,
    'ip_proxy_arp_pvlan': 0,
    'intf': '',
    'mac': '',
    'mtu': 1500,
    'vif_s': [],
    'vif_s_remove': [],
    'vif': [],
    'vif_remove': []
}


def apply_vlan_config(vlan, config):
    """
    Generic function to apply a VLAN configuration from a dictionary
    to a VLAN interface
    """

    if type(vlan) != type(VLANIf("lo")):
        raise TypeError()

    # update interface description used e.g. within SNMP
    vlan.ifalias = config['description']
    # ignore link state changes
    vlan.link_detect = config['disable_link_detect']
    # Maximum Transmission Unit (MTU)
    vlan.mtu = config['mtu']
    # Change VLAN interface MAC address
    if config['mac']:
        vlan.mac = config['mac']

    # enable/disable VLAN interface
    if config['disable']:
        vlan.state = 'down'
    else:
        vlan.state = 'up'

    # Configure interface address(es)
    # - not longer required addresses get removed first
    # - newly addresses will be added second
    for addr in config['address_remove']:
        vlan.del_addr(addr)
    for addr in config['address']:
        vlan.add_addr(addr)


def get_config():
    eth = deepcopy(default_config_data)
    conf = Config()

    # determine tagNode instance
    try:
        eth['intf'] = os.environ['VYOS_TAGNODE_VALUE']
    except KeyError as E:
        print("Interface not specified")

    # check if ethernet interface has been removed
    cfg_base = 'interfaces ethernet ' + eth['intf']
    if not conf.exists(cfg_base):
        eth['deleted'] = True
        # we can not bail out early as ethernet interface can not be removed
        # Kernel will complain with: RTNETLINK answers: Operation not supported.
        # Thus we need to remove individual settings
        return eth

    # set new configuration level
    conf.set_level(cfg_base)

    # retrieve configured interface addresses
    if conf.exists('address'):
        eth['address'] = conf.return_values('address')

    # get interface addresses (currently effective) - to determine which
    # address is no longer valid and needs to be removed
    eff_addr = conf.return_effective_values('address')
    eth['address_remove'] = list_diff(eff_addr, eth['address'])

    # retrieve interface description
    if conf.exists('description'):
        eth['description'] = conf.return_value('description')
    else:
        eth['description'] = eth['intf']

    # get DHCP client identifier
    if conf.exists('dhcp-options client-id'):
        eth['dhcp_client_id'] = conf.return_value('dhcp-options client-id')

    # DHCP client host name (overrides the system host name)
    if conf.exists('dhcp-options host-name'):
        eth['dhcp_hostname'] = conf.return_value('dhcp-options host-name')

    # DHCPv6 only acquire config parameters, no address
    if conf.exists('dhcpv6-options parameters-only'):
        eth['dhcpv6_prm_only'] = conf.return_value('dhcpv6-options parameters-only')

    # DHCPv6 temporary IPv6 address
    if conf.exists('dhcpv6-options temporary'):
        eth['dhcpv6_temporary'] = conf.return_value('dhcpv6-options temporary')

    # ignore link state changes
    if conf.exists('disable-link-detect'):
        eth['disable_link_detect'] = 2

    # disable ethernet flow control (pause frames)
    if conf.exists('disable-flow-control'):
        eth['flow_control'] = 'off'

    # retrieve real hardware address
    if conf.exists('hw-id'):
        eth['hw_id'] = conf.return_value('hw-id')

    # disable interface
    if conf.exists('disable'):
        eth['disable'] = True

    # ARP cache entry timeout in seconds
    if conf.exists('ip arp-cache-timeout'):
        eth['ip_arp_cache_tmo'] = int(conf.return_value('ip arp-cache-timeout'))

    # Enable proxy-arp on this interface
    if conf.exists('ip enable-proxy-arp'):
        eth['ip_proxy_arp'] = 1

    # Enable private VLAN proxy ARP on this interface
    if conf.exists('ip proxy-arp-pvlan'):
        eth['ip_proxy_arp_pvlan'] = 1

    # Media Access Control (MAC) address
    if conf.exists('mac'):
        eth['mac'] = conf.return_value('mac')

    # Maximum Transmission Unit (MTU)
    if conf.exists('mtu'):
        eth['mtu'] = int(conf.return_value('mtu'))

    # re-set configuration level and retrieve vif-s interfaces
    conf.set_level(cfg_base)
    # get vif-s interfaces (currently effective) - to determine which vif-s
    # interface is no longer present and needs to be removed
    eff_intf = conf.list_effective_nodes('vif-s')
    act_intf = conf.list_nodes('vif-s')
    eth['vif_s_remove'] = list_diff(eff_intf, act_intf)

    if conf.exists('vif-s'):
        for vif_s in conf.list_nodes('vif-s'):
            # set config level to vif-s interface
            conf.set_level(cfg_base + ' vif-s ' + vif_s)
            eth['vif_s'].append(vlan_to_dict(conf))

    # re-set configuration level and retrieve vif-s interfaces
    conf.set_level(cfg_base)
    # Determine vif interfaces (currently effective) - to determine which
    # vif interface is no longer present and needs to be removed
    eff_intf = conf.list_effective_nodes('vif')
    act_intf = conf.list_nodes('vif')
    eth['vif_remove'] = list_diff(eff_intf, act_intf)

    if conf.exists('vif'):
        for vif in conf.list_nodes('vif'):
            # set config level to vif interface
            conf.set_level(cfg_base + ' vif ' + vif)
            eth['vif'].append(vlan_to_dict(conf))

    return eth


def verify(eth):
    conf = Config()
    # some options can not be changed when interface is enslaved to a bond
    for bond in conf.list_nodes('interfaces bonding'):
        if conf.exists('interfaces bonding ' + bond + ' member interface'):
                if eth['name'] in conf.return_values('interfaces bonding ' + bond + ' member interface'):
                    if eth['disable']:
                        raise ConfigError('Can not disable interface {} which is a member of {}').format(eth['intf'], bond)

                    if eth['address']:
                        raise ConfigError('Can not assign address to interface {} which is a member of {}').format(eth['intf'], bond)


    return None


def generate(eth):
    import pprint
    pprint.pprint(eth)
    return None


def apply(eth):
    e = EthernetIf(eth['intf'])
    # update interface description used e.g. within SNMP
    e.ifalias = eth['description']

    #
    # missing DHCP/DHCPv6 options go here
    #

    # ignore link state changes
    e.link_detect = eth['disable_link_detect']
    # disable ethernet flow control (pause frames)
    e.set_flow_control(eth['flow_control'])
    # configure ARP cache timeout in milliseconds
    e.arp_cache_tmp = eth['ip_arp_cache_tmo']
    # Enable proxy-arp on this interface
    e.proxy_arp = eth['ip_proxy_arp']
    # Enable private VLAN proxy ARP on this interface
    e.proxy_arp_pvlan = eth['ip_proxy_arp_pvlan']

    # Change interface MAC address - re-set to real hardware address (hw-id)
    # if custom mac is removed
    if eth['mac']:
        e.mac = eth['mac']
    else:
        e.mac = eth['hw_id']

    # Maximum Transmission Unit (MTU)
    e.mtu = eth['mtu']

    # Configure interface address(es)
    # - not longer required addresses get removed first
    # - newly addresses will be added second
    for addr in eth['address_remove']:
        e.del_addr(addr)
    for addr in eth['address']:
        e.add_addr(addr)

    # Enable/Disable interface
    if eth['disable']:
        e.state = 'down'
    else:
        e.state = 'up'

    # remove no longer required service VLAN interfaces (vif-s)
    for vif_s in eth['vif_s_remove']:
        e.del_vlan(vif_s)

    # create service VLAN interfaces (vif-s)
    for vif_s in eth['vif_s']:
        s_vlan = e.add_vlan(vif_s['id'], ethertype=vif_s['ethertype'])
        apply_vlan_config(s_vlan, vif_s)

        # remove no longer required client VLAN interfaces (vif-c)
        # on lower service VLAN interface
        for vif_c in vif_s['vif_c_remove']:
            s_vlan.del_vlan(vif_c)

        # create client VLAN interfaces (vif-c)
        # on lower service VLAN interface
        for vif_c in vif_s['vif_c']:
            c_vlan = s_vlan.add_vlan(vif_c['id'])
            apply_vlan_config(c_vlan, vif_c)

    # remove no longer required VLAN interfaces (vif)
    for vif in eth['vif_remove']:
        e.del_vlan(vif)

    # create VLAN interfaces (vif)
    for vif in eth['vif']:
        # QoS priority mapping can only be set during interface creation
        # so we delete the interface first if required.
        if vif['egress_qos_changed'] or vif['ingress_qos_changed']:
            e.del_vlan(vif['id'])

        vlan = e.add_vlan(vif['id'], ingress_qos=vif['ingress_qos'], egress_qos=vif['egress_qos'])
        apply_vlan_config(vlan, vif)

    return None

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        exit(1)
