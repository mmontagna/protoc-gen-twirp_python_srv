import bjoern
import echo_pb2 as pb
from echo_twirp_srv import EchoImpl, EchoServer


class Echoer(EchoImpl):
    def Repeat(self, request, ctx={}):
        return pb.EchoResponse(output=request.input)

    def RepeatMultiple(self, request, ctx={}):
        output = request.input
        if request.count > 0:
            output = output * request.count
        return pb.EchoResponse(output=output)

application = EchoServer(Echoer())
