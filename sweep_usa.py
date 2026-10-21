from mininet.net import Mininet
from mininet.node import OVSSwitch, Controller
from mininet.link import TCLink
import time
import csv
import re
import math

ALGORITHMS = {
    "slhdsa": ("slhdsa.crt", "slhdsa.key"),
    "ecdsa":  ("ecdsa.crt",  "ecdsa.key"),
    "rsa":    ("rsa.crt",    "rsa.key"),
    "mldsa":  ("mldsa.crt",  "mldsa.key"),
}

LOSS_LEVELS = [0, 1, 3, 5]
RUNS = 100

CITY_PAIRS = [
    ("nyc", "dca"),   # short  — adjacent, ~330 km
    ("lax", "atl"),   # medium — ~3100 km
    ("sea", "nyc"),   # long   — coast-to-coast, multi-hop
]

ENV = (
    "export OQS_ROOT=/home/ubuntu/Desktop/pqc; "
    "export PATH=$OQS_ROOT/openssl-install/bin:$PATH; "
    "export LD_LIBRARY_PATH=$OQS_ROOT/openssl-install/lib64:$OQS_ROOT/liboqs-install/lib; "
    "export OPENSSL_MODULES=$OQS_ROOT/openssl-install/lib64/ossl-modules; "
    "export OPENSSL_CONF=$OQS_ROOT/openssl-install/ssl/openssl.cnf; "
)

USA_CITIES = {
    "sea": (47.6062, -122.3321),  # Seattle
    "lax": (34.0522, -118.2437),  # Los Angeles
    "den": (39.7392, -104.9903),  # Denver
    "chi": (41.8781, -87.6298),   # Chicago
    "dal": (32.7767, -96.7970),   # Dallas
    "atl": (33.7490, -84.3880),   # Atlanta
    "nyc": (40.7128, -74.0060),   # New York City
    "dca": (38.9072, -77.0369),   # Washington D.C.
}

USA_LINKS = [
    ("sea", "lax"), ("sea", "den"),
    ("lax", "den"), ("lax", "dal"),
    ("den", "chi"), ("den", "dal"),
    ("dal", "chi"), ("dal", "atl"),
    ("chi", "nyc"), ("chi", "dca"),
    ("atl", "dca"), ("atl", "nyc"),
    ("nyc", "dca"),
]

def _haversine_km(a, b):
    R = 6371.0
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def _fiber_delay_ms(km):
    return km * 0.005   # fiber ~200,000 km/s -> 5 microsec/km = 0.005 ms/km

def build_usa_network(loss, src, dst):
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink)
    net.addController('c0')

    sw = {}
    for i, city in enumerate(USA_CITIES, start=1):
        sw[city] = net.addSwitch('s%d' % i, failMode='standalone', stp=True)

    for city1, city2 in USA_LINKS:
        d_ms = _fiber_delay_ms(_haversine_km(USA_CITIES[city1], USA_CITIES[city2]))
        net.addLink(sw[city1], sw[city2], delay='%.1fms' % d_ms, loss=loss)

    client = net.addHost('client', ip='10.0.0.2')
    server = net.addHost('server', ip='10.0.0.1')

    net.addLink(client, sw[src], delay='2ms', loss=loss)
    net.addLink(server, sw[dst], delay='2ms', loss=loss)

    net.start()
    print("   waiting for STP to converge (mesh has loops)...")
    time.sleep(45)
    return net, server, client

def run_algorithm(h1, h2, algo_name, cert, key, src, dst, loss, writer):
    h1.cmd("pkill myserver")
    time.sleep(1)
    h1.cmd(ENV + "./myserver %s %s &" % (cert, key))
    time.sleep(2)

    for run in range(1, RUNS + 1):
        output = h2.cmd(ENV + "./myclient 10.0.0.1")
        match = re.search(r"DATA:([\d.]+|FAIL),?(\d*),?(\d*)", output)
        if match and match.group(1) != "FAIL":
            latency = match.group(1)
            bytes_sent = match.group(2)
            bytes_read = match.group(3)
        else:
            latency = "FAIL"
            bytes_sent = "0"
            bytes_read = "0"
        print("    [%s->%s | %s | loss %d%%] run %d: latency=%s ms, read=%s"
              % (src, dst, algo_name, loss, run, latency, bytes_read))
        writer.writerow(["usa", src, dst, loss, algo_name, run, latency, bytes_sent, bytes_read])

    h1.cmd("pkill myserver")
    time.sleep(0.5)

def main():
    with open("result_usa.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["topology", "src", "dst", "loss", "algorithm", "run",
                         "latency_ms", "bytes_sent", "bytes_read"])

        for src, dst in CITY_PAIRS:
            for loss in LOSS_LEVELS:
                print("\n=== USA %s->%s | Loss: %d%% ===" % (src, dst, loss))
                net, h1, h2 = build_usa_network(loss, src, dst)
                for algo_name, (cert, key) in ALGORITHMS.items():
                    run_algorithm(h1, h2, algo_name, cert, key, src, dst, loss, writer)
                net.stop()
    print("Done. Results saved to result_usa.csv")

if __name__ == "__main__":
    main()