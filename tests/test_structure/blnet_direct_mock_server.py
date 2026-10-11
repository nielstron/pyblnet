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

GET_MODE = 0x81
GET_HEADER = 0xAA
GET_LATEST = 0xAB
END_READ = 0xAD


class BLNETDirectServer(ThreadingTCPServer):

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address):
        super().__init__(server_address, BLNETDirectRequestHandler)
        # Responses to GET_LATEST, the last one is repeated forever
        self.latest_responses = [DL_LATEST_RESPONSE]


class BLNETDirectRequestHandler(BaseRequestHandler):
    def handle(self):
        while True:
            command = self.request.recv(1)
            if not command:
                return
            command = command[0]
            if command == GET_MODE:
                self.request.sendall(DL_MODE_RESPONSE)
            elif command == GET_HEADER:
                self.request.sendall(DL_HEADER_RESPONSE)
            elif command == GET_LATEST:
                # frame number
                self.request.recv(1)
                responses = self.server.latest_responses
                response = responses.pop(0) if len(responses) > 1 else responses[0]
                self.request.sendall(response)
            elif command == END_READ:
                self.request.sendall(bytes([END_READ]))
