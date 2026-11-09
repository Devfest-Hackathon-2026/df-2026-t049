"""Loopback-only development server for the visual arena and existing engine."""
import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .bots import BOTS, CONFIG_OPTIONS, configured_bot, validate_config
from .engine import Engine
from .scenario import PUBLIC_SEEDS, event_scenario, fixed_scenario

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
ASSETS = {"/i18n.js": ("i18n.js", "text/javascript; charset=utf-8"),"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8")}
ASSETS.update({"/replay-controller.js": ("replay-controller.js", "text/javascript; charset=utf-8"),"/map-renderer.js": ("map-renderer.js", "text/javascript; charset=utf-8"),"/map-geometry.js": ("map-geometry.js", "text/javascript; charset=utf-8"),'/league': ('league.html', 'text/html; charset=utf-8'),
               '/league.js': ('league.js', 'text/javascript; charset=utf-8')})


def run_match(params):
    if set(params) - {"scenario", "seed", "bot", *CONFIG_OPTIONS} or any(len(v) != 1 for v in params.values()):
        raise ValueError("Invalid match parameters")
    kind = params.get("scenario", ["events"])[0]
    bot = params.get("bot", ["nearest"])[0]
    if kind not in ("events", "fixture") or bot not in (*BOTS, "custom"):
        raise ValueError("Unknown scenario or Bot")
    try:
        seed = int(params.get("seed", ["11" if kind == "events" else "0"])[0])
    except ValueError:
        raise ValueError("Seed must be an integer") from None
    if not -(2**31) <= seed < 2**31 or (kind == "fixture" and seed != 0):
        raise ValueError("Invalid seed for this scenario")
    scenario = event_scenario(seed) if kind == "events" else fixed_scenario()
    config = {key: params[key][0] for key in CONFIG_OPTIONS if key in params}
    if bot != "custom" and config:
        raise ValueError("Configuration requires custom Bot")
    policy = configured_bot(config) if bot == "custom" else BOTS[bot]
    result = Engine(scenario).run(policy)
    result["bot"] = bot
    if bot == "custom":
        result["bot_config"] = config
        result["bot_version"] = "1.0"
    return result


def compare_matches(config=None):
    names = list(BOTS)
    if config is not None:
        config = validate_config(config)
        names.append("custom")
    matches = []
    for seed in PUBLIC_SEEDS:
        for bot in names:
            params = {"scenario": ["events"], "seed": [str(seed)], "bot": [bot]}
            if bot == "custom":
                params.update({key: [value] for key, value in config.items()})
            record = run_match(params)
            row = {"seed": seed, "bot": bot, "score": record["score"], "summary": record["summary"]}
            if bot == "custom":
                row.update(bot_config=dict(config), bot_version="1.0")
            matches.append(row)
    ranking = [{"bot": bot, "mean_score": round(sum(m["score"]["total"] for m in matches
                if m["bot"] == bot) / len(PUBLIC_SEEDS), 6)} for bot in names]
    return {"scenario_version": "0.2-events", "scoring_version": "0.1", "seeds": list(PUBLIC_SEEDS),
            "matches": matches, "ranking": sorted(ranking, key=lambda r: (-r["mean_score"], r["bot"]))}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type="application/json; charset=utf-8"):
        body = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, dict) else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.reply(*route(self.path))

    def do_POST(self):
        from .league_api import handle
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 8192:
                raise ValueError()
        except ValueError:
            self.reply(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {'error': 'Invalid body length'})
            return
        if urlsplit(self.path).path.startswith('/api/league'):
            self.reply(*handle(self.path, 'POST', self.rfile.read(length), self.headers.get('Content-Type', '')))
        else:
            self.reply(HTTPStatus.METHOD_NOT_ALLOWED, {'error': 'Use GET'})


def route(target):
    """Shared bounded, read-only routes for local HTTP and production WSGI."""
    mime = "application/json; charset=utf-8"
    if len(target) > 2048:
        return HTTPStatus.REQUEST_URI_TOO_LONG, {"error": "Request too long"}, mime
    url = urlsplit(target)
    if url.path == '/bot-example.py':
        return HTTPStatus.OK, (WEB_ROOT.parent / 'examples' / 'decision_bot.py').read_bytes(), 'text/plain; charset=utf-8'
    if url.path.startswith('/api/league'):
        from .league_api import handle
        return handle(target)
    try:
        params = parse_qs(url.query, keep_blank_values=True, max_num_fields=8)
        if url.path == "/api/match":
            return HTTPStatus.OK, run_match(params), mime
        if url.path == "/api/compare":
            if any(len(v) != 1 for v in params.values()):
                raise ValueError("Duplicate parameters")
            config = {k: v[0] for k, v in params.items()} if params else None
            return HTTPStatus.OK, compare_matches(config), mime
        if url.path == "/health":
            return HTTPStatus.OK, {"status": "ok"}, mime
        if url.path in ASSETS:
            name, mime = ASSETS[url.path]
            return HTTPStatus.OK, (WEB_ROOT / name).read_bytes(), mime
        return HTTPStatus.NOT_FOUND, {"error": "Not found"}, mime
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}, mime


def main():
    parser = argparse.ArgumentParser(description="Local ReliefRoute Arena visual frontend")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", help="Local SQLite path (otherwise RELIEFROUTE_LEAGUE_DB or outputs/local-league.sqlite3)")
    args = parser.parse_args()
    from .local_startup import configure_local_league
    path = configure_local_league(args.db)
    print(f"Local database: {path}", flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"ReliefRoute Arena: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
