# -*- coding: utf-8 -*-

import smtplib
import email.mime.text

from pknyx.api import FunctionalBlock
from pknyx.api import logger, schedule, notify

import settings


class AlertFB(FunctionalBlock):
    DP_01 = dict(name="temp_1", access="input", dptId="9.001", default=19.)
    DP_02 = dict(name="temp_2", access="input", dptId="9.001", default=19.)
    DP_03 = dict(name="door_1", access="input", dptId="1.009", default="Close")

    GO_01 = dict(dp="temp_1", flags="CWU", priority="low")
    GO_02 = dict(dp="temp_2", flags="CWU", priority="low")
    GO_03 = dict(dp="door_1", flags="CWU", priority="low")

    DESC = "Alert FB"

    def _sendEmail(self, msg):
        """ Send an e-mail
        """

        # Create a text/plain message
        message = email.mime.text.MIMEText(msg)

        message['Subject'] = settings.SUBJECT
        message['From'] = settings.FROM
        message['To'] = settings.TO

        # Send the message via SMTP server, but don't include the envelope header
        smtp = smtplib.SMTP(settings.SMTP)
        smtp.sendmail(message['From'], [message['To']], message.as_string())
        smtp.quit()

    @notify.datapoint(dp="temp_1", condition="change")
    @notify.datapoint(dp="temp_2", condition="change")
    def tempChanged(self, event):
        """ Method called when any of the 'temp_x' Datapoint change
        """
        logger.debug("%s: event=%s" % (self.name, repr(event)))

        dpName = event['dp']
        newValue = event['newValue']
        oldValue = event['oldValue']
        logger.info("%s: '%s' value changed from %s to %s" % (self.name, dpName, oldValue, newValue))

        # Check if new value is outside limits
        if not settings.TEMP_LIMITS[dpName][0] <= newValue <= settings.TEMP_LIMITS[dpName][1]:
            msg = "'%s' value (%s) is outside limits %s" % (dpName, newValue, repr(settings.TEMP_LIMITS[dpName]))
            logger.warning("%s: %s" % (self.name, msg))

            # Only send e-mail if old value was inside limits
            if settings.TEMP_LIMITS[dpName][0] <= oldValue <= settings.TEMP_LIMITS[dpName][1]:
                self._sendEmail(msg)

    @notify.datapoint(dp="door_1", condition="change")
    def doorChanged(self, event):
        """ Method called when 'door' Datapoint change
        """
        logger.debug("%s event=%s" % (self.name, repr(event)))

        dpName = event['dp']
        newValue = event['newValue']
        oldValue = event['oldValue']
        logger.info("%s: '%s' value changed from %s to %s" % (self.name, dpName, oldValue, newValue))

        # Check new value
        if newValue == "Open" and oldValue == "Close":
            msg = "'%s' value is now %s" % (dpName, newValue)
            logger.warning("%s: %s" % (self.name, msg))
            self._sendEmail(msg)
