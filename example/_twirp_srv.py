# Code generated by protoc-gen-twirp_python_srv 1.0.0, DO NOT EDIT.
# source: protoc-gen-twirp_python_srv/example/

try:
    import http.client as httplib
except ImportError:
    import httplib

import json
import sys
from collections import namedtuple
from enum import Enum
from functools import partial

from blinker import Namespace
from google.protobuf import json_format
from google.protobuf import symbol_database as _symbol_database
from werkzeug.wrappers import Request, Response

_sym_lookup = _symbol_database.Default().GetSymbol

Endpoint = namedtuple("Endpoint", ["name", "function", "input", "output"])

_signals = Namespace()

request_received = _signals.signal('request-received')
request_routed = _signals.signal('request-routed')
response_prepared = _signals.signal('response-prepared')
response_sent = _signals.signal('response-sent')
error_occurred = _signals.signal('error-occurred')


class Errors(Enum):
    Canceled = "canceled"
    Unknown = "unknown"
    InvalidArgument = "invalid_argument"
    DeadlineExceeded = "deadline_exceeded"
    NotFound = "not_found"
    BadRoute = "bad_route"
    AlreadyExists = "already_exists"
    PermissionDenied = "permission_denied"
    Unauthenticated = "unauthenticated"
    ResourceExhausted = "resource_exhausted"
    FailedPrecondition = "failed_precondition"
    Aborted = "aborted"
    OutOfRange = "out_of_range"
    Unimplemented = "unimplemented"
    Internal = "internal"
    Unavailable = "unavailable"
    DataLoss = "data_loss"
    NoError = ""

    @staticmethod
    def get_status_code(code):
        return {
            Errors.Canceled: 408,
            Errors.Unknown: 500,
            Errors.InvalidArgument: 400,
            Errors.DeadlineExceeded: 408,
            Errors.NotFound: 404,
            Errors.BadRoute: 404,
            Errors.AlreadyExists: 409,
            Errors.PermissionDenied: 403,
            Errors.Unauthenticated: 401,
            Errors.ResourceExhausted: 403,
            Errors.FailedPrecondition: 412,
            Errors.Aborted: 409,
            Errors.OutOfRange: 400,
            Errors.Unimplemented: 501,
            Errors.Internal: 500,
            Errors.Unavailable: 503,
            Errors.DataLoss: 500,
            Errors.NoError: 200,
        }.get(code, 500)


class TwirpServerException(httplib.HTTPException):
    def __init__(self, code, message, meta={}):
        if isinstance(code, Errors):
            self.code = code
        else:
            self.code = Errors.Unknown
        self.message = message
        self.meta = meta
        super(TwirpServerException, self).__init__(message)


class TwirpWSGIApp(object):
    def __init__(self, service=None):
        """Create a basic WSGI App for handling Twirp requests,
        with no endpoints.

        Meant to be subclassed by each individual service.
        """
        self.service = None
        self._endpoints = {}

    def __call__(self, environ, start_response):
        ctx = {
            "package_name": self._package_name,
            "service_name": self._service_name,
        }
        try:
            return self.handle_request(ctx, environ, start_response)
        except Exception as e:
            ctx['exc_info'] = sys.exc_info()
            return self.handle_error(ctx, e, environ, start_response)

    @staticmethod
    def json_decoder(request, data_obj=None):
        body = request.get_data(as_text=False)
        data = data_obj()
        json_format.Parse(body, data)
        return data

    @staticmethod
    def json_encoder(value, data_obj=None):
        if not isinstance(value, data_obj):
            raise TwirpServerException(
                Errors.Internal,
                ("bad service response type " + str(type(value)) +
                 ", expecting: " + data_obj.DESCRIPTOR.full_name))

        resp = Response(json_format.MessageToJson(
            value, preserving_proto_field_name=True),
            headers=[("Content-Type", "application/json")])
        return resp

    @staticmethod
    def proto_decoder(request, data_obj=None):
        body = request.get_data(as_text=False)
        data = data_obj()
        data.ParseFromString(body)
        return data

    @staticmethod
    def proto_encoder(value, data_obj=None):
        if not isinstance(value, data_obj):
            raise TwirpServerException(
                Errors.Internal,
                ("bad service response type " + str(type(value)) +
                 ", expecting: " + data_obj.DESCRIPTOR.full_name))

        resp = Response(value.SerializeToString(),
                        headers=[("Content-Type", "application/protobuf")])
        return resp

    def get_endpoint_methods(self, request):
        (_, url_pre, rpc_method) = request.path.rpartition(self._prefix + "/")
        if not url_pre or not rpc_method:
            raise TwirpServerException(
                Errors.BadRoute, "no handler for path " + request.path,
                {"twirp_invalid_route": "POST " + request.path},
            )

        endpoint = self._endpoints.get(rpc_method, None)
        if not endpoint:
            raise TwirpServerException(
                Errors.Unimplemented, "service has no endpoint " + rpc_method,
                {"twirp_invalide_route": "POST " + request.path})

        ctype = request.headers['Content-Type']
        if "json" in ctype:
            decoder = partial(self.json_decoder, data_obj=endpoint.input)
            encoder = partial(self.json_encoder, data_obj=endpoint.output)
        elif "protobuf" in ctype:
            decoder = partial(self.proto_decoder, data_obj=endpoint.input)
            encoder = partial(self.proto_encoder, data_obj=endpoint.output)
        else:
            raise TwirpServerException(
                Errors.BadRoute, "unexpected Content-Type: " + ctype,
                {"twirp_invalid_route": "POST " + request.path},
            )

        return endpoint.name, endpoint.function, decoder, encoder

    def handle_request(self, ctx, environ, start_response):
        request = Request(environ)
        ctx["request"] = request
        request_received.send(ctx)

        http_method = request.method
        if http_method != "POST":
            raise TwirpServerException(
                Errors.BadRoute,
                "unsupported method " + http_method + " (only POST is allowed)",
                {"twirp_invalid_route": http_method + " " + request.path},
            )
        ctx["http_method"] = "POST"
        ctx["url"] = request.path
        ctx["content-type"] = request.headers["Content-Type"]

        endpoint, func, decode, encode = self.get_endpoint_methods(request)
        ctx["endpoint"] = endpoint
        request_routed.send(ctx)

        input_arg = decode(request)
        ctx["input"] = input_arg
        result = func(input_arg, ctx=ctx)
        ctx["output"] = result
        response = encode(result)
        ctx["response"] = response
        response_prepared.send(ctx)

        ctx["status_code"] = 200
        response_sent.send(ctx)

        return response(environ, start_response)

    def handle_error(self, ctx, exc, environ, start_response):
        base_err = {
            "type": "Internal",
            "msg": ("There was an error but it could not be "
                    "serialized into JSON"),
            "meta": {}
        }
        response = Response()
        response.status_code = 500

        try:
            err = base_err
            if isinstance(exc, TwirpServerException):
                err["code"] = exc.code.value
                err["msg"] = exc.message
                if exc.meta:
                    for k, v in exc.meta.items():
                        err["meta"][k] = str(v)
                response.status_code = Errors.get_status_code(exc.code)
            else:
                err["msg"] = "Internal non-Twirp Error"
                err["code"] = 500
                err["meta"] = {"raw_error": str(exc)}

            for k, v in ctx.items():
                err["meta"][k] = str(v)

            response.set_data(json.dumps(err))
        except Exception as e:
            err = base_err
            err["meta"] = {"original_error": str(exc),
                           "handling_error": str(e)}
            response.set_data(json.dumps(err))

        # Force json for errors.
        response.headers["Content-Type"] = "application/json"

        ctx["status_code"] = response.status_code
        ctx["response"] = response
        ctx["exception"] = exc
        error_occurred.send(ctx)

        return response(environ, start_response)
