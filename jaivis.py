#!/usr/bin/env python3

import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

# Copyright 2009, Mark Fassler  <spin at eavesdown dot org>
# Licensed under the GNU GPLv2

import vtk
import os
from optparse import OptionParser
import logging

from jv.jvPaths import *

parser = OptionParser(usage = "usage: %prog [options] viewer_type")

# We take one option:  debug_level
parser.add_option("-d", action="store", type="int", dest="debugLevel", default=0,
  help='0 = minimal (default), 3 = everything')

(options, args) = parser.parse_args()

# We require one argument:  viewer_type
if len(args) < 1:
    parser.error("user must specify a viewer_type")
elif len(args) == 1:
    viewerType = args[0]
elif len(args) > 1:
    parser.error("extra arguments on the command line")

# Debug levels:
#  0 (default) - only fatal errors
#  1 - only errors.  No news is good news.
#  2 - errors and important info
#  3 - everything

try:
    os.remove( LOG_FILENAME + '.2' )
except:
    pass

try:
    os.rename( LOG_FILENAME + '.1' , LOG_FILENAME + '.2')
except:
    pass

try:
    os.rename( LOG_FILENAME,         LOG_FILENAME + '.1')
except:
    pass

logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)

logging.debug("\n **** Starting Jaivis ****")
logging.debug("Debug level set to: %d" % (options.debugLevel))

print("viewer_type is: ", viewerType)

from jv import viewers

if not viewerType in viewers.AllViewers:
    print("Viewer not available.  Available viewer types:")
    for i in viewers.AllViewers.keys():
        print(" ", i)
    sys.exit(1)

print("\nLogfile:  plaintext: %s" % (LOG_FILENAME))

# Create the Jaivis (ie, VTK) viewer:
v = viewers.AllViewers[viewerType]()

# Add an origin and compass rose:
v.LoadMap('CompassRose')

# Set the orientation and ViewAngle for the camera:
camera = v.ren.GetActiveCamera()
camera.SetFocalPoint (0.0, 0.0, 0.0)
camera.SetPosition (7.0, -5., 0.0)
camera.SetViewUp(0.0, 0.0, 1.0)
camera.SetPosition (7.0, -5., 4.0)
camera.SetFocalDisk(9.0)
camera.SetViewAngle(45.)
v.renwin.Render()

# Load our first character:
v.LoadCharacter('username@jabber.org', {'race': 'Human'})

# Bind the local Jaivis session to this character:
v.BindTo('username@jabber.org')

# Move the character (and thus our camera) to somewhere useful:
v.characters['username@jabber.org'].assembly.SetPosition(8.2, -9.3, 2.7)
v.characters['username@jabber.org'].assembly.SetOrientation(0.0, 0.0, 58.0)

# Load a default map (beyond the basic CompassRose):
v.LoadMap('BeachSunset')

# Post a "hello" message to the On-Screen Display:
v.PostOSD('Welcome to Jaivis!')



#v.authorizedUDPpackets[('127.0.0.1', 45000)] = ['customer@eavesdown.org']
#v.authorizedUDPpackets[('localhost', 45000)] = ['customer@eavesdown.org']

# Start the animation loop:
v.iren.CreateTimer(0)
v.iren.Start()


