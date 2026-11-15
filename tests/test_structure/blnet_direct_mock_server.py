import socket
import time
from socketserver import BaseRequestHandler, ThreadingTCPServer

# Responses recorded from a real BL-NET with one UVR1611 in DL mode
DL_MODE_RESPONSE = bytes.fromhex("a8")
DL_HEADER_RESPONSE = bytes.fromhex("0fa85e6b1d76809204409204ff")
DL_LATEST_RESPONSE = bytes.fromhex(
    "80ff2fff2fff2fff2fff2f1b224d210522e92110216e20322103226f21ff2f003061"
    "0218000a1201000000001a216a010b010a3c0001000c04"
)
# Asks the client to wait the given amount of seconds before trying again
WAIT_RESPONSE = bytes.fromhex("ba00ba")
# No new data available yet ("Synchronisation" in TA's interface spec)
NO_DATA_RESPONSE = bytes.fromhex("ab")

GET_MODE = 0x81
GET_HEADER = 0xAA
GET_LATEST = 0xAB
READ_DATA = 0xAC
END_READ = 0xAD


class BLNETDirectServer(ThreadingTCPServer):

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address):
        super().__init__(server_address, BLNETDirectRequestHandler)
        # Responses to GET_LATEST, the last one is repeated forever
        self.latest_responses = [DL_LATEST_RESPONSE]
        # Accept connections but never answer
        self.silent = False
        # Close the connection when receiving this command
        self.close_on = None
        # Answer GET_LATEST with NO_DATA_RESPONSE until this time.monotonic() value
        self.no_data_until = None
        # Response to READ_DATA, by default one with a wrong checksum
        self.read_data_response = bytes.fromhex("0001")
        # Send the first byte of GET_LATEST replies in a TCP segment of its own,
        # like real BL-NETs sometimes do
        self.split_latest = False
        # Currently open client connections
        self.connections = set()

    def drop_connections(self):
        """Close all open client connections, like a BL-NET that restarts"""
        for connection in list(self.connections):
            connection.shutdown(socket.SHUT_RDWR)


class BLNETDirectRequestHandler(BaseRequestHandler):
    def handle(self):
        self.server.connections.add(self.request)
        try:
            self._handle_commands()
        except OSError:
            # connection was dropped
            pass
        finally:
            self.server.connections.discard(self.request)

    def _handle_commands(self):
        while True:
            command = self.request.recv(1)
            if not command:
                return
            command = command[0]
            if command == self.server.close_on:
                return
            if self.server.silent:
                continue
            if command == GET_MODE:
                self.request.sendall(DL_MODE_RESPONSE)
            elif command == GET_HEADER:
                self.request.sendall(DL_HEADER_RESPONSE)
            elif command == GET_LATEST:
                # frame number
                self.request.recv(1)
                no_data_until = self.server.no_data_until
                if no_data_until is not None and time.monotonic() < no_data_until:
                    self.request.sendall(NO_DATA_RESPONSE)
                    continue
                responses = self.server.latest_responses
                response = responses.pop(0) if len(responses) > 1 else responses[0]
                if self.server.split_latest and len(response) > 1:
                    self.request.sendall(response[:1])
                    time.sleep(0.05)
                    self.request.sendall(response[1:])
                else:
                    self.request.sendall(response)
            elif command == READ_DATA:
                # address, number of frames, checksum
                self.request.recv(5)
                self.request.sendall(self.server.read_data_response)
            elif command == END_READ:
                self.request.sendall(bytes([END_READ]))
