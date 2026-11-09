"""Production entry point: gunicorn reliefroute.wsgi:application."""
import json
from http import HTTPStatus

from .server import route


def application(environ, start_response):
    if environ.get('PATH_INFO', '').startswith('/api/league'):
        from .league_api import handle
        try:
            length = int(environ.get('CONTENT_LENGTH') or '0')
            if not 0 <= length <= 8192:
                raise ValueError()
        except ValueError:
            status, data, mime = HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {'error': 'Invalid body length'}, 'application/json'
        else:
            query = environ.get('QUERY_STRING', '')
            status, data, mime = handle(environ['PATH_INFO'] + ('?' + query if query else ''),
                environ.get('REQUEST_METHOD', 'GET'), environ['wsgi.input'].read(length) if length else b'',
                environ.get('CONTENT_TYPE', ''))
    elif environ.get("REQUEST_METHOD") not in ("GET", "HEAD"):
        status, data, mime = HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Use GET"}, "application/json"
    else:
        target = environ.get("PATH_INFO", "/")
        query = environ.get("QUERY_STRING", "")
        status, data, mime = route(target + ("?" + query if query else ""))
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if isinstance(data, dict) else data
    headers = [("Content-Type", mime), ("Content-Length", str(len(body))),
               ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
               ("Referrer-Policy", "no-referrer"), ("X-Frame-Options", "DENY")]
    if status == HTTPStatus.METHOD_NOT_ALLOWED:
        headers.append(("Allow", "GET, HEAD"))
    start_response(f"{status.value} {status.phrase}", headers)
    return [] if environ.get("REQUEST_METHOD") == "HEAD" else [body]
