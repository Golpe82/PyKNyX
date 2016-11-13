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

Application layer group data management

Implements
==========

 - B{L_DataService}
 - B{L_DSValueError}

Documentation
=============

Usage
=====

@author: Frédéric Mantegazza
@copyright: (C) 2013-2015 Frédéric Mantegazza
@license: GPL
"""


import time
import threading

from pknyx.common.exception import PKNyXValueError
from pknyx.services.logger import Logger
from pknyx.stack.individualAddress import IndividualAddress
from pknyx.stack.priorityQueue import PriorityQueue
from pknyx.stack.layer3.n_groupDataListener import N_GroupDataListener
from pknyx.stack.transceiver.transceiverLSAP import TransceiverLSAP
from pknyx.stack.transceiver.transmission import Transmission
from pknyx.stack.cemi.cemiLData import CEMILData


class L_DSValueError(PKNyXValueError):
    """
    """


class L_DataService(threading.Thread, TransceiverLSAP):  # @todo: do not inherits Thread
    """ L_DataService class

    @ivar _individualAddress: own Individual Address
    @type _individualAddress: str or L{IndividualAddress<pknyx.core.individualAddress>}

    @ivar _inQueue: input queue
    @type _inQueue: L{PriorityQueue}

    @ivar _outQueue: output queue
    @type _outQueue: L{PriorityQueue}

    @ivar _ldl: link data listener
    @type _ldl: L{L_DataListener<pknyx.core.layer2.l_dataListener>}

    @ivar _running: True if thread is running
    @type _running: bool
    """
    def __init__(self, priorityDistribution, individualAddress=IndividualAddress("0.0.0")):
        """

        @param individualAddress: own Individual Address
        @type individualAddress: str or L{IndividualAddress}

        @param priorityDistribution:
        @type priorityDistribution:

        raise L_DSValueError:
        """
        super(L_DataService, self).__init__(name="LinkLayer")

        if not isinstance(individualAddress, IndividualAddress):
            individualAddress = IndividualAddress(individualAddress)
        self._individualAddress = individualAddress

        self._inQueue  = PriorityQueue(priorityDistribution)
        self._outQueue = PriorityQueue(priorityDistribution)

        self._ldl = None

        self._running = False

        self.setDaemon(True)
        #self.start()

    @property
    def individualAddress(self):
        return self._individualAddress

    def setListener(self, ldl):
        """

        @param ldl: listener to use to transmit data
        @type ldl: L{L_GroupDataListener<pknyx.core.layer2.l_groupDataListener>}
        """
        self._ldl = ldl

    def putInFrame(self, cEMI):
        """ Set input frame

        @param cEMI:
        @type cEMI:
        """
        Logger().debug("L_DataService.putInFrame(): cEMI=%s" % cEMI)

        # Get priority from cEMI
        priority = cEMI.priority

        # Add to inQueue and notify inQueue handler
        self._inQueue.add(cEMI, priority)

    def getOutFrame(self):
        """ Get output frame

        Blocks until there is a transmission pending in outQueue, then returns this transmission

        @return: pending transmission in outQueue
        @rtype: L{Transmission}
        """
        transmission = self._outQueue.remove()
        return transmission

    def dataReq(self, cEMI):
        """
        """
        Logger().debug("L_DataService.dataReq(): cEMI=%s" % cEMI)

        # Add source address to cEMI
        cEMI.sourceAddress = self._individualAddress

        priority = cEMI.priority

        transmission = Transmission(cEMI.frame)
        transmission.acquire()
        try:
            self._outQueue.add(transmission, priority)

            while transmission.waitConfirm:
                transmission.wait()
        finally:
            transmission.release()

        return transmission.result

    def run(self):
        """ inQueue handler main loop
        """
        Logger().trace("L_DataService.run()")

        self._running = True
        while self._running:
            try:

                # Get incoming frame from inQueue
                cEMI = self._inQueue.remove()
                Logger().debug("L_DataService.run(): cEMI=%s" % cEMI)

                srcAddr = cEMI.sourceAddress
                if srcAddr != self._individualAddress:  # Avoid loop
                    if cEMI.messageCode == CEMILData.MC_LDATA_IND:  #in (CEMILData.MC_LDATA_CON, CEMILData.MC_LDATA_IND):
                        if self._ldl is None:
                            Logger().warning("L_GroupDataService.run(): not listener defined")
                        else:
                            self._ldl.dataInd(cEMI)

            except:
                Logger().exception("L_DataService.run()")  #, debug=True)

        Logger().trace("L_DataService.run(): ended")

    def stop(self):
        """ stop thread
        """
        Logger().trace("L_DataService.stop()")

        self._running = False


if __name__ == '__main__':
    import unittest

    # Mute logger
    Logger().setLevel('error')


    class L_DataServiceCase(unittest.TestCase):

        def setUp(self):
            pass

        def tearDown(self):
            pass

        def test_constructor(self):
            pass


    unittest.main()
