import socket
import struct

####################### This snippet by Michael Urman.  GPL'd.
try:
        SO_PEERCRED = socket.SO_PEERCRED
except:
        SO_PEERCRED = 17

sizeof_ucred = 12
# 'III' is compatible between 32-bit and 64-bit
format_ucred = 'III' # pid_t, uid_t, gid_t

def getpeerid(sock):
        """getpeereid(sock) -> uid, gid

        Return the effective uid and gid of the remote connection.  Only works on
        UNIX sockets."""

        ucred = sock.getsockopt(socket.SOL_SOCKET, SO_PEERCRED, sizeof_ucred)
        pid, uid, gid = struct.unpack(format_ucred, ucred)

        return uid, gid
####################### end of snippet

