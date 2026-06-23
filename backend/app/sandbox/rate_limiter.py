from ipaddress import ip_address


class RateLimiter:
    def __init__(self, ip_address):
        self.ip_address = ip_address
        self.limit = 5
        self.seconds = 60