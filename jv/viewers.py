
# Copyright 2009, Mark Fassler <spin at eavesdown dot org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.

# Some snippets of this code originally came from the Python bindings
# for VTK, which I believe were written mostly by Prabhu Ramachandran,
# licensed under a BSD-style license.  The code is radically different
# at this point...

import logging
import sys
import os
import select
import time
import socket

import math
import numpy
import vtk

from jv.jvDatatypes import *
from jv.jvPaths import *

from jv.peercred import *

from jv import characters
from jv import xmlReader
from jv import primitives
from jv import restful

class VirtualWorldForPeople:
    def __init__(self):

        ### Create our VTK Render Window and Interactor
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground(1.0, 1.0, 1.0)
        self.renwin = vtk.vtkRenderWindow()
        self.renwin.AddRenderer(self.ren)
        self.renwin.SetSize(820,600)
        self.iren = vtk.vtkRenderWindowInteractor()
        self.iren.SetRenderWindow(self.renwin)
        self.iren.SetInteractorStyle(None)
        self.iren.LightFollowCameraOff()
        self.camera = self.ren.GetActiveCamera()
        ### gimme some point-n-click:
        self.picker = vtk.vtkPropPicker()
        self.lastPickedActor = 0

        ### Add some event handlers to the VTK Window Interactor
        #print "Adding TimerHandler."
        self.iren.AddObserver("TimerEvent", self.TimerHandler)
        self.iren.AddObserver("KeyPressEvent", self.KeyEvent)
        self.iren.AddObserver("KeyReleaseEvent", self.KeyEvent)
        self.iren.AddObserver("LeftButtonPressEvent", self.ButtonEvent)
        #self.iren.AddObserver("LeftButtonReleaseEvent", self.ButtonEvent)
        self.iren.AddObserver("MiddleButtonPressEvent", self.ButtonEvent)
        self.iren.AddObserver("MiddleButtonReleaseEvent", self.ButtonEvent)
        #self.iren.AddObserver("RightButtonPressEvent", self.ButtonEvent)
        #self.iren.AddObserver("RightButtonReleaseEvent", self.ButtonEvent)
        self.iren.AddObserver("MouseMoveEvent", self.MouseMove)
        self.iren.AddObserver("EnterEvent", self.MouseEnters)
        self.iren.AddObserver("LeaveEvent", self.MouseLeaves)

        ### These are "stateful" things that might be occuring in the Interactor
        self.XkeyRepeat = 1
        self.Wireframing = 0
        self.Headlighting = 0
        self.OutOfBodyPerspective = 0
        self.Rotating = 0
        self.translatingForward = 0
        self.translatingBackward = 0
        self.translatingUp = 0
        self.translatingDown = 0
        self.translatingLeft = 0
        self.translatingRight = 0
        self.turningLeft = 0
        self.turningRight = 0
        self.status = ""
        self.osdLines = ['', '', '', '']
        self.numberOfosdLines = len(self.osdLines)

        ##
        self.iAmMoving = 0
        self.PleaseRender = 0
        self.PleaseSendUDPpackets = 0

        ### Let's keep track of the things that we are rendering:
        self.maps = {} # collections of vtkActor's and vtkLight's
        self.characters = {} # vtkAssembly's that are connected to JIDs
        self.BoundTo = 0  # Which JID is "me"?

        self.timerCount = 0  # how long since we last rendered a frame?

        # We have a network UDP socket (jvIOSocket) to rapidly interact 
        # with other viewers.  We use UDP to send and receive MOVE commands, 
        # using a binary protocol, in case we ever want to do fast 
        # video-game-stuff on a LAN or something
        self.authorizedUDPpackets = {} # who are we receiving packets from?
        self.UDPRecipients = [] # who are we sending packets to?

        ##  The "IO" socket is for peer-to-peer communications
        self.jvIOSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.jvIOSocket.bind( ("localhost", 49005) )
        except socket.error, err:
            logging.critical("Failed to bind IO socket: %s" % err)
            sys.exit(1)
 
        self.jvIOSocketLocalAddr = self.jvIOSocket.getsockname()
        logging.info("IO socket is bound to: %s" % str(self.jvIOSocketLocalAddr))
        print "IO_socket:      UDP: %s:%i" % (self.jvIOSocketLocalAddr[0], self.jvIOSocketLocalAddr[1])
        self.jvIOSocket.setblocking(0)

        ##  The "MC" socket is for local master-slave communications
        try:
            os.remove(jvCommandSocketFileName)
        except:
            pass
        self.jvMCSocket = socket.socket(socket.AF_UNIX)
        try:
            self.jvMCSocket.bind(jvCommandSocketFileName)
        except socket.error, err:
            logging.critical("Failed to bind MC socket: %s" % err)
            sys.exit(1)
        self.jvMCSocket.listen(1)
        self.MCsocketList = [self.jvMCSocket]
        print "MC_socket:     UNIX: %s" % jvCommandSocketFileName
 

        ###  Create the OSDs (On-Screen Displays)  ("status" and "primary")
        self.osdStatus = vtk.vtkTextActor()
        #self.osdStatus.ScaledTextOff()   #deprecated in 5.4
        self.osdStatus.SetDisplayPosition(9, 10)
        self.osdStatusBackground = primitives.create2dRectangle(0, 5, 1600, 22)
        self.ren.AddActor2D(self.osdStatusBackground.actor)
        self.ren.AddActor2D(self.osdStatus)

        tprop = self.osdStatus.GetTextProperty()
        tprop.SetFontSize(14)
        tprop.SetFontFamilyToCourier()
        tprop.SetColor(0, 0, 0)

        self.osdPrimary = vtk.vtkTextActor()
        #self.osdPrimary.ScaledTextOff()   #deprecated in 5.4
        self.osdPrimary.SetDisplayPosition(9, 32)
        self.osdStatusBackground = primitives.create2dRectangle(0, 27, 1600, self.numberOfosdLines * 17 +24)
        self.ren.AddActor2D(self.osdStatusBackground.actor)
        self.ren.AddActor2D(self.osdPrimary)

        tprop = self.osdPrimary.GetTextProperty()
        tprop.SetFontSize(14)
        tprop.SetFontFamilyToCourier()
        tprop.SetColor(0, 0, 0)



    def TimerHandler(self, obj, event):
        #logging.debug( "TimerEvent")
        # the timers are one-shot, so we always have to create a new timer:
        self.iren.CreateTimer(0)
        # The one-shot timers occur every 10ms (100 fps).  Most things
        # don't need to occur nearly that fast, so we create a schedule:
        #  1 - if someone is requesting a render (typically 
        #      MouseMove->InputLocalMoveCommand), then we are willing to do 
        #      that at once per timer (~100 fps)
        #  3 - if we are moving (translating due to keyboard input), then we
        #      we are willing to render once per 3 timers (~33 fps)
        #  6 - most everything else occurs at once per 6 timers(~17 fps)
        self.timerCount += 1
        self.CheckForIO_UDPinput()
        #self.PleaseRender = 1
        if self.PleaseRender:
            self.macroAnimate()
            #self.animateObjects()
            self.positionCamera()
            self.renwin.Render()
            self.PleaseRender = 0
        if self.timerCount == 3 or self.timerCount == 6:
            #self.CheckForIO_UDPinput()
            if self.iAmMoving:
                self.PleaseRender = 1
        if self.timerCount == 6:
            self.timerCount = 0
            self.PleaseRender = 1
            self.CheckForMCinput()
            #self.CheckForIO_UDPinput()
            self.microAnimate()
            self.animateObjects()
            if self.PleaseSendUDPpackets:
                self.sendUDPpackets()
                self.PleaseSendUDPPackets = 0


    #####
    ##### Communication functions:
    #####
    #####   sendUDPpackets
    #####   CheckForIO_UDPinput
    #####   CheckForMCinput


    def sendUDPpackets(self):
        '''Send a UDP packet to each of the other viewers.'''
        if self.BoundTo:
            (x, y, z) = self.characters[self.BoundTo].assembly.GetPosition()
            (phi, roll, theta) = self.characters[self.BoundTo].assembly.GetOrientation()
            (headPhi, headRoll, headTheta) = self.characters[self.BoundTo].actors['head'].GetOrientation()
            moveCommand = {}
            moveCommand['userID'] = 0
            moveCommand['command'] = 0x03
            moveCommand['subcommand'] = 0
            moveCommand['x'] = x
            moveCommand['y'] = y
            moveCommand['z'] = z
            moveCommand['vx'] = self.characters[self.BoundTo].velocity[0]
            moveCommand['vy'] = self.characters[self.BoundTo].velocity[1]
            moveCommand['vz'] = self.characters[self.BoundTo].velocity[2]
            moveCommand['theta'] = theta
            moveCommand['phi'] = phi
            moveCommand['roll'] = roll
            moveCommand['headTheta'] = headTheta
            moveCommand['headPhi'] = headPhi
            moveCommand['headRoll'] = headRoll
            moveCommand['omega'] = self.characters[self.BoundTo].omega
            packet = packMoveCommandUDP(moveCommand)
            for recipient in self.UDPRecipients:
                try:
                    self.jvIOSocket.connect(recipient)
                except socket.error, err:
                    logging.error("Failed to set destination IP address for UDP packet: %s" % err)
                try:
                    self.jvIOSocket.send(packet)
                except socket.error, err:
                    logging.error("Failed to send UDP packet: %s" % err)

    def CheckForIO_UDPinput(self):
        try:
            inputPacket, addr = self.jvIOSocket.recvfrom(1024)
        except:
            pass
        else:
            if inputPacket:
                if len(inputPacket) > 4:
                    if (inputPacket[2] == '\x01') or (inputPacket[2] == '\x02') or (inputPacket[2] == '\x03'): # moveCommand
                        try:
                            moveCommand = unpackMoveCommandUDP(inputPacket)
                        except:
                            pass
                        else:
                            try:
                                jid = self.authorizedUDPpackets[addr][moveCommand['userID']]
                            except:
                                pass
                            else:
                                self.InputUDPMoveCommand(jid, moveCommand)
                    elif inputPacket[2] == '\x04': #microAnimate command
                        try:
                            microAnimateCommand = unpackMicroAnimateCommandUDP(inputPacket)
                        except:
                            pass
                        else:
                            try:
                                jid = self.authorizedUDPpackets[addr][microAnimateCommand['userID']]
                            except:
                                pass
                            else:
                                self.InputUDPMicroAnimateCommand(jid, microAnimateCommand)
                                #self.renwin.Render()
                                self.PleaseRender = 1
				
                # Let's go ahead and empty out the queue:
                self.CheckForIO_UDPinput()


    def CheckForMCinput(self):
        inputs, outputs, errors = select.select(self.MCsocketList, [], [], 0)
        for input in inputs:
            if input == self.jvMCSocket:
                conn, addr = self.jvMCSocket.accept()
                #userUID, userGID = getpeerid(conn)
                self.MCsocketList.append(conn)
                conn.send("Jaivis Viewer.  Connection number: %d\nReady.\n" % (len(self.MCsocketList)-1))
                conn.send("> ")
            else:
                try:
                    inputPacket = input.recv(1024)
                except:
                    logging.error('Error while attempting to receive data from MC socket')
                if inputPacket:
                    try:
                        restful.RESTfulHandler(self, input, inputPacket)
                    except:
                        logging.error('Failed to execute self.RESTful()')
                else:
                    self.MCsocketList.remove(input)
                    logging.info('An MC socket has been disconnected.')
                    logging.info('There are now %d MC socket connections.' % (len(self.MCsocketList) - 1))
                # Let's go ahead and empty out the queue:
                self.CheckForMCinput()

    ####
    #### Virtual World functions:
    ####
    ####   AnnounceTransport
    ####   LoadMap
    ####   LoadCharacter
    ####   BindTo
    ####   RemoveCharacter

    def PostOSD(self, text):
        for i in range(self.numberOfosdLines - 1):
            self.osdLines[i] = self.osdLines[i + 1]
        self.osdLines[self.numberOfosdLines - 1] = text
        outputString = '\n'.join(self.osdLines)
        self.osdPrimary.SetInput(outputString)

    def AnnounceTransport(self):
        '''Announce our IP address and port number.'''
        print "Jaivis/1.0 200 OK"
        returnString = self.jvIOSocketLocalAddr[0] + ' ' + \
           str(self.jvIOSocketLocalAddr[1]) + '/udp\n'
        sys.stdout.write(returnString)

    def LoadMap(self, mapname):
        '''Loads a map (typically a building) for the characters to walk around in.'''
        self.status = "Loading map: " + str(mapname)
        self.osdStatus.SetInput(self.status)
        self.renwin.Render()
        if not mapname in self.maps:
            try:
                self.maps[mapname] = xmlReader.MapReader(mapname)
            except:
                logging.error('Failed to load map "%s"' % mapname)
                returnString = "Jaivis/1.0 400 Failed"
            else:
                returnString = "Jaivis/1.0 200 OK"
                try:
                    self.ren.SetBackground(self.maps[mapname].bgcolor)
                except:
                    pass
                for actor in self.maps[mapname].actors:
                    logging.info('Adding actor "%s" from map "%s"' % (actor, mapname))
                    self.ren.AddActor(self.maps[mapname].actors[actor])
                for assembly in self.maps[mapname].assemblies:
                    logging.info('Adding assembly "%s" from map "%s"' % (assembly, mapname))
                    self.ren.AddActor(self.maps[mapname].assemblies[assembly])
                for light in self.maps[mapname].lights:
                    logging.info('Adding light "%s" from map "%s"' % (light, mapname))
                    self.ren.AddLight(self.maps[mapname].lights[light])
                # Turn off camera headlights
                self.renwin.Render()
                if self.Headlighting == 0:
                    lights = self.ren.GetLights()
                    lights.InitTraversal()
                    lightList = []
                    lightList.append(lights.GetNextItem())
                    lightList[0].SetIntensity(0.0)
        else:
            returnString = "Map %s already exists." % mapname
        self.status = "Done"
        self.osdStatus.SetInput(self.status)
        self.renwin.Render()
        return returnString


    def LoadCharacter(self, jid, avatarSettings):
        '''Create an avatar for a particular JID, and add it to the renderer.'''
        self.status = "Loading character: " + str(jid)
        self.osdStatus.SetInput(self.status)
        self.renwin.Render()
        if not jid in self.characters:
            try:
                character = characters.AllClasses[avatarSettings['race']](jid)
            except:
                logging.error("    Failed to create <" + jid + "> as a " + avatarSettings['race'])
            else:
                logging.info("    Created <" + jid + "> as a " + avatarSettings['race'])
            try:
                self.ren.AddActor(character.assembly)
                self.characters[character.jid] = character
            except:
                logging.error("    Failed to add " + jid + " to the renderer")
            else:
                logging.info("    Added <" + jid + "> to the renderer")
                returnString = "Jaivis/1.0 200 OK"
                if ('x' in avatarSettings) and ('y' in avatarSettings) and ('z' in avatarSettings):
                    position = ( float(avatarSettings['x']), float(avatarSettings['y']), float(avatarSettings['z']))
                    try:
                        self.characters[jid].assembly.SetPosition(position)
                    except:
                        logging.error('Failed to SetPosition() in LoadCharacter()')

            #try:
            #    self.ren.AddActor2D(character.caption)
            #    self.ren.AddActor(character.caption)
            #except:
            #    print "erg."
        else:
            returnString = "Character %s already exists." % jid
        self.status = "Done"
        self.osdStatus.SetInput(self.status)
        self.renwin.Render()
        return returnString

    def BindTo(self, jid):
        "Bind the camera and user interaction to a specific character."
        if self.characters.__contains__(jid):
            self.BoundTo = jid
            logging.info("I am bound to: %s " % self.BoundTo)
        else:
            logging.error("  Failed to bind to <%s> .  JID not listed here." % jid)

    def RemoveCharacter (self, jid):
        "Removes a character from the renderer"
        self.ren.RemoveActor(self.characters[jid].assembly)
        self.characters.__delitem__(jid)

    def RemoveMap (self, mapname):
        "Removes a character from the renderer"
        for actor in self.maps[mapname].actors:
            logging.info('Removing actor "%s" from map "%s"' % (actor, mapname))
            self.ren.RemoveActor(self.maps[mapname].actors[actor])
        for assembly in self.maps[mapname].assemblies:
            logging.info('Removing assembly "%s" from map "%s"' % (assembly, mapname))
            self.ren.RemoveActor(self.maps[mapname].assemblies[assembly])
        for light in self.maps[mapname].lights:
            logging.info('Removing light "%s" from map "%s"' % (light, mapname))
            self.ren.RemoveLight(self.maps[mapname].lights[light])
        try:
            nothing = self.maps[mapname].bgcolor
        except:
            pass
        else:
            self.ren.SetBackground(1.0, 1.0, 1.0)
        del self.maps[mapname]
        print "Jaivis/1.0 200 OK"

    ####
    #### Convert commands into macroAnimations.  No animation is done here.  
    ####
    ####    For other users:  we recieve UDP packets, and convert that into our own
    ####      data structures (including position and velocity, which will cause
    ####      macroAnimation).  
    ####
    ####    For our own (bound) JID:  we recieve keyboard commands, and convert that
    ####      into our own data structures (position and velocity).  
    ####
    ####
    ####   InputUDPMoveCommand  -- take a UDP "move" command and apply it to our data structures
    ####   InputLocalMoveCommand  -- take the local user's keyboard and mouse movements, and apply 
    ####                           that data to our bound character.  

    def InputUDPMoveCommand(self, jid, args):
        '''Move a single Avatar (ie, JID) to somewhere on the map.  Also does velocity and rotation.'''
        try:
            self.characters[jid].assembly.SetPosition(args["x"], args["y"], args["z"])
            self.characters[jid].assembly.SetOrientation(args['phi'], args['roll'], args["theta"])
            self.characters[jid].actors['head'].SetOrientation(args['headPhi'], args['headRoll'], args['headTheta'])
        except:
            logging.error("    Failed to move <" + jid + ">")
        else:
            self.characters[jid].posTimeStamp = time.time()
        if args['command'] == 1:
            self.characters[jid].axisOfRotation = 'x'
        if args['command'] == 2:
            self.characters[jid].axisOfRotation = 'y'
        if args['command'] == 3:
            self.characters[jid].axisOfRotation = 'z'
        self.characters[jid].velocity = numpy.array([args["vx"], args["vy"], args["vz"]])
        self.characters[jid].omega = args["omega"]

    def InputLocalMoveCommand(self):
        '''The macroAnimation-ness of our own, bound JID has probably changed,
           so call this function.'''
        # for some maximum velocities, try:
        #     http://www.elitefeet.com/how-fast-can-humans-run
        # (5 or 6 m/s seems plenty fast for most people...)
        # for walking velocities, this website:  
        #     http://www.bellaonline.com/articles/art20257.asp
        # claims that women walk at about 3 miles/hour, men walk 
        # at about 3.5 miles/hour, which translates to 1.34 m/s 
        # and 1.56 m/s, respectively.  (perhaps avg and max speed should
        # be based on stride length from the walk cycle animation?)
        #
        # Also, of course, people can't strafe right nearly as fast as
        # they can run forward... etc..
        #
        # TODO:  In the future, it will be up to the server to enforce
        # the rules (physics, collisions, max speeds, etc.).  For now, 
        # we have to trust each individual client.  
        #walkingSpeed = 1.5
        #joggingSpeed = 3.0
        #runningSpeed = 5.0
        speed = 2.2 # meters per second
        rotSpeed = 60.0 # degrees per second
        vx = (self.translatingForward - self.translatingBackward) * speed
        vy = (self.translatingLeft - self.translatingRight) * speed
        vz = (self.translatingUp - self.translatingDown) * speed
        omega = (self.turningLeft - self.turningRight) * rotSpeed
        # [Insert Useful Comment Here]
        if self.BoundTo:
            # Rotate the vx,vy,vz vector from character coordinates into world
            # coordinates:
            (phi, roll, theta) = self.characters[self.BoundTo].assembly.GetOrientation()
            sinTheta = math.sin(math.radians(theta))
            cosTheta = math.cos(math.radians(theta))
            #sinPhi = math.sin(math.radians(phi))
            #cosPhi = math.cos(math.radians(phi))
            rotVx = -vx * sinTheta - vy * cosTheta
            rotVy =  vx * cosTheta - vy * sinTheta

            self.characters[self.BoundTo].velocity = numpy.array([rotVx, rotVy, vz])
            self.characters[self.BoundTo].omega = omega

            iWasMoving = self.iAmMoving
            self.iAmMoving = vx or vy or vz or omega
            if iWasMoving != self.iAmMoving:
                self.characters[self.BoundTo].posTimeStamp = time.time()
        self.PleaseSendUDPPackets = 1
        self.PleaseRender = 1

    def InputUDPMicroAnimateCommand(self, jid, args):
        #print "InputUDPMicroAnimateCommand for", jid
        try:
            self.characters[jid].angles['left elbow'] = args['left elbow']
            self.characters[jid].angles['right elbow'] = args['right elbow']
        except:
            logging.error("    Failed to microAnimate <" + jid + ">")
        else:
            self.characters[jid].UpdateAllJointsAndBones()

    ####
    #### Animation:
    ####
    ####   animateObjects
    ####   microAnimate
    ####   macroAnimate
    ####   positionCamera

    def animateObjects(self):
        if 'BeachSunset' in self.maps:
            #(x, y, z) = self.maps['Sunset-1'].actors['oceanFloor'].actor.GetPosition()
            #print x, y, z
            omega = 0.3 # radians per second
            omega2 = omega / math.e
            omega3 = omega2 / math.e
            t = time.time()
            z = 0.3 * math.sin( omega * t) + 0.15 * math.sin( omega2 * t) + 0.07 * math.sin(omega3*t)
            self.maps['BeachSunset'].actors['oceanTop'].SetPosition(0.0, 0.0, z)
        if 'Clock' in self.maps:
            omega8 = 360. / 8. # 1 revolution per 8 seconds  
            omega4 = 360. / 4.  # 1 revolution per 4 seconds
            omega2 = 360. / 2.
            omegaLED = 360. * 2.  # 2 revolutions per second
            t = time.time()
            self.maps['Clock'].assemblies['8second'].SetOrientation(0.0, 0.0, -omega8 * t)
            self.maps['Clock'].assemblies['4second'].SetOrientation(0.0, 0.0, -omega4 * t)
            self.maps['Clock'].assemblies['2second'].SetOrientation(0.0, 0.0, -omega2 * t)
            self.maps['Clock'].assemblies['LED Display'].SetOrientation(0.0, 0.0, -omegaLED * t)


    def microAnimate(self):
        ''' Animations for individual characters (walk-cycles, gestures, etc). '''
        for jid in self.characters:
            if self.characters[jid].microAnimation == 'breathing':
                self.characters[jid].breathing()

    def macroAnimate(self):
        ''' Large-scale animation (rotating and moving to different locations on the map),
            but not small-scale animation (walk-cycles, etc). '''
        for jid in self.characters:
            vx = self.characters[jid].velocity[0]
            vy = self.characters[jid].velocity[1]
            vz = self.characters[jid].velocity[2]
            omega = self.characters[jid].omega
            if vx or vy or vz or omega:  # This character has a velocity, so we animate its movement
                try:
                    (x, y, z) = self.characters[jid].assembly.GetPosition()
                    (phi, roll, theta) = self.characters[jid].assembly.GetOrientation()
                    deltaTime = time.time() - self.characters[jid].posTimeStamp
                    axisOfRotation = self.characters[jid].axisOfRotation
                except:
                    logging.error("Failed to GetPosition() from <" + jid + ">")
                else:
                    x += vx * deltaTime
                    y += vy * deltaTime
                    z += vz * deltaTime
                    ## TODO (?)  Rotating about the X axis (pitch) doesn't actually
                    ## work:  VTK stops you when you're looking straight up.  Might
                    ## not really be worth fixing.  (Most real-world objects only 
                    ## have two eigenvectors of stable rotation, anyway...)
                    ##  (of course, we'll still need a hack to allow a plane or spaceship
                    ##   to loop)
                    if axisOfRotation == "x":
                        phi += omega * deltaTime
                    elif axisOfRotation == "y":
                        roll += omega * deltaTime
                    elif axisOfRotation == "z":
                        theta += omega * deltaTime
                    try:
                        self.characters[jid].assembly.SetPosition(x, y, z)
                        self.characters[jid].assembly.SetOrientation(phi, roll, theta)
                    except:
                        logging.error("Failed to SetPosition() on <" + jid + ">")
                    else:
                        self.characters[jid].posTimeStamp = time.time()

    def positionCamera(self):
        if self.BoundTo:
            body_position = numpy.array(self.characters[self.BoundTo].assembly.GetPosition())
            head_position = numpy.array(self.characters[self.BoundTo].actors["head"].GetPosition())
            (phi, roll, theta) = self.characters[self.BoundTo].assembly.GetOrientation()
            (headPhi, headRoll, headTheta) = self.characters[self.BoundTo].actors['head'].GetOrientation()
            sinTheta = math.sin(math.radians(theta))
            cosTheta = math.cos(math.radians(theta))
            sinPhi = math.sin(math.radians(headPhi))
            #cosPhi = math.cos(math.radians(headPhi))

            r = 2.0
            projectVectorX = -r * sinTheta
            projectVectorY = r * cosTheta
            projectVectorZ = r * sinPhi
            projectVector = numpy.array( [ projectVectorX, projectVectorY, projectVectorZ] )

            if self.OutOfBodyPerspective:
                shift_perspective = numpy.array([ -projectVectorX, -projectVectorY, -projectVectorZ])
                position = body_position + head_position + shift_perspective
            else:
                position = body_position + head_position
            self.camera.SetPosition(position[0], position[1], position[2])
            self.camera.SetFocalPoint(position + projectVector)
            self.camera.SetClippingRange( 0.25, 800)


    ####
    #### Event handlers (except for the timer, see up top)
    ####
    ####   ButtonEvent
    ####   KeyEvent
    ####   MouseEnters
    ####   MouseLeaves
    ####   MouseMove

    def ButtonEvent(self, obj, event):
        logging.debug("ButtonEvent!")
        if event == "LeftButtonPressEvent":
            if self.lastPickedActor:
                try:
                    href = self.lastPickedActor.href
                except:
                    for chr in self.characters:
                        if self.lastPickedActor == self.characters[chr].assembly:
                            print "jid: ", chr
                else:
                    #command = '/usr/bin/xdg-open ' + href 
                    command = 'echo \#xdg-open ' + href 
                    os.system(command)
                    logging.info("URL click.  Executing:  %s" % command)
        elif event == "LeftButtonReleaseEvent":
            pass
        elif event == "MiddleButtonPressEvent":
            self.Rotating = 1
        elif event == "MiddleButtonReleaseEvent":
            self.Rotating = 0
        elif event == "RightButtonPressEvent":
            pass
        elif event == "RightButtonReleaseEvent":
            pass

    def KeyEvent(self, obj, event):
        if event == "KeyPressEvent":
            pressed = 1
            if self.XkeyRepeat:
                # strange hack so that we don't get repeat keypresses
                logging.debug("xset r off")
                os.system("xset r off")
                self.XkeyRepeat = 0
        elif event == "KeyReleaseEvent":
            pressed = 0
        else:
            debug.error("Unknown event passed to Keypress() function.  Da hell?...")
        key = obj.GetKeySym()
        if key == "w" and pressed:
            self.ToggleWireframe()
        elif key == "h" and pressed:
            self.ToggleHeadlights()
        elif key == "o" and pressed:
            self.TogglePerspective()
        ### translational movement:
        elif key == "e":
            self.translatingForward=pressed
        elif key == "d":
            self.translatingBackward=pressed
        elif key == "t":
            self.translatingUp=pressed
        elif key == "g":
            self.translatingDown=pressed
        elif key == "s":
            self.translatingLeft=pressed
        elif key == "f":
            self.translatingRight=pressed
        #### rotational movement:
        elif key == "Left":
            self.turningLeft=pressed
        elif key == "Right":
            self.turningRight=pressed
        # when a person presses a key, we update the character:
        self.InputLocalMoveCommand()
        # ... and then instantly tell the world about the change:
        self.sendUDPpackets() 
        # (surely people can't type too fast for this to be a problem)

    def MouseEnters(self, obj, event):
        # strange hack so that we don't get repeat keypresses
        logging.debug("xset r off")
        os.system("xset r off")
        self.XkeyRepeat = 0

    def MouseLeaves(self, obj, event):
        if not self.Rotating:
            logging.debug("xset r on")
            os.system("xset r on")
            self.XkeyRepeat = 1

    def MouseMove(self, obj, event):
        lastXYpos = self.iren.GetLastEventPosition()
        lastX = lastXYpos[0]
        lastY = lastXYpos[1]

        xypos = self.iren.GetEventPosition()
        x = xypos[0]
        y = xypos[1]

        # Highlight URLs that can be clicked on:
        self.picker.PickProp(x,y,self.ren)
        pickedActor = self.picker.GetViewProp()
        if self.lastPickedActor == pickedActor:
            pass
        else:
            try: 
                hovercolor = pickedActor.hovercolor
            except:
                pass
            else:
                pickedActor.GetProperty().SetColor(hovercolor)
            try:
                color = self.lastPickedActor.color
            except:
                pass
            else:
                self.lastPickedActor.GetProperty().SetColor(color)
            self.lastPickedActor = pickedActor
            try:
                href = self.lastPickedActor.href
            except:
                for chr in self.characters:
                    if self.lastPickedActor == self.characters[chr].assembly:
                        self.osdStatus.SetInput("jid: " + str(chr))
            else:
                self.osdStatus.SetInput(str(href))
            if not pickedActor:
                self.osdStatus.SetInput(self.status)
            self.renwin.Render()

        if self.Rotating and self.BoundTo:
            scaling = 0.4
            deltaLeftRight = (lastX - x) * scaling
            deltaUpDown = (y - lastY) * scaling
            (phi, roll, theta) = self.characters[self.BoundTo].assembly.GetOrientation()
            (headPhi, headRoll, headTheta) = self.characters[self.BoundTo].actors['head'].GetOrientation()
            theta += deltaLeftRight
            headPhi += deltaUpDown
            self.characters[self.BoundTo].assembly.SetOrientation(0.0, 0.0, theta)
            self.characters[self.BoundTo].actors['head'].SetOrientation(headPhi, 0.0, 0.0)
            
            self.InputLocalMoveCommand()

 
    ####
    #### Modes of interaction and rendering
    ####
    ####   ToggleWireframe
    ####   ToggleHeadlights
    ####   TogglePerspective

    def ToggleWireframe(self):
        logging.debug("Toggling wireframe")
        if self.Wireframing:
            self.Wireframing = 0
        else:
            self.Wireframing = 1
        actors = self.ren.GetActors()
        actors.InitTraversal()
        actor = actors.GetNextItem()
        while actor:
            if self.Wireframing:
                actor.GetProperty().SetRepresentationToWireframe()
            else:
                actor.GetProperty().SetRepresentationToSurface()
            actor = actors.GetNextItem()
        self.renwin.Render()

    def ToggleHeadlights(self):
        logging.debug("Toggling headlights")
        lights = self.ren.GetLights()
        lights.InitTraversal()
        lightList = []
        lightList.append(lights.GetNextItem())
        if self.Headlighting:
            self.Headlighting = 0
            lightList[0].SetIntensity(0.0)
        else:
            self.Headlighting = 1
            lightList[0].SetIntensity(1.0)
        self.renwin.Render()

    def TogglePerspective(self):
        logging.debug("Toggling perspective")
        if self.OutOfBodyPerspective:
            self.OutOfBodyPerspective = 0
        else:
            self.OutOfBodyPerspective = 1


AllViewers = {}
AllViewers["VirtualWorldForPeople"] = VirtualWorldForPeople
AllViewers["justTesting"] = "nothing here"


