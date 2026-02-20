import logging

from app.common import tracing


# Adds additional ECS fields to the logger.
class ExtraFieldsFilter(logging.Filter):
    def filter(self, record):
        trace_id = tracing.ctx_trace_id.get("")
        req = tracing.ctx_request.get(None)
        resp = tracing.ctx_response.get(None)

        if trace_id:
            record.trace = {"id": trace_id}

        http = {}
        if req:
            record.url = {"full": req.get("url", None)}
            http["request"] = {"method": req.get("method", None)}
        if resp:
            http["response"] = resp
        if http:
            record.http = http
        return True


class EndpointFilter(logging.Filter):
    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path = path

    def filter(self, record):
        return record.getMessage().find(self._path) == -1
