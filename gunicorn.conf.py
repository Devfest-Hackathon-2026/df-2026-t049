import os

bind = "0.0.0.0:" + os.environ.get("PORT", "8080")
workers = 2
worker_class = "sync"
timeout = 120
accesslog = "-"
errorlog = "-"
limit_request_line = 4094
