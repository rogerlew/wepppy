worker_class = "tornado"
preload_app = False           # critical: avoid import-time loop work in master
threads = 1
reuse_port = False

# keep your recycling
max_requests = 500
max_requests_jitter = 100

# websockets: timeout must exceed heartbeat window
timeout = 75                  # > 30s heartbeat + jitter
graceful_timeout = 15
keepalive = 10

def post_fork(server, worker):
    # schedule your async startup after the worker’s IOLoop exists
    import tornado.ioloop
    from wepppy.microservices import preflight
    tornado.ioloop.IOLoop.current().add_callback(preflight.startup_event)
