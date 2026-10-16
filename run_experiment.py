from mininet.net import Mininet                         # main mininet class
from mininet.node import OVSSwitch, Controller          # switch and controller classes
from mininet.link import TCLink                         # let's you set delays and packet losses
from mininet.cli import CLI                             # let's you interact with the network
import time                                             # time toolbox


# Building the network

net = Mininet(controller = Controller, switch=OVSSwitch, link = TCLink)  # create a network with default controller, OVS switches and links with delay and loss

net.addController('c0')

h1 = net.addHost('h1',ip = '10.0.0.1')
h2 = net.addHost('h2',ip = '10.0.0.2')

s1 = net.addSwitch('s1')

net.addLink(h1,s1)
net.addLink(h2,s1)

net.start()  # start the network

env_setup = (
    "export OQS_ROOT=/home/ubuntu/Desktop/pqc; "
    "export PATH=$OQS_ROOT/openssl-install/bin:$PATH; "
    "export LD_LIBRARY_PATH=$OQS_ROOT/openssl-install/lib64:$OQS_ROOT/liboqs-install/lib; "
    "export OPENSSL_MODULES=$OQS_ROOT/openssl-install/lib64/ossl-modules; "
    "export OPENSSL_CONF=$OQS_ROOT/openssl-install/ssl/openssl.cnf; "
)

h1.cmd(env_setup + "./myserver &")

time.sleep(2)

result = h2.cmd(env_setup + "./myclient 10.0.0.1")

print("---Client Output---")
print(result)


net.stop()