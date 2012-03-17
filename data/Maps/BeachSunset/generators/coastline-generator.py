import numpy
import sys
#import random

## cgkit comes from:  http://cgkit.sourceforge.net
#from cgkit.noise import noise

print "# vtk DataFile Version 2.0"
print
print "ASCII"
print "DATASET UNSTRUCTURED_GRID"



from pylab import *
import random



maxY = 256.0
minY = -270.0
Ysubdivisions = 16.
deltaY = (maxY - minY) / Ysubdivisions
y_values = numpy.arange(maxY, minY, -deltaY)



def pinkNoise(t):
    "vaguely pink noise-ish"
    w = 0.015 # the lowest frequency, in radians per second
    y = - (7 * sin( w * t) + 4.5 * sin( w * e * t) + sin( w * e**2 * t) ) * 0.5
    return y

def arbitraryShape(t):
    "adding my own arbitrary curve"
    y = zeros(len(t))
    for i in range(len(t)):
        if t[i] < 0:
            y[i] = 0.0
        else:
            y[i] = -(t[i] ** 2.0) * 0.003
    return y


y = pinkNoise(y_values)
y1 = arbitraryShape(y_values)

initial_coastline = y+y1

#plot(y_values, initial_coastline, '.')
#show()




z_values = numpy.arange(-1.0, 15.0, 2.0)
minX = -35.0
maxX = 300.0
Xsubdivisions = len(z_values)
deltaX = (maxX - minX) / Xsubdivisions

x_offsets = numpy.arange(minX, maxX, deltaX)

number_of_points = len(initial_coastline) * len(z_values)
print "POINTS %d float" % number_of_points

for z in range(len(z_values)):
    if z > 1 :
        z_rand = z
    else:
        z_rand = 1
    #print "************************** new Z value:", z
    xOffset = x_offsets[z]
    next_line = initial_coastline + xOffset + numpy.random.random(Ysubdivisions) * (xOffset/4.)
    for j in range(len(next_line)):
        print next_line[j], 
        print y_values[j] + random.random()*(deltaY * 0.8) - (deltaY * 0.4), 
        print z_values[z] + random.random()* (1.5 *z_rand )  - 0.75


number_of_strips = len(z_values) - 1
points_per_line = len(initial_coastline)
points_per_strip = points_per_line * 2
number_of_points = points_per_strip * number_of_strips

print
print "CELLS %d %d" % (number_of_strips, number_of_points + number_of_strips)
for j in range(number_of_strips):
    print points_per_strip,
    for i in range(points_per_line):
        print i + (j*points_per_line), i + points_per_line + (j*points_per_line),
    print
print
print "CELL_TYPES", number_of_strips
for i in range(number_of_strips):
    print "6 ",



