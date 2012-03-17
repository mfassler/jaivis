

# This is the command that jabberClient.py will use to launch jaivis.py:
#jaivisCommand = 'xterm -e python -i /home/fassler/Projects/jaivis/jaivis.py'
# (I like to put it in its own xterm window to watch the debugging output.)


# This is where we will look for maps and textures:
#jvDataDir = '~/Projects/jaivis/data/'
import os
base = os.path.split(__file__)[0] # get directory where this module is.
jvDataDir = os.path.abspath(os.path.join(base, '../data'))+'/'
if not os.path.exists(jvDataDir):
    print "cannot find data files in: %s" % (jvDataDir)
    os.exit(1)

jvCommandSocketFileName = '/tmp/jv-wazza'
LOG_FILENAME = '/tmp/jaivis.out'

