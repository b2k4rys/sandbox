from ipaddress import ip_address


class RateLimiter:
    def __init__(self, ip_address):
        self.ip_adress = ip_address