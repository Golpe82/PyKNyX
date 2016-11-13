# -*- coding: utf-8 -*-

""" Python KNX framework

License
=======

 - B{pKNyX} (U{http://www.pknyx.org}) is Copyright:
  - (C) 2013-2015 Frédéric Mantegazza

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
or see:

 - U{http://www.gnu.org/licenses/gpl.html}

Module purpose
==============

UDP Multicast support.

Implements
==========

 - B{McastSockValueError}
 - B{MulticastSocketBase}
 - B{MulticastSocketReceive}
 - B{MulticastSocketTransmit}

Documentation
=============

See U{http://www.tldp.org/HOWTO/Multicast-HOWTO.html}

Usage
=====

@author: Frédéric Mantegazza
@author: Jakub Wroniecki
@copyright: (C) 2013-2015 Frédéric Mantegazza
@copyright: (C) 2009 Jakub Wroniecki, STANSAT
@license: GPL
"""


import socket
import struct
import six

from pknyx.common.exception import PKNyXValueError
from pknyx.services.logger import logging; logger = logging.getLogger(__name__)


class McastSockValueError(PKNyXValueError):
    """
    """


class MulticastSocketBase(socket.socket):
    """ Multicast socket
    """
    def __init__(self, localAddr, localPort, ttl=32, loop=1):
        """ Init the multicast socket base class

        @param localAddr: IP address used as local address
        @type: localAddr: str

        @param localPort: port used as local port
        @type: localPort: int

        @param ttl:    0  Restricted to the same host (won't be output by any interface)
                      1  Restricted to the same subnet (won't be forwarded by a router)
                    <32  Restricted to the same site, organization or department
                    <64 Restricted to the same region
                   <128 Restricted to the same continent
                   <255 Unrestricted in scope. Global
        @type ttl: int

        @param loop:
        @type loop: int
        """
        super(MulticastSocketBase, self).__init__(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        self._localAddr = localAddr
        self._localPort = localPort
        self._ttl= ttl
        self._loop = loop

        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except:
            logger.exception("MulticastSocketBase.__init__(): system doesn't support SO_REUSEPORT")
        self.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, ttl)
        self.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, loop)

        self._bind()

    def _bind(self):
        """
        """
        raise NotImplementedError

    @property
    def localAddress(self):
        return self._localAddr

    @property
    def localPort(self):
        return self._localPort


class MulticastSocketReceive(MulticastSocketBase):
    """
    """
    def __init__(self, localAddr, mcastAddr, mcastPort, timeout=1, ttl=32, loop=1):
        """
        """

        multicast = six.byte2int(socket.inet_aton(mcastAddr)) in range(224, 240)
        if not multicast:
            raise McastSockValueError("address is not a multicast destination (%s)" % repr(mcastAddr))

        self._mcastAddr = mcastAddr

        super(MulticastSocketReceive, self).__init__(localAddr, mcastPort, ttl, loop)

        self.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self._localAddr))
        value = struct.pack("=4sl", socket.inet_aton(mcastAddr), socket.INADDR_ANY)
        self.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, value)
        self.settimeout(timeout)

    def _bind(self):
        """

        @todo: use mcastAddr, instead of ""?
        """
        self.bind(("", self._localPort))

    def receive(self):
        """
        """
        return self.recvfrom(1024)


class MulticastSocketTransmit(MulticastSocketBase):
    """
    """
    def __init__(self, localAddr, localPort, mcastAddr, mcastPort, ttl=32, loop=1):
        """
        """
        super(MulticastSocketTransmit, self).__init__(localAddr, localPort, ttl, loop)

        self._mcastAddr = mcastAddr
        self._mcastPort = mcastPort

    def _bind(self):
        """
        """
        self.bind((self._localAddr, self._localPort))

    def transmit(self, data):
        """
        """
        l = self.sendto(data, (self._mcastAddr, self._mcastPort))
        if l > 0 and l < len(data):
            raise IOError("partial transmit: %d of %d to %s", l, len(data), self) 

