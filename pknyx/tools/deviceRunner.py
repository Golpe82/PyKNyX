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

Device (process) management.

Implements
==========

 - B{DeviceRunnerValueError}
 - B{DeviceRunner}

Documentation
=============

The main goal of this utility is to start/stop a device, and to create a fresh device from a template.
Ths usage of this utility is not mandatory, but handles some annoying logger init suffs.

Usage
=====

Should be used from an executable script. See scripts/pknyx-admin.py.

@author: Frédéric Mantegazza
@copyright: (C) 2013-2015 Frédéric Mantegazza
@license: GPL
"""


import os
import os.path
import imp
import sys
import time

from pknyx.common import config
from pknyx.common.exception import PKNyXValueError
from pknyx.services.logger import logging; logger = logging.getLogger(__name__)
from pknyx.services.scheduler import Scheduler
from pknyx.services.groupAddressTableMapper import GroupAddressTableMapper
from pknyx.core.ets import ETS
from pknyx.stack.individualAddress import IndividualAddress
from pknyx.stack.groupAddress import GroupAddress, GroupAddressValueError


class DeviceRunnerValueError(PKNyXValueError):
    """
    """


class DeviceRunner(object):
    """
    """
    def __init__(self, loggerLevel, devicePath, gadMapPath):
        """
        """
        super(DeviceRunner, self).__init__()

        sys.path.insert(0, devicePath)

        # Load user 'settings' module
        from settings import DEVICE_NAME, DEVICE_IND_ADDR

        # Init the logger
        if loggerLevel is not None:
            config.LOGGER_LEVEL = loggerLevel

        # DO NOT USE LOGGER BEFORE THIS POINT!
        Logger("%s-%s" % (DEVICE_NAME, DEVICE_IND_ADDR))
        logger.info("Logger level is '%s'" % config.LOGGER_LEVEL)

        logger.info("Device path is '%s'" % devicePath)
        logger.info("Device name is '%s'" % DEVICE_NAME)

        self._deviceIndAddr = DEVICE_IND_ADDR
        if not isinstance(self._deviceIndAddr, IndividualAddress):
            self._deviceIndAddr = IndividualAddress(self._deviceIndAddr)
        if self._deviceIndAddr.isNull:
            logger.warning("Device Individual Address is null")
        else:
            logger.info("Device Individual Address is '%s'" % self._deviceIndAddr)

        # Load GAD map table
        mapper = GroupAddressTableMapper()
        mapper.loadFrom(gadMapPath)

        self.ets = ETS()

    def _doubleFork(self):
        """ Double fork.
        """
        if os.fork() != 0:  # launch child and ...
            os._exit(0)     # kill off parent
        os.setsid()
        os.chdir("/")
        os.umask(0)
        if os.fork() != 0:  # fork again so we are not a session leader
            os._exit(0)

        # Close stdxxx
        sys.stdin.close()
        sys.__stdin__ = sys.stdin = open('/dev/null','r')

        sys.stdout.close()
        sys.stdout = sys.__stdout__ = open('/dev/null','w')
        sys.stderr.close()
        sys.stderr = sys.__stderr__ = open('/dev/null','w')

        # ??? does not work if enable
        #for fd in xrange(4, 1024):
            #try:
                #os.close(fd)
            #except OSError:
                #pass

    def check(self, printGroat=False):
        """
        """

        # Create device from user 'device' module
        from device import DEVICE
        self._device = DEVICE(self._deviceIndAddr)

        ets.register(self._device)
        ets.weave(self._device)

        if printGroat:
            logger.info(ets.getGrOAT(self._device, "gad"))
            logger.info(ets.getGrOAT(self._device, "go"))

    def run(self, daemon=False):
        """
        """
        logger.trace("Device.run()")

        self.check()

        if daemon:
            logger.info("Run process as daemon...")
            self._doubleFork()

        self._device.start()
        Scheduler().start()
        time.sleep(1)  # wait for things to start
        try:
            self._device.mainLoop()

        except KeyboardInterrupt:
            logger.warning("Device execution canceled (SIGTERM)")

        except:
            logger.exception("deviceRunner.run()")

        finally:
            Scheduler().stop()
            self._device.stop()
            self._device.shutdown()


if __name__ == '__main__':
    import unittest

    # Mute logger
    logger.root.setLevel(logging.ERROR)


    class DeviceRunnerTestCase(unittest.TestCase):

        def setUp(self):
            pass

        def tearDown(self):
            pass

        def test_constructor(self):
            pass


    unittest.main()
