import logging


def simpleDict2Dict(simpleDict):
    returnDict = {}
    simplePairs = simpleDict.split()
    for simplePair in simplePairs:
        try:
            keyName, keyValue = simplePair.split(':', 1)
            returnDict[keyName] = keyValue
        except:
            pass
    return returnDict

## The RESTful handler

def RESTfulHandler(viewer, inputSocket, inputPacket):
    inputString = inputPacket.strip()
    if isinstance(inputString, bytes):
        inputString = inputString.decode()

    logging.debug("Received a command:  %s" % (inputString))
    try:
        pieces = inputString.split(None, 2) # maximum of 3 pieces
        verb = pieces[0]
        cObjects = pieces[1].split('/')
    except:
        logging.error("Failed to parse Jaivis command.")
    else:
        if verb == "LOAD":
            if cObjects[0] == "map":
                returnString = viewer.LoadMap(pieces[2])
                inputSocket.send( (" %s\n" % (returnString)).encode())
            elif cObjects[0] == "character":
                extraArgs = simpleDict2Dict(pieces[2])
                returnString = viewer.LoadCharacter(extraArgs['jid'], extraArgs)
                #ipaddr = extraArgs['transport']['ip']
                #udpport = extraArgs['transport']['port']
                #viewer.UDPRecipients.append( (ipaddr, int(udpport)) )
                #viewer.authorizedUDPpackets[ (ipaddr, int(udpport)) ] = [ jid ]
                inputSocket.send( (" %s\n" % (returnString)).encode())
        elif verb == "REMOVE":
            if cObjects[0] == "maps":
                mapName = cObjects[1]
                viewer.RemoveMap(mapName)
            elif cObjects[0] == "characters":
                jid = cObjects[1]
                viewer.RemoveCharacter(jid)
        elif verb == "BINDTO":
            viewer.BindTo(cObject)
            viewer.AnnounceTransport()
        elif verb == "PUT":
            if cObjects[0] == 'characters':
                jid = cObjects[1]
                if cObjects[2] == 'authorizedPackets':
                    extraArgs = simpleDict2Dict(pieces[2])
                    ipaddr = extraArgs['transport']['ip']
                    udpport = extraArgs['transport']['port']
                    viewer.authorizedUDPpackets[ (ipaddr, int(udpport)) ] = [ jid ]
        elif verb == "POST":
            if cObjects[0] == "osd":
                viewer.PostOSD(pieces[2])
        elif verb == "GET":
            print(cObjects, len(cObjects))
            if cObjects[0] == "info":
                if len(cObjects) > 1:
                    if cObjects[1] == "transport":
                        viewer.AnnounceTransport()
                else:
                    inputSocket.send(b"Available info is:\n")
                    inputSocket.send(b"info/transport\n")
            elif cObjects[0] == "maps":
                for mapName in viewer.maps:
                    inputSocket.send( ("%s\n" % (mapName)).encode() )
            elif cObjects[0] == "characters":
                for jid in viewer.characters:
                    inputSocket.send( ("%s\n" % (jid)).encode() )
        elif verb == "DELETE":
            pass
        elif verb == "MOVE":
            if cObjects[0] == "characters":
                jid = cObjects[1]
                extraArgs = simpleDict2Dict(pieces[2])
                position = ( float(extraArgs['x']), float(extraArgs['y']), float(extraArgs['z']))
                try:
                    viewer.characters[jid].assembly.SetPosition(position)
                except:
                    logging.error('Failed to SetPosition() in RESTful handler')
        elif verb == "ROTATE":
            if cObjects[0] == "characters":
                jid = cObjects[1]
                extraArgs = simpleDict2Dict(pieces[2])
                if not 'phi' in extraArgs:
                    extraArgs['phi'] = 0.0
                if not 'roll' in extraArgs:
                    extraArgs['roll'] = 0.0
                if not 'theta' in extraArgs:
                    extraArgs['theta'] = 0.0
                orientation = ( float(extraArgs['phi']), float(extraArgs['roll']), float(extraArgs['theta']))
                try:
                    viewer.characters[jid].assembly.SetOrientation(orientation)
                except:
                    logging.error('Failed to SetPosition() in RESTful handler')
        else:
            logging.error('Unrecognized command: %s' % pieces[0])
    inputSocket.send(b"> ")


