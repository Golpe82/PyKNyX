# -*- coding: utf-8 -*-

""" Python KNX framework

License
=======

 - B{PyKNyX} (U{https://github.com/knxd/pyknyx}) is Copyright:
  - © 2016-2017 Matthias Urlichs
  - PyKNyX is a fork of pKNyX
   - © 2013-2015 Frédéric Mantegazza

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

Notifier management

Implements
==========

 - B{Notifier}
 - B{NotifierValueError}

Documentation
=============

One of the nice feature of B{PyKNyX} is to be able to register some L{FunctionalBlock<pyknyx.core.functionalBlock>}
sub-classes methods to have them executed at specific times. For that, B{PyKNyX} uses the nice third-party module
U{APScheduler<http://pythonhosted.org/APScheduler>}.

The idea is to use the decorators syntax to register these methods.

Unfortunally, a decorator can only wraps a function. But what we want is to register an instance method! How can it be
done, as we didn't instanciated the class yet?

Luckily, such classes are not directly instanciated by the user, but through the L{ETS<pyknyx.core.ets>} register()
method. So, here is how this registration is done.

Instead of directly using the APScheduler, the Notifier class below provides the decorators we need, and maintains a
list of names of the decorated functions, in _pendingFuncs.

Then, when a new instance of the FunctionalBlock sub-class is created, in ETS.register(), we call the
Notifier.doRegisterJobs() method which tried to retrieve the bounded method matching one of the decorated functions.
If found, the method is registered in APScheduler.

Notifier also adds a listener to be notified when a decorated method call fails to be run, so we can log it.

Usage
=====

@author: Frédéric Mantegazza
@copyright: (C) 2013-2015 Frédéric Mantegazza
@license: GPL

@todo: solve name conflicts between blocks -> also store block name when registering?

@todo: use metaclass for FunctionalBlock to store funcs in the class itself. Is it usefull?
--------------------
Juste une idée comme ça: tu pourrais aussi utiliser une métaclasse. Cela permet de personnaliser la création d'une classe. La création de la classe a lieu après que son corps ait été interprété; cela veut dire que les décorateurs sont exécutés avant.

Donc pour les décorateurs, pas grand chose ne change: ils stockent les fonctions décorées dans une liste (funcs).
La métaclasse va récupérer les fonctions; comme la classe est maintenant connue (en cours de création, en fait), tu peux les associer à celle-ci (par exemple faire de funcs un attribut de la classe).

[edit]... ou bien avec un décorateur de classe (Python 2.6+), ça devrait fonctionner aussi
---------------------
See: http://www.developpez.net/forums/d1361199/autres-langages/python-zope/general-python/apschduler-methodes-classe/#post7387938

Idem for scheduler.
"""

import six

from pyknyx.common.exception import PyKNyXValueError
from pyknyx.common.utils import reprStr
from pyknyx.common.utils import func_name, meth_name,meth_self,meth_func
from pyknyx.common.singleton import Singleton
from pyknyx.services.logger import logging; logger = logging.getLogger(__name__)

scheduler = None


class NotifierValueError(PyKNyXValueError):
    """
    """

@six.add_metaclass(Singleton)
class Notifier(object):
    """ Notifier class

    @ivar _pendingFuncs:
    @type _pendingFuncs: list

    @ivar _datapointJobs:
    @type _registeredJobs: dict
    """

    def __init__(self):
        """ Init the Notifier object

        raise NotifierValueError:
        """
        super(Notifier, self).__init__()

        self._pendingFuncs = []
        self._datapointJobs = {}
        #self._groupJobs = {}

    def _execute(self, method, event):
        """ Execute given method

        Used to add the try/except statement when launched in a thread

        @todo: add a more explicite message for enduser?
        """
        try:
            method(event)
        except:
            logger.exception("Notifier._execute()")

    def addDatapointJob(self, func, dp, condition="change", thread=False):
        """ Add a job for a datapoint change

        @param func: job to register
        @type func: callable

        @param dp: name of the datapoint
        @type dp: str

        @param condition: watching condition, in ("change", "always")
        @type condition: str

        @param thread: flag to execute job in a thread
        @type thread: bool
        """
        logger.debug("Notifier.addDatapointJob(): func=%s, dp=%s" % (repr(func), repr(dp)))

        if condition not in ("change", "always"):
            raise NotifierValueError("invalid condition (%s)" % repr(condition))

        self._pendingFuncs.append(("datapoint", func, (dp, condition, thread)))

    def datapoint(self, dp, *args, **kwargs):
        """ Decorator for addDatapointJob()
        """
        logger.debug("Notifier.datapoint(): dp=%s, args=%s, kwargs=%s" % (repr(dp), repr(args), repr(kwargs)))

        def decorated(func):
            """ We don't wrap the decorated function!
            """
            self.addDatapointJob(func, dp, *args, **kwargs)

            return func

        return decorated

    #def addGroupJob(self, func, gad):
        #""" Add a job for a group adress activity

        #@param func: job to register
        #@type func: callable

        #@param gad: group address
        #@type gad: str or L{GroupAddress}
        #"""
        #logger.debug("Notifier.addGroupJob(): func=%s" % repr(func))

        #self._pendingFuncs.append(("group", func, gad))

    #def group(self, **kwargs):
        #""" Decorator for addGroupJob()
        #"""
        #logger.debug("Notifier.datapoint(): kwargs=%s" % repr(kwargs))

        #def decorated(func):
            #""" We don't wrap the decorated function!
            #"""
            #self.addGroupJob(func, **kwargs)

            #return func

        #return decorated

    def doRegisterJobs(self, obj):
        """ Really register jobs

        @param obj: instance for which a method may have been pre-registered
        @type obj: object
        """
        logger.debug("Notifier.doRegisterJobs(): obj=%s" % repr(obj))

        for type_, func, args in self._pendingFuncs:
            logger.debug("Notifier.doRegisterJobs(): type_=\"%s\", func=%s, args=%s" % (type_, func_name(func), repr(args)))

            method = getattr(obj, func_name(func), None)
            if method is not None:
                logger.debug("Notifier.doRegisterJobs(): add method %s() of %s" % (meth_name(method), meth_self(method)))

                if meth_func(method) is func:  # avoid name clash between FB methods

                    if type_ == "datapoint":
                        dp, condition, thread = args
                        try:
                            self._datapointJobs[obj][dp].append((method, condition, thread))
                        except KeyError:
                            try:
                                self._datapointJobs[obj][dp] = [(method, condition, thread)]
                            except KeyError:
                                self._datapointJobs[obj] = {dp: [(method, condition, thread)]}

                    #elif type_ == "group":
                        #gad = args
                        #try:
                            #self._groupJobs[gad].append(method)
                        #except KeyError:
                            #self._groupJobs[gad] = [method]

    def datapointNotify(self, obj, dp, oldValue, newValue):
        """ Notification of a datapoint change

        This method is called when a datapoint value changes.

        @param obj: owner of the datapoint
        @type obj: <FunctionalBloc>

        @param dp: name of the datapoint
        @type dp: str

        @param oldValue: previous value of the datapoint
        @type oldValue: depends on datapoint type

        @param newValue: new value of the datapoint
        @type newValue: depends on datapoint type
        """
        logger.debug("Notifier.datapointNotify(): obj=%s, dp=%s, oldValue=%s, newValue=%s" % (obj.name, dp, repr(oldValue), repr(newValue)))

        if obj in self._datapointJobs.keys():
            if dp in self._datapointJobs[obj].keys():
                for method, condition, thread_ in self._datapointJobs[obj][dp]:
                    if oldValue != newValue and condition == "change" or condition == "always":
                        try:
                            logger.debug("Notifier.datapointNotify(): trigger method %s() of %s" % (meth_name(method), meth_self(method)))
                            event = dict(name="datapoint", dp=dp, oldValue=oldValue, newValue=newValue, condition=condition, thread=thread_)

                            if thread_:
                                thread.start_new_thread(self._execute, (method, event))
                                #TODO: register threads, so they can be killed (how?) when stopping the device
                            else:
                                self._execute(method, event)
                        except:
                            logger.exception("Notifier.datapointNotify()")

    def printJobs(self):
        """ Print registered jobs
        """

