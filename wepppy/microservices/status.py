#!/usr/bin/env python
"""
WebSocket-to-Redis proxy using Tornado and redis-py 6.x (async).
Listens on :9002 and forwards Pub/Sub traffic {runid}:{channel} → WebSocket.

• Uses redis.asyncio (aioredis is now folded into redis-py)
• Health-checks idle sockets
• Retries with exponential back-off
• Suppresses tornado.access logs for GET /health
"""

import os
import json
import asyncio
import logging
import async_timeout

import tornado.ioloop
import tornado.web
import tornado.websocket

import redis.asyncio as aioredis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError
from wepppy.config.redis_settings import RedisDB, redis_async_url

# ───────────────────────── Config ──────────────────────────
REDIS_URL = redis_async_url(RedisDB.STATUS)

HEARTBEAT_INTERVAL_MS = 30_000
CLIENT_CHECK_INTERVAL_MS = 5_000

# ─────────────────── Redis connection pool ─────────────────
def new_redis():
    """Return a fresh Redis connection with healthy defaults."""
    return aioredis.from_url(
        REDIS_URL,
        health_check_interval=30,                       # send PING every 30 s
        retry_on_timeout=True,
        retry=Retry(backoff=ExponentialBackoff(1, 60), retries=-1),
        encoding="utf-8",
        decode_responses=True,
    )

shared_redis: aioredis.Redis | None = None  # set in main()

# ───────────────────── Logging tweaks ──────────────────────
logging.basicConfig(level=logging.INFO)

# suppress “GET /health …” access logs
logging.getLogger("tornado.access").addFilter(
    lambda rec: "/health" not in rec.getMessage()
)

# ───────────────────── WebSocket handler ───────────────────
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    clients: set["WebSocketHandler"] = set()

    def check_origin(self, origin):                   # disable CORS checks
        return True

    async def open(self, arg):
        global shared_redis

        arg = os.path.split(arg)[-1].strip()
        if arg == "health":
            await self.write_message("OK")
            self.close()
            return

        try:
            self.runid, self.channel = arg.split(":")
        except ValueError:
            self.close()                              # bad path
            return

        WebSocketHandler.clients.add(self)
        self.last_pong = tornado.ioloop.IOLoop.current().time()
        self.stop_event = asyncio.Event()

        self.pubsub = shared_redis.pubsub()
        await self.pubsub.subscribe(f"{self.runid}:{self.channel}")
        logging.info("WS subscribed to %s:%s", self.runid, self.channel)

        asyncio.create_task(self._proxy_loop())

    # ────────── message pump ──────────
    async def _proxy_loop(self):
        while not self.stop_event.is_set():
            try:
                async with async_timeout.timeout(1):
                    msg = await self.pubsub.get_message(ignore_subscribe_messages=True)
                    if msg is not None:
                        data = msg["data"]
                        await self.write_message(json.dumps({"type": "status", "data": data}))

            except Exception as e:
                # truly unexpected — die fast
                logging.critical("Fatal error in redis_listener: %s", e, exc_info=True)
                os._exit(1)

    async def _reconnect_pubsub(self):
        global shared_redis
        shared_redis = new_redis()
        self.pubsub = shared_redis.pubsub()
        await self.pubsub.subscribe(f"{self.runid}:{self.channel}")

    # ────────── WS plumbing ──────────
    async def on_message(self, msg):
        try:
            if json.loads(msg).get("type") == "pong":
                self.last_pong = tornado.ioloop.IOLoop.current().time()
        except json.JSONDecodeError:
            pass

    def on_close(self):
        WebSocketHandler.clients.discard(self)
        if hasattr(self, "pubsub"):
            asyncio.create_task(self.pubsub.unsubscribe(f"{self.runid}:{self.channel}"))
            asyncio.create_task(self.pubsub.aclose())
        self.stop_event.set()

    # ────────── heartbeat helpers ──────────
    def _ping(self):
        if self.ws_connection and self.ws_connection.stream.socket:
            try:
                self.write_message('{"type":"ping"}')
            except Exception:
                logging.info("Ping failed; closing %s", self.runid)
                self.close()
                
    @classmethod
    async def send_heartbeats(cls):
        for c in list(cls.clients):
            c._ping()
            await asyncio.sleep(0.05)

    @classmethod
    def reap_stale(cls):
        now = tornado.ioloop.IOLoop.current().time()
        for c in list(cls.clients):
            if (now - c.last_pong > 65) or not c.ws_connection or not c.ws_connection.stream.socket:
                c.close()

# ───────────────────────── Tornado app ─────────────────────
class Health(tornado.web.RequestHandler):
    def get(self):
        self.write("OK")

async def main():
    global shared_redis
    shared_redis = await new_redis()

    app = tornado.web.Application([
        (r"/health", Health),
        (r"/(.*)", WebSocketHandler),
    ])
    app.listen(9002)

    pc = tornado.ioloop.PeriodicCallback
    pc(lambda: tornado.ioloop.IOLoop.current().spawn_callback(WebSocketHandler.send_heartbeats),
       HEARTBEAT_INTERVAL_MS).start()
    pc(WebSocketHandler.reap_stale, CLIENT_CHECK_INTERVAL_MS).start()

    # close pool cleanly at shutdown
    async def _close_pool():
        await shared_redis.aclose()
    tornado.ioloop.IOLoop.current().add_callback(_close_pool)

    await asyncio.Event().wait()  # keep running


async def startup_event():
    """This function contains all the async setup logic."""
    global shared_redis
    shared_redis = new_redis()

    # Periodic tasks still need to be managed by the IOLoop
    # Gunicorn handles the IOLoop and the event loop
    pc = tornado.ioloop.PeriodicCallback
    pc(lambda: tornado.ioloop.IOLoop.current().spawn_callback(WebSocketHandler.send_heartbeats),
       HEARTBEAT_INTERVAL_MS).start()
    pc(WebSocketHandler.reap_stale, CLIENT_CHECK_INTERVAL_MS).start()

    logging.info("Status service startup complete.")


app = tornado.web.Application([
    (r"/health", Health),
    (r"/(.*)", WebSocketHandler),
])


# Schedule the async startup tasks to run once the IOLoop starts
#tornado.ioloop.IOLoop.current().spawn_callback(startup_event)
    

#if __name__ == "__main__":
#    tornado.ioloop.IOLoop.current().run_sync(main)


# ────────────────────────── App setup ──────────────────────────
# cp _service_files/gunicorn-preflight.service /etc/systemd/system/
# systemctl daemon-reload
# systemctl start gunicorn-preflight.service
# systemctl start gunicorn-preflight.service
# journalctl -u gunicorn-preflight -f
