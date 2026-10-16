from mininet.net import Mininet                         # main mininet class
from mininet.node import OVSSwitch, Controller          # switch and controller classes
from mininet.link import TCLink                         # let's you set delays and packet losses
import time                                             # time toolbox
import csv
import re


# Experiment Configuration
ALGORITHMS = {
    "slhdsa": ("slhdsa.crt", "slhdsa.key"),
    "ecdsa": ("ecdsa.crt", "ecdsa.key"),
    "rsa": ("rsa.crt", "rsa.key"),
    "mldsa":  ("mldsa.crt",  "mldsa.key"),
}

LOSS_LEVELS = [0,1,3,5]
TOPOLOGIES = ["single","multi"]
RUNS=100
# RUNS=3

DELAY = "20ms"  # delay for the links

ENV = (
    "export OQS_ROOT=/home/ubuntu/Desktop/pqc; "
    "export PATH=$OQS_ROOT/openssl-install/bin:$PATH; "
    "export LD_LIBRARY_PATH=$OQS_ROOT/openssl-install/lib64:$OQS_ROOT/liboqs-install/lib; "
    "export OPENSSL_MODULES=$OQS_ROOT/openssl-install/lib64/ossl-modules; "
    "export OPENSSL_CONF=$OQS_ROOT/openssl-install/ssl/openssl.cnf; "
)


def build_network(topology, loss):
    net = Mininet(controller=Controller,switch=OVSSwitch, link = TCLink)
    net.addController('c0')

    h1 = net.addHost('h1',ip="10.0.0.1")
    h2 = net.addHost('h2',ip="10.0.0.2")


    if topology == "single":
        s1 = net.addSwitch('s1')
        net.addLink(h1, s1, delay=DELAY, loss=loss)
        net.addLink(h2, s1, delay=DELAY, loss=loss)
    elif topology == "multi":
        s1 = net.addSwitch('s1')
        s2 = net.addSwitch('s2')
        s3 = net.addSwitch('s3')
        net.addLink(h1,s1,delay=DELAY,loss=loss)
        net.addLink(s1,s2,delay=DELAY,loss=loss)
        net.addLink(h2,s3,delay=DELAY,loss=loss)
        net.addLink(s2,s3,delay=DELAY,loss=loss)

    net.start()
    return net, h1, h2


def run_algorithm(h1,h2,algo_name,cert,key,topology,loss,writer):
    # Start the server on h1 with algo's certificate
    h1.cmd("pkill myserver")  # Ensure no previous server is running
    time.sleep(1)
    h1.cmd(ENV + f"./myserver {cert} {key} &")
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

        print(f"    [{algo_name}] run {run}: latency={latency} ms, sent={bytes_sent}, read={bytes_read}")

        writer.writerow([topology, loss, algo_name, run, latency, bytes_sent, bytes_read])

    h1.cmd("pkill myserver")
    time.sleep(0.5)


def main():
    with open("result.csv","w",newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["topology", "loss", "algorithm", "run", "latency_ms", "bytes_sent", "bytes_read"])

        for topology in TOPOLOGIES:
            for loss in LOSS_LEVELS:
                print(f"---Topology: {topology} | Loss: {loss}%---")
                net, h1, h2 = build_network(topology, loss)

                for algo_name, (cert, key) in ALGORITHMS.items():
                    print(f"Running {algo_name}...")
                    run_algorithm(h1,h2,algo_name,cert,key,topology,loss,writer)

                net.stop()

    print("Done. Results saved to result.csv")


if __name__ == "__main__":
    main()
