# PreNS

PreNS (Pre-DNS) is a utility to periodically query a list of domain names in order to keep the cache fresh.
There are 2 main components:
- An API server in `app.py`
- A daemon to periodically query the domains in `prensd`

To start the server, you should run `prens-server`. This will start the server on port 80 (may require root privileges).
To start the daemon, you should run `prensd`. This will run in the foreground.

When the server is running, you will be able to access a web frontend at `http://localhost/` where you can add/remove domains to be queried.
The domain list is stored in a database file called `prens.db` in the current directory.
