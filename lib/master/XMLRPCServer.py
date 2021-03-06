#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software  Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# The Original Code is Copyright (C) 2010 by Sergey Sharybin
# All rights reserved.
#
# The Original Code is: all of this file.
#
# Contributor(s): none yet.
#
# ***** END GPL LICENSE BLOCK *****
#

import os
import socket

try:
    # python 3.0 and newer
    import xmlrpc.client
    import xmlrpc.server

except ImportError:
    import xmlrpclib
    import SimpleXMLRPCServer

    # small hack to make API py3-compatible
    class xmlrpc:
        client = xmlrpclib
        server = SimpleXMLRPCServer

    setattr(xmlrpc.client, 'Binary', xmlrpclib.Binary)

import master
import Logger

from SignalThread import SignalThread


class XMLRPCHandlers:
    """
    Set of XML-RPC handlers
    """

    class XMLRPCNode:
        def __init__(self):
            """
            Initialize XML-RPC node handlers
            """

            pass

        def register(self, host_info, client_info):
            """
            Register rendering node
            """

            render_server = master.Master().getRenderServer()

            return render_server.registerNode(host_info, client_info)

        def unregister(self, nodeUUID, client_info):
            """
            Register rendering node
            """

            render_server = master.Master().getRenderServer()

            node = render_server.getNode(nodeUUID)

            if node is None:
                return False

            return render_server.unregisterNode(node)

        def check(self, nodeUUID, client_info):
            """
            Check if node still walid
            """

            render_server = master.Master().getRenderServer()
            node = render_server.getNode(nodeUUID)

            return node != None

        def touch(self, nodeUUID, client_info):
            """
            Register rendering node
            """

            render_server = master.Master().getRenderServer()

            node = render_server.getNode(nodeUUID)

            if node is None:
                return False

            return render_server.touchNode(node)

        def logMessage(self, nodeUUID, message, client_info):
            """
            Log message from node
            """

            log_server = master.Master().getLogServer()

            source = 'node-' + nodeUUID

            if not log_server.hasSource(source):
                return False

            log_server.logMessage(source, message)

            return True

    class XMLRPCJob:
        def __init__(self):
            """
            Initialize XML-RPC job handlers
            """

            pass

        def register(self, options, client_info):
            """
            Register new job
            """

            render_server = master.Master().getRenderServer()

            return render_server.registerJob(options)

        def unregister(self, jobUUID, client_info):
            """
            Unregister job
            """

            render_server = master.Master().getRenderServer()

            job = render_server.getJob(jobUUID)
            if job is None:
                return job

            return render_server.unregisterJob(job)

        def requestTask(self, nodeUUID, client_info):
            """
            Request task for rendering node
            """

            render_server = master.Master().getRenderServer()

            node = render_server.getNode(nodeUUID)
            if node is None:
                return False

            return render_server.requestTask(node)

        def restartTask(self, nodeUUID, jobUUID, task_nr, client_info):
            """
            Restart task in queue
            """

            render_server = master.Master().getRenderServer()

            node = render_server.getNode(nodeUUID)
            if node is None:
                return False

            if not node.hasTask(jobUUID, task_nr):
                return False

            Logger.log('Job {0}: restart task {1} requested from node {2}' .
                format(jobUUID, task_nr, nodeUUID))

            node.unassignTask(jobUUID, task_nr)

            job = render_server.getJob(jobUUID)
            job.restartTask(task_nr)
            job.ignoreNodeForTask(node, task_nr)

            return True

        def getBlendChunk(self, nodeUUID, jobUUID, task_nr,
                          chunk_nr, client_info):
            """
            Get chunk of .blend file
            """

            render_server = master.Master().getRenderServer()

            node = render_server.getNode(nodeUUID)
            if node is None:
                # XXX: value for pre-py3k only
                return {'CANCELLED': True}

            if not node.hasTask(jobUUID, task_nr):
                # XXX: value for pre-py3k only
                return {'CANCELLED': True}

            job = render_server.getJob(jobUUID)

            if job is None:
                # XXX: value for pre-py3k only
                return {'CANCELLED': True}

            chunk = job.getBlendChunk(chunk_nr)
            if chunk is None:
                # XXX: value for pre-py3k only
                return {'FINISHED': True}

            return xmlrpc.client.Binary(chunk)

        def getBlendChecksum(self, jobUUID, client_info):
            """
            Get checksum of .blend file
            """

            render_server = master.Master().getRenderServer()

            job = render_server.getJob(jobUUID)

            if job is None:
                return ''

            return job.getBlendChecksum()

        def putRenderChunk(self, nodeUUID, jobUUID, task_nr, fname, chunk,
                           chunk_nr, client_info):
            """
            Put chunk of rendered file
            """

            full_file = '{0} (job {1}, task {2})' . \
                    format(fname, jobUUID, task_nr)

            # XXX: should it be something else?
            if fname.find(os.path.sep) >= 0:
                Logger.log('Attempt to write to invalid file {0}, ip {1}' .
                    format(full_file, client_info['address'][0]))
                return False

            render_server = master.Master().getRenderServer()

            node = render_server.getNode(nodeUUID)
            if node is None:
                Logger.log(('Attempt to write file {0} from un-registered ' +
                            'node {1} (ip {2})') .
                    format(full_file, nodeUUID, client_info['address'][0]))
                return False

            if not node.hasTask(jobUUID, task_nr):
                Logger.log(('Attempt to write file {0} from wrong ' +
                            'node {1} (ip {2})') .
                    format(full_file, nodeUUID, client_info['address'][0]))

                # Active task mistmatch. Happens after jobs after network
                # lags and jobs reassignment
                return False

            job = render_server.getJob(jobUUID)
            if job is None:
                Logger.log(('Attempt to write file {0} for wrong ' +
                            'job {1} from node {2} (ip {3})') .
                    format(full_file, jobUUID, nodeUUID,
                           client_info['address'][0]))

                return False

            if chunk != False:
                chunk = chunk.data

            return job.putRenderChunk(fname, chunk, chunk_nr)

        def putBlendChunk(self, jobUUID, chunk, chunk_nr, client_info):
            """
            Get chunk of .blend file
            """

            render_server = master.Master().getRenderServer()

            job = render_server.getJob(jobUUID)
            if job is None:
                return False

            if chunk != False:
                chunk = chunk.data

            return job.putBlendChunk(chunk, chunk_nr)

        def taskComplete(self, nodeUUID, jobUUID, task_nr, client_info):
            """
            Mark task as DONE
            """

            render_server = master.Master().getRenderServer()

            node = render_server.getNode(nodeUUID)
            if node is None:
                return False

            if not node.hasTask(jobUUID, task_nr):
                # Active task mistmatch. Happens after jobs after network
                # lags and jobs reassignment

                Logger.log(('Attempt to copmlete task {0} of job {1}' +
                            'from wrong node {1} (ip {2})') .
                    format(task_nr, jobUUID, nodeUUID,
                           client_info['address'][0]))

                return False

            # Unassign task from node
            node.unassignTask(jobUUID, task_nr)

            job = render_server.getJob(jobUUID)
            if job is None:
                return False

            return render_server.taskComplete(job, task_nr)

    def __init__(self):
        """
        Initialize XML-RPC handlers
        """

        self.job = XMLRPCHandlers.XMLRPCJob()
        self.node = XMLRPCHandlers.XMLRPCNode()

    def requestStop(self, clientInfo):
        """
        Stop serve
        """

        render_server = naster.Master().getRenderServer()

        render_server.requestStop()

        return True


class XMLRPCRequestHandler(xmlrpc.server.SimpleXMLRPCRequestHandler):
    """
    Request handler class
    """

    def __init__(self, request, client_address, server):
        """
        Initialize request handler
        """

        self.client_address = client_address

        # XXX: We'd better get rid of manual server descriptor passing
        self.server = server

        xmlrpc.server.SimpleXMLRPCRequestHandler.__init__(self, request,
            client_address, server)

    def log_request(self,  code='-', size='-'):
        """
        Request printer
        """

        pass

    def _dispatch(self, method, params):
        """
        Dispatches the XML-RPC method
        """

        # Append client info
        params += ({'address': self.client_address},)

        func = None
        try:
            # check to see if a matching function has been registered
            func = self.server.funcs[method]
        except KeyError:
            if self.server.instance is not None:
                # check for a _dispatch method
                if hasattr(self.server.instance, '_dispatch'):
                    return self.server.instance._dispatch(method, params)
                else:
                    # call instance method directly
                    try:
                        func = xmlrpc.server.resolve_dotted_attribute(
                                self.server.instance,
                                method,
                                self.server.allow_dotted_names)
                    except AttributeError:
                        pass

        if func is not None:
            return func(*params)
        else:
            raise Exception('method "%s" is not supported' % method)


class XMLRPCServer(xmlrpc.server.SimpleXMLRPCServer, SignalThread):
    """
    XML-RPC access for render frame server
    """

    def __init__(self, address):
        """
        Initialize XML-RPC server
        """

        SignalThread.__init__(self, name='XMLRPCServerThread')
        xmlrpc.server.SimpleXMLRPCServer.__init__(self, address,
            XMLRPCRequestHandler)

        self.handlers = XMLRPCHandlers()
        self.register_instance(self.handlers)
        self.address = address
        self.allow_dotted_names = True
        self.stop_flag = False

        self.register_function(lambda client_info: 'OK', 'ping')

    def server_bind(self):
        """
        Bind server to socket
        """

        # reuse address for fast restart after crash
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        xmlrpc.server.SimpleXMLRPCServer.server_bind(self)

    def verify_request(self, request, client_address):
        """
        Chack if RPC is avaliable for client
        """

        #
        # TODO: implement this
        #

        return True

    def run(self):
        """
        Serve requests till server stop
        """

        Logger.log('XML-RPC started at {0}:{1}' .
            format(self.address[0], self.address[1]))

        while not self.stop_flag:
            self.handle_request()

    def requestStop(self):
        """
        Stop server
        """

        self.stop_flag = True

        # Actually, server would be stopped after next request handle
        # so create one to prevent locking

        self._createDummyRequest()

    def _createDummyRequest(self):
        """
        Create dummy request to self
        """

        url = 'http://{0}:{1}' . format(self.address[0], self.address[1])
        proxy = xmlrpc.client.ServerProxy(url)
        proxy.ping()
