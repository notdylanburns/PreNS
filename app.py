import atexit
import logging
import time
from multiprocessing import Process, Queue

from flask import Flask, Response, make_response, redirect, request, url_for

from src.database import Database
from src.host import Host

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.get("/")
def main() -> Response:
    return redirect(url_for("static", filename="index.html"))  # type: ignore


@app.get("/api/hosts")
def get_hosts() -> Response:
    with DATABASE.connect() as conn:
        hosts = conn.get_hosts()

    return make_response(hosts, 200)


@app.get("/api/label/<int:label_id>/children")
def get_children(label_id: int) -> Response:
    with DATABASE.connect() as conn:
        children = conn.get_children(label_id or None)

    return make_response(children, 200)


@app.delete("/api/host/<int:host_id>")
def delete_host(host_id: int) -> Response:
    with DATABASE.connect() as conn:
        conn.delete_host(host_id)

    CLEANUP_QUEUE.put("CLEANUP")

    return make_response("", 204)


@app.post("/api/host")
def post_host() -> Response:
    data = request.json

    if data is None:
        return make_response("missing request body", 400)

    try:
        host = Host(data)

        with DATABASE.connect() as conn:
            conn.insert_host(host)

    except ValueError as e:
        return make_response(str(e), 400)

    return make_response(
        {
            "id": 1,
            "hostname": data["hostname"],
            "ttl": data["ttl"],
            "resolved_at": None,
            "error_message": None,
        },
        200,
    )


def heirarchy_cleanup():
    try:
        while True:
            CLEANUP_QUEUE.get()
            logging.info("processing cleanup job...")
            try:
                with DATABASE.connect() as conn:
                    removed = conn.heirarchy_cleanup()

                logging.info(
                    f"cleanup job finished - removed heirarchy items with ids: {removed}"
                )
            except Exception as e:
                logging.error(f"cleanup job failed: {e}")

            time.sleep(5)
    except KeyboardInterrupt:
        return


DATABASE = Database("prens.db")
CLEANUP_QUEUE = Queue()

Process(target=heirarchy_cleanup, daemon=True).start()

with DATABASE.connect() as conn:
    conn.initialise_tables()
