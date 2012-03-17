
import struct

#moveCommand = {}

# A single IP_Address/UDP_Sourceport can manage 65535 JIDs.
#moveCommand['userID'] = 65534			# 16-bit unsigned Int

#  Command
#
# Right now, the only command is "move", as defined here.  There are
# three variants of the move command:
#  0x01 - move with "X" as your principle axis
#  0x02 - move with "Y" as your principle axis
#  0x03 - move with "Z" as your principle axis
# the principle axis only affects "omega", the angular velocity.  The
# angular velocity must occur about the principle axis specified here.
# For everything else, these three move commands are identical.  
#moveCommand['command'] = 0x03			#  8-bit unsigned Int

# Subcommand
#
# this will be for choosing walk-cycles, animations, gestures
#moveCommand['subcommand'] = int('01010101', 2)	#  8-bit unsigned Int

# Our position, in meters, in real-world coordinates
#   - the x-axis points east
#   - the y-axis points north
#   - the z-axis points up
#moveCommand['x'] = 234.5532			# 64-bit float
#moveCommand['y'] = 5634.5532			# 64-bit float
#moveCommand['z'] = 34.0032			# 64-bit float

# Our velocity, in meters/second
#moveCommand['vx'] = 4.22			# 64-bit float
#moveCommand['vy'] = 0.12			# 64-bit float
#moveCommand['vz'] = 2.88435522			# 64-bit float

# Our orientation, in degrees.  In absolute (world) coordinates.
#   - theta is the negative of compass direction (0 points north.  -90 points east)
#   - phi ("pitch") is looking up from the horizon (positive is up)
#   - roll is like the roll of an airplane (positive is clockwise)
#moveCommand['theta'] = 34.5			# 32-bit float
#moveCommand['phi'] = 0.00			# 32-bit float
#moveCommand['roll'] = -45.00			# 32-bit float

# The orientation of our head (or perhaps a gun turret on a vehicle)
#  These coordinates are relative to the body that owns the head
#moveCommand['headTheta'] = 5.5			# 32-bit float
#moveCommand['headPhi'] = -9.233			# 32-bit float
#moveCommand['headRoll'] = 0.00			# 32-bit float

# Our angular velocity, in degrees/second, about the principle axis 
# specified in the command.  (Models that are intended to rotate 
# *must* rotate about one of their principle axes.)
#moveCommand['omega'] = 5.001			# 32-bit float

def packMoveCommandUDP(moveCommand):
    packet = struct.pack( '!HBBddddddfffffff',
      moveCommand['userID'],
      moveCommand['command'],
      moveCommand['subcommand'],
      moveCommand['x'],
      moveCommand['y'],
      moveCommand['z'],
      moveCommand['vx'],
      moveCommand['vy'],
      moveCommand['vz'],
      moveCommand['theta'],
      moveCommand['phi'],
      moveCommand['roll'],
      moveCommand['headTheta'],
      moveCommand['headPhi'],
      moveCommand['headRoll'],
      moveCommand['omega'] )
    return packet

def unpackMoveCommandUDP(packet):
    moveCommand = {}
    (moveCommand['userID'],
      moveCommand['command'],
      moveCommand['subcommand'],
      moveCommand['x'],
      moveCommand['y'],
      moveCommand['z'],
      moveCommand['vx'],
      moveCommand['vy'],
      moveCommand['vz'],
      moveCommand['theta'],
      moveCommand['phi'],
      moveCommand['roll'],
      moveCommand['headTheta'],
      moveCommand['headPhi'],
      moveCommand['headRoll'],
      moveCommand['omega'] ) = struct.unpack('!HBBddddddfffffff', packet)
    return moveCommand


def packMicroAnimateCommandUDP(microAnimateCommand):
    packet = struct.pack( '!HBBff',
      microAnimateCommand['userID'],
      microAnimateCommand['command'],
      microAnimateCommand['subcommand'],
      microAnimateCommand['left elbow'],
      microAnimateCommand['right elbow'] )
    return packet


def unpackMicroAnimateCommandUDP(packet):
    microAnimateCommand = {}
    (microAnimateCommand['userID'],
      microAnimateCommand['command'],
      microAnimateCommand['subcommand'],
      microAnimateCommand['left elbow'],
      microAnimateCommand['right elbow'] ) = struct.unpack('!HBBff', packet)
    return microAnimateCommand


