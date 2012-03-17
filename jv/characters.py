
# Copyright 2009, Mark Fassler

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.


import vtk
import time
import math
import random
import numpy
from jv.xmlReader import *
from jv.jvPaths import *

### Note:
#
# All characters should be constructed such that they are looking in the "Y"
# direction.  This will cause the vtk SetOrientation function (rotateZ, rotateX, rotateY)
# to function as rotateTHETA, rotatePHI, rotateROLL.  Therefore, theta is the
# negative of the compass direction.
#

class Nothing:
    def __init__ (self):
        self.a = 4
        self.actor = 7

class Human:
    'Supposed to look vaguely like a normal human being.'
    def __init__ (self, jid):
        self.jid = jid
        self.height = 1.73
        self.posTimeStamp = time.time()
        self.velocity = numpy.array([0.0, 0.0, 0.0])
        self.axisOfRotation = "z"
        self.omega = 0.0
        self.actors = {}
        self.joints = {}
        self.angles = {}
        self.bonelengths = {}
        self.microAnimation = 'breathing'
        # we don't want all the characters to be breathing exactly in sync,
        # so we need some random seeds that are unique per character
        self.seed1 = random.random()
        self.seed2 = random.random()
        self.seed3 = random.random()
        # How long are each of the bones?  We need the distance from the fulcrum
        # of the parent joint to the fulcrum of the child joint.  (The femur don't
        # make a straight line from hip to knee, but what we want here is the 
        # straight line from the hip to the knee, for positioning and animation.)
        self.bonelengths['sternum'] = 0.22
        self.bonelengths['left collarbone'] = 0.19
        self.bonelengths['right collarbone'] = 0.19
        self.bonelengths['left humerus'] = 0.28
        self.bonelengths['right humerus'] = 0.28
        self.bonelengths['left forearm'] = 0.26
        self.bonelengths['right forearm'] = 0.26
        self.bonelengths['left femur'] = 0.49
        self.bonelengths['right femur'] = 0.49
        self.bonelengths['left shin'] = 0.38
        self.bonelengths['right shin'] = 0.38
        # The positions of all the joints in the body (local coordinates):
        self.joints['heart'] = numpy.array([0.0, 0.0, 1.45])
        self.joints['sternumTop'] = numpy.array([0.0, 0.03, 1.45])
        self.joints['left sternCollar'] = numpy.array([-0.012, 0.03, 1.45])
        self.joints['right sternCollar'] = numpy.array([0.012, 0.03, 1.45])
        self.joints["left shoulder"] = numpy.array([-0.2, 0.0, 1.45])
        self.joints["right shoulder"] = numpy.array([0.2, 0.0, 1.45])
        self.joints['left elbow'] = numpy.array([0.0, 0.0, 0.0])
        self.joints['right elbow'] = numpy.array([0.0, 0.0, 0.0])
        self.joints['left wrist'] = numpy.array([0.0, 0.0, 0.0])
        self.joints['right wrist'] = numpy.array([0.0, 0.0, 0.0])
        self.joints['left hip'] = numpy.array([-0.12, 0.0, 0.96])
        self.joints['right hip'] = numpy.array([0.12, 0.0, 0.96])
        self.joints['left knee'] = numpy.array([0.0, 0.0, 0.0])
        self.joints['right knee'] = numpy.array([0.0, 0.0, 0.0])
        self.joints['left ankle'] = numpy.array([0.0, 0.0, 0.0])
        self.joints['right ankle'] = numpy.array([0.0, 0.0, 0.0])
        # Angles of joints.  *These* angles are intended to be intuitive for
        # animators.  It is the job of the programmer to translate these 
        # angles into the local coordinates.  
        #  For knees and elbows:  
        #     0.0 is fully extended
        #     ~160 degrees is fully flexed (via the bicep, or hamstring)
        #     negative numbers is hyper-extended 
        self.angles['left elbow'] = 25.0
        self.angles['right elbow'] = 17.0
        self.angles['left knee'] = 0.0
        self.angles['right knee'] = 32.0
        # Create the "core" bones:
        filename = jvDataDir + 'Avatars/Human/index.xml'
        fd = open(filename, 'r')
        XMLstring = fd.read()
        fd.close()
        logging.debug("Human:  Attempting to transform XML string")
        try:
            topElement = ET.fromstring(XMLstring)
        except:
            logging.error("MapReader:  Failed to transform XML string")
        xmlConverter = XML2VTK(topElement, bonelengths = self.bonelengths)
        self.actors = xmlConverter.actors

        # Initial positions for the bones:
        self.actors["sternum"].SetPosition(self.joints['sternumTop'])
        self.actors["sternum"].SetOrientation(-90.0, 0.0, 0.0)
        self.actors["left collarbone"].SetPosition(self.joints['left sternCollar'])
        self.actors["left collarbone"].SetOrientation(0.0, 0.0, 95.0)
        self.actors["right collarbone"].SetPosition(self.joints['right sternCollar'])
        self.actors["right collarbone"].SetOrientation(0.0, 0.0, -95.0)
        #self.actors["left humerus"].SetPosition(self.joints['left shoulder'])
        #self.actors["left humerus"].SetOrientation(-75.0, 0.0, 0.0)
        #self.actors["right humerus"].SetPosition(self.joints['right shoulder'])
        #self.actors["right humerus"].SetOrientation(-110.0, 0.0, 0.0)
        self.actors['left femur'].SetPosition(self.joints['left hip'])
        self.actors['left femur'].SetOrientation(-90.0, 0.0, 0.0)
        self.actors['right femur'].SetPosition(self.joints['right hip'])
        self.actors['right femur'].SetOrientation(-90.0, 0.0, 0.0)
        # dynamic update
        self.UpdateAllJointsAndBones()
        # Bind everything into a single object for the viewer:
        self.assembly = vtk.vtkAssembly()
        for i in self.actors:
            self.actors[i].SetPickable(1)
            self.assembly.AddPart(self.actors[i])
        #self.caption = vtk.vtkCaptionActor2D()
        #self.caption.SetCaption(self.jid)
    def UpdateAllJointsAndBones(self):
        self.actors["sternum"].SetPosition(self.joints['sternumTop'])
        self.actors["left collarbone"].SetPosition(self.joints['left sternCollar'])
        self.actors["right collarbone"].SetPosition(self.joints['right sternCollar'])
        ### Left arm
        self.UpdateNextJointLocation('left sternCollar', 'left collarbone', 'left shoulder')
        self.actors['left humerus'].SetPosition(self.joints['left shoulder'])
        self.actors["left humerus"].SetOrientation(-75.0, 0.0, 0.0)
        self.UpdateNextJointLocation('left shoulder', 'left humerus', 'left elbow')
        self.actors['left forearm'].SetPosition(self.joints['left elbow'])
        # First, we set the orientation to be the same as the parent 
        # bone, then we incrementally flex the joint:  (there are other ways
        # we could do this -- we could do the transformations ourselves, or
        # we could use nested vtkAssembly()'s...)
        phi, roll, theta = self.actors['left humerus'].GetOrientation()
        self.actors['left forearm'].SetOrientation(phi, roll, theta)
        self.actors['left forearm'].RotateX(self.angles['left elbow'])
        self.UpdateNextJointLocation('left elbow', 'left forearm', 'left wrist')
        self.actors['left hand'].SetPosition(self.joints['left wrist'])
        phi, roll, theta = self.actors['left forearm'].GetOrientation()
        self.actors['left hand'].SetOrientation(phi, roll, theta)
        # Right arm
        self.UpdateNextJointLocation('right sternCollar', 'right collarbone', 'right shoulder')
        self.actors['right humerus'].SetPosition(self.joints['right shoulder'])
        self.actors["right humerus"].SetOrientation(-45.0, 0.0, 0.0)
        self.UpdateNextJointLocation('right shoulder', 'right humerus', 'right elbow')
        self.actors["right forearm"].SetPosition(self.joints['right elbow'])
        phi, roll, theta = self.actors['right humerus'].GetOrientation()
        self.actors["right forearm"].SetOrientation(phi, roll, theta)
        self.actors["right forearm"].RotateX(self.angles['right elbow'])
        self.UpdateNextJointLocation('right elbow', 'right forearm', 'right wrist')
        self.actors['right hand'].SetPosition(self.joints['right wrist'])
        phi, roll, theta = self.actors['right forearm'].GetOrientation()
        self.actors['right hand'].SetOrientation(phi, roll, theta)
        # Left leg
        self.UpdateNextJointLocation('left hip', 'left femur', 'left knee')
        self.actors["left shin"].SetPosition(self.joints['left knee'])
        phi, roll, theta = self.actors['left femur'].GetOrientation()
        self.actors["left shin"].SetOrientation(phi, roll, theta)
        self.actors["left shin"].RotateX(-self.angles['left knee'])
        self.UpdateNextJointLocation('left knee', 'left shin', 'left ankle')
        self.actors["left foot"].SetPosition(self.joints['left ankle'])
        phi, roll, theta = self.actors['left shin'].GetOrientation()
        self.actors["left foot"].SetOrientation(phi, roll, theta)
        self.actors["left foot"].RotateX(90.0)
        # Right leg
        self.UpdateNextJointLocation('right hip', 'right femur', 'right knee')
        self.actors["right shin"].SetPosition(self.joints['right knee'])
        phi, roll, theta = self.actors['right femur'].GetOrientation()
        self.actors["right shin"].SetOrientation(phi, roll, theta)
        self.actors["right shin"].RotateX(-self.angles['right knee'])
        self.UpdateNextJointLocation('right knee', 'right shin', 'right ankle')
        self.actors["right foot"].SetPosition(self.joints['right ankle'])
        phi, roll, theta = self.actors['right shin'].GetOrientation()
        self.actors["right foot"].SetOrientation(phi, roll, theta)
        self.actors["right foot"].RotateX(90.0)
    def UpdateNextJointLocation(self, parent, connector, child):
        '''Updates the XYZ location of the "child" joint, given a "parent" joint and a "connector" bone.'''
        length = self.bonelengths[connector]
        phi, roll, theta = self.actors[connector].GetOrientation()
        sinTheta = math.sin(math.radians(theta))
        cosTheta = math.cos(math.radians(theta))
        sinPhi = math.sin(math.radians(phi))
        cosPhi = math.cos(math.radians(phi))
        # theta==0 points in the Y direction.  So everything is shifted by
        # 90 degrees from what you usually see in calculus textbooks.  So:
        #   x = r*cos(theta + 90)  =>  x = -r*sin(theta)
        #   y = r*sin(theta + 90)  =>  y = r*cos(theta)
        self.joints[child][0] = self.joints[parent][0] - length * cosPhi * sinTheta
        self.joints[child][1] = self.joints[parent][1] + length * cosPhi * cosTheta
        self.joints[child][2] = self.joints[parent][2] + length * sinPhi
    def breathing(self):
        # TODO:  This looks way too cheesey right now... hehe :-)
        # we use our random seeds to make sure that all the characters don't breathe in-sync
        periodOfBreath = 4.0 + self.seed1 * 0.5 # in seconds
        phaseOffset = self.seed2 * 5.0
        omega = 2. * math.pi / periodOfBreath
        amplitude = 0.005
        deltaZ = amplitude * math.sin( omega* time.time() + phaseOffset)
        deltaY = deltaZ
        heartToSternumTop = numpy.array([0.0, 0.03 + deltaY, deltaZ])
        heartToLeftSternCollar = numpy.array([-0.012, 0.03 + deltaY, deltaZ])
        heartToRightSternCollar = numpy.array([0.012, 0.03 + deltaY, deltaZ])
        #self.joints['heart'] = numpy.array([0.0, 0.0, 1.45])
        self.joints['sternumTop'] = self.joints['heart'] + heartToSternumTop
        self.joints['left sternCollar'] = self.joints['heart'] + heartToLeftSternCollar
        self.joints['right sternCollar'] = self.joints['heart'] + heartToRightSternCollar
        self.UpdateAllJointsAndBones()




class MechAngel:
    ''' See ThreePanelSoul, http://threepanelsoul.com/view.php?date=2009-02-09 for the
     MechAngel'''
    def __init__ (self, jid):
	self.jid = jid
        self.posTimeStamp = time.time()
        self.velocity = numpy.array([0.0, 0.0, 0.0])
        self.axisOfRotation = "z"
        self.omega = 0.0
        self.microAnimation = 'nothing'
        self.basedir = jvDataDir + '/Avatars/MechAngel'

        # Load the stuff:
        filename = jvDataDir + 'Avatars/MechAngel/index.xml'
        fd = open(filename, 'r')
        XMLstring = fd.read()
        fd.close()
        logging.debug("MechAngel:  Attempting to transform XML string")
        try:
            topElement = ET.fromstring(XMLstring)
        except:
            logging.error("MechAngel:  Failed to transform XML string")
        xmlConverter = XML2VTK(topElement, basedir=self.basedir)

        self.actors = xmlConverter.actors
        self.assemblies = xmlConverter.assemblies

        # Bind everything into a single object for the viewer:
        self.assembly = vtk.vtkAssembly()
        for i in self.actors:
            self.actors[i].SetPickable(1)
            self.assembly.AddPart(self.actors[i])
        for i in self.assemblies:
            self.assembly.AddPart(self.assemblies[i])



AllClasses = {}
AllClasses["Human"] = Human
AllClasses["MechAngel"] = MechAngel


