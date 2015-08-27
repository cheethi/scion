# Copyright 2015 ETH Zurich
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
:mod:`socket` --- Low-level socket library
==========================================
"""
# Stdlib
import logging
import selectors
from socket import (
    AF_INET,
    AF_INET6,
    SOCK_DGRAM,
    SOL_SOCKET,
    SO_REUSEADDR,
    socket,
)

# SCION
from lib.defines import (
    ADDR_IPV4_TYPE,
    ADDR_IPV6_TYPE,
    SCION_BUFLEN,
)


class UDPSocket(object):
    """
    Thin wrapper around BSD/POSIX UDP sockets.
    """
    def __init__(self, bind=None, addr_type=ADDR_IPV6_TYPE):
        """
        Initialise a socket of the specified type, and optionally bind it to an
        address/port.

        :param tuple bind:
            Optional tuple of (`str`, `int`) describing the address and port to
            bind to, respectively.
        :param addr_type:
            Socket domain. Must be one of :const:`~lib.defines.ADDR_IPV4_TYPE`,
            :const:`~lib.defines.ADDR_IPV6_TYPE` (default).
        """
        assert addr_type in (ADDR_IPV4_TYPE, ADDR_IPV6_TYPE)
        self._addr_type = addr_type
        af_domain = AF_INET6
        if self._addr_type == ADDR_IPV4_TYPE:
            af_domain = AF_INET
        self.sock = socket(af_domain, SOCK_DGRAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if bind:
            self.bind(*bind)

    def bind(self, addr, port):
        """
        Bind socket to the specified address & port. If `addr` is ``None``, the
        socket will bind to all interfaces.

        :param str addr: Address to bind to (can be ``None``, see above).
        :param int port: Port to bind to.
        """
        if addr is None:
            addr = "::"
            if self._domain == ADDR_IPV4_TYPE:
                addr = ""
        self.sock.bind((addr, port))
        logging.info("Bound to %s:%d", addr, port)

    def send(self, data, dst):
        """
        Send data to a specified destination.

        :param bytes data: Data to send.
        :param tuple dst:
            Tuple of (`str`, `int`) describing the destination address and port,
            respectively.
        """
        self.sock.sendto(data, dst)

    def recv(self):
        """
        Read data from socket.

        :returns:
            Tuple of (`bytes`, (`str`, `int`) containing the data, and remote
            host/port respectively.
        """
        return self.sock.recvfrom(SCION_BUFLEN)

    def close(self):
        """
        Close the socket.
        """
        self.sock.close()


class UDPSocketMgr(object):
    """
    :class:`UDPSocket` manager.
    """
    def __init__(self):
        self._sel = selectors.DefaultSelector()

    def add(self, udpsock):
        """
        Add new socket.

        :param UDPSocket sock: UDPSocket to add.
        """
        self._sel.register(udpsock.sock, selectors.EVENT_READ, udpsock)

    def remove(self, udpsock):
        """
        Remove socket.

        :param UDPSocket sock: UDPSocket to remove.
        """
        self._sel.unregister(udpsock.sock)

    def select_(self, timeout=None):
        """
        Return the set of UDPSockets that have data pending.

        :param float timeout:
            Number of seconds to wait for at least one UDPSocket to become
            ready. ``None`` means wait forever.
        """
        ret = []
        for key, _ in self._sel.select(timeout=timeout):
            ret.append(key.data)
        return ret

    def close(self):
        """
        Close all sockets.
        """
        for entry in list(self._sel.get_map().values()):
            udpsock = entry.data
            self.remove(udpsock)
            udpsock.close()
        self._sel.close()