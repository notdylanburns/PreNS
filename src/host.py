import re
import socket

HOST_REGEX = r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"


class Host:
    hostname: str
    ttl: int
    labels: list[str]

    def __init__(self, data: dict):
        if data["ttl"] < 60:
            raise ValueError("ttl must be at least 60")

        if not re.match(HOST_REGEX, data["hostname"]):
            raise ValueError("invalid hostname")

        self.hostname = data["hostname"].rstrip(".")
        self.ttl = data["ttl"]
        self.labels = self.hostname.split(".")

    def get_prefixes(self) -> list[str]:
        return [".".join(self.labels[-(i + 1) :]) for i in range(len(self.labels) - 1)]

    # def resolve(self) -> list[str]:
    #     return sorted(
    #         set(
    #             addr[0]
    #             for (af, *_, addr) in socket.getaddrinfo(self.hostname, None)
    #             if af == socket.AddressFamily.AF_INET
    #         )
    #     )
