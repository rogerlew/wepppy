
import os
import json
import asyncio
import logging

import tornado.ioloop
import tornado.web
import tornado.websocket

import redis.asyncio as aioredis          # keep the async bits separate
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

# ─────────────────────────── Config ────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost")
REDIS_KEY_PATTERN = "__keyspace@0__:*"
HEARTBEAT_INTERVAL_MS = 30_000
CLIENT_CHECK_INTERVAL_MS = 5_000

# ──────────────────── Redis connection helpers ─────────────────
def new_redis():
    """Return a fresh Redis connection with sane defaults."""
    return aioredis.from_url(
        REDIS_URL,
        db=0,
        health_check_interval=30,        # send PING every 30 s
        retry_on_timeout=True,
        retry=Retry(backoff=ExponentialBackoff(1, 60), retries=-1),
        encoding="utf-8",
        decode_responses=True,
    )

shared_redis: aioredis.Redis | None = None   # set in main()

# ───────────────────── Logging tweaks ──────────────────────
logging.basicConfig(level=logging.INFO)

# suppress “GET /health …” access logs
logging.getLogger("tornado.access").addFilter(
    lambda rec: "/health" not in rec.getMessage()
)

# ────────────────────────── Helpers ────────────────────────────
def _try_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None

def _safe_gt(a, b):
    a, b = _try_int(a), _try_int(b)
    return a is not None and b is not None and a > b

def lock_statuses(prep: dict) -> dict:
    d = {}
    d['watershed'] = prep.get('locked:watershed', False) == 'true'
    d['climate'] = prep.get('locked:climate', False) == 'true'
    d['wepp'] = prep.get('locked:wepp', False) == 'true'
    d['soils'] = prep.get('locked:soils', False) == 'true'
    d['landuse'] = prep.get('locked:landuse', False) == 'true'
    d['disturbed'] = prep.get('locked:disturbed', False) == 'true'
    return d

def preflight(prep: dict) -> dict:
    """
    Runs preflight check for running wepp

    Parameters:
    - prep (dict): redis hashmap of preflight parameters

    Returns:
    - dict: preflight checklist


    The timestamps are from wepppy.nodb.redis_prep.TaskEnum set by wepppy.nodb.redis_prep.RedisPrep.timestamp()
    """

    d = {}

    d['sbs_map'] = prep.get('attrs:has_sbs', 'false') == 'true'
    d['channels'] = 'timestamps:build_channels' in prep
    d['outlet'] = _safe_gt(prep.get('timestamps:set_outlet'), prep.get('timestamps:build_channels'))
    d['subcatchments'] = _safe_gt(prep.get('timestamps:abstract_watershed'), prep.get('timestamps:build_channels'))
    d['landuse'] = _safe_gt(prep.get('timestamps:build_landuse'), prep.get('timestamps:abstract_watershed'))
    d['soils'] = _safe_gt(prep.get('timestamps:build_soils'), prep.get('timestamps:abstract_watershed')) and \
                 _safe_gt(prep.get('timestamps:build_soils'), prep.get('timestamps:build_landuse'))
    d['climate'] = _safe_gt(prep.get('timestamps:build_climate'), prep.get('timestamps:abstract_watershed'))
    d['rap_ts'] = _safe_gt(prep.get('timestamps:build_rap_ts'), prep.get('timestamps:build_climate'))
    d['wepp'] = _safe_gt(prep.get('timestamps:run_wepp'), prep.get('timestamps:build_landuse')) and \
                _safe_gt(prep.get('timestamps:run_wepp'), prep.get('timestamps:build_soils')) and \
                _safe_gt(prep.get('timestamps:run_wepp'), prep.get('timestamps:build_climate'))
    d['observed'] = _safe_gt(prep.get('timestamps:run_observed'), prep.get('timestamps:build_landuse')) and \
                    _safe_gt(prep.get('timestamps:run_observed'), prep.get('timestamps:build_soils')) and \
                    _safe_gt(prep.get('timestamps:run_observed'), prep.get('timestamps:build_climate')) and \
                    _safe_gt(prep.get('timestamps:run_observed'), prep.get('timestamps:run_wepp'))
    d['debris'] = _safe_gt(prep.get('timestamps:run_debris'), prep.get('timestamps:build_landuse')) and \
                  _safe_gt(prep.get('timestamps:run_debris'), prep.get('timestamps:build_soils')) and \
                  _safe_gt(prep.get('timestamps:run_debris'), prep.get('timestamps:build_climate')) and \
                  _safe_gt(prep.get('timestamps:run_debris'), prep.get('timestamps:run_wepp'))
    d['watar'] = _safe_gt(prep.get('timestamps:run_watar'), prep.get('timestamps:build_landuse')) and \
                 _safe_gt(prep.get('timestamps:run_watar'), prep.get('timestamps:build_soils')) and \
                 _safe_gt(prep.get('timestamps:run_watar'), prep.get('timestamps:build_climate')) and \
                 _safe_gt(prep.get('timestamps:run_watar'), prep.get('timestamps:run_wepp'))
    d['dss_export'] = _safe_gt(prep.get('timestamps:dss_export'), prep.get('timestamps:run_wepp'))

    return d

# ───────────────────── WebSocket handler ───────────────────────
class RunWebSocket(tornado.websocket.WebSocketHandler):
    clients: dict[str, set["RunWebSocket"]] = {}

    # ───────── Tornado plumbing ─────────
    def check_origin(self, origin):          # disable CORS for now
        return True


    async def open(self, arg):
        global shared_redis
        self.run_id = os.path.split(arg)[-1].strip()
        self.last_pong = tornado.ioloop.IOLoop.current().time()

        if self.run_id == "health":
            await self.write_message("OK")
            self.close()
            return

        RunWebSocket.clients.setdefault(self.run_id, set()).add(self)

        try:
            hashmap = await shared_redis.hgetall(self.run_id)
        except Exception as e:
            logging.critical("Failed to prime state for %s: %s", self.run_id, e, exc_info=True)
            # Close the socket, then kill the worker so siblings take over
            try: self.close()
            finally: os._exit(1)

        await self.write_message(json.dumps({
            "type": "preflight",
            "checklist": preflight(hashmap),
            "lock_statuses": lock_statuses(hashmap),
        }))
        
    async def on_message(self, msg):
        try:
            if json.loads(msg).get("type") == "pong":
                self.last_pong = tornado.ioloop.IOLoop.current().time()
        except json.JSONDecodeError:
            logging.warning("Bad JSON from %s", self.run_id)

    def on_close(self):
        s = RunWebSocket.clients.get(self.run_id, set())
        s.discard(self)
        if not s:
            RunWebSocket.clients.pop(self.run_id, None)

    # ───── class-level heartbeat utils ─────
    def _ping(self):
        if self.ws_connection and self.ws_connection.stream.socket:
            try:
                self.write_message('{"type":"ping"}')
            except Exception:
                logging.info("Ping failed; closing %s", self.run_id)
                self.close()
                
    @classmethod
    async def send_heartbeats(cls):
        for sockset in cls.clients.values():
            for client in list(sockset):
                client._ping()
                await asyncio.sleep(0.05)

    @classmethod
    def reap_dead(cls):
        now = tornado.ioloop.IOLoop.current().time()
        for sockset in list(cls.clients.values()):
            for client in list(sockset):
                dead = (
                    now - client.last_pong > 65 or
                    not client.ws_connection or
                    not client.ws_connection.stream.socket
                )
                if dead:
                    logging.info("Closing stale %s", client.run_id)
                    client.close()

# ─────────────────── Redis Pub/Sub listener ────────────────────
async def redis_listener():
    global shared_redis
    while True:
        try:
            pubsub = shared_redis.pubsub(ignore_subscribe_messages=True)
            await pubsub.psubscribe(REDIS_KEY_PATTERN)

            async for msg in pubsub.listen():
                if msg is None or msg["type"] != "pmessage":
                    continue
                # channel looks like "__keyspace@0__:<key>"
                # split only on the first ":" after the db tag
                try:
                    _, key = msg["channel"].split("__:", 1)
                except ValueError:
                    # fallback if not in expected form
                    key = msg["channel"].split(":", maxsplit=1)[-1]
                run_id = key

                sockset = RunWebSocket.clients.get(run_id)
                if not sockset:
                    continue

                try:
                    hashmap = await shared_redis.hgetall(run_id)
                except (ConnectionError, TimeoutError):
                    raise

                payload = json.dumps({
                    "type": "preflight", 
                    "checklist": preflight(hashmap), 
                    "lock_statuses": lock_statuses(hashmap)
                })
                for ws in list(sockset):
                    try:
                        await ws.write_message(payload)
                    except tornado.websocket.WebSocketClosedError:
                        pass

        except Exception as e:
            # truly unexpected — die fast
            logging.critical("Fatal error in redis_listener: %s", e, exc_info=True)
            os._exit(1)

# ────────────────────────── App setup ──────────────────────────
class Health(tornado.web.RequestHandler):
    def get(self): self.write("OK")

async def main():
    global shared_redis
    shared_redis = await new_redis()

    app = tornado.web.Application([
        (r"/health", Health),
        (r"/(.*)", RunWebSocket),
    ])
    app.listen(9001)

    # periodic tasks
    pc = tornado.ioloop.PeriodicCallback
    pc(lambda: tornado.ioloop.IOLoop.current().spawn_callback(RunWebSocket.send_heartbeats),
       HEARTBEAT_INTERVAL_MS).start()
    pc(RunWebSocket.reap_dead, CLIENT_CHECK_INTERVAL_MS).start()

    # fire-and-forget listener
    asyncio.create_task(redis_listener())

    await asyncio.Event().wait()   # keep main alive


async def startup_event():
    """This function contains all the async setup logic."""
    global shared_redis
    shared_redis = new_redis()

    pc = tornado.ioloop.PeriodicCallback
    pc(lambda: tornado.ioloop.IOLoop.current().spawn_callback(RunWebSocket.send_heartbeats),
       HEARTBEAT_INTERVAL_MS).start()
    pc(RunWebSocket.reap_dead, CLIENT_CHECK_INTERVAL_MS).start()

    asyncio.create_task(redis_listener())
    logging.info("Preflight service startup complete.")


app = tornado.web.Application([
    (r"/health", Health),
    (r"/(.*)", RunWebSocket),
])


# Schedule the async startup tasks to run once the IOLoop starts
#tornado.ioloop.IOLoop.current().spawn_callback(startup_event)
    
#if __name__ == "__main__":
#    tornado.ioloop.IOLoop.current().run_sync(main)

# ────────────────────────── App setup ──────────────────────────
# cp _service_files/gunicorn-status.service /etc/systemd/system/
# systemctl daemon-reload
# systemctl start gunicorn-status.service
# systemctl start gunicorn-status.service
# journalctl -u gunicorn-status -f
