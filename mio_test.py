import binascii
import struct
import time
from bluepy.bluepy.btle import UUID, Peripheral, DefaultDelegate

# replace with MAC of actual device
device_mac = "E3:81:6B:4B:C1:99"

# following config should be standard for BLE devices sending HR data, see e.g. for those codes: http://blog.akhq.net/2014/11/polar-h7-bluetooth-le-heart-rate-sensor.html

# uuid for heart rate service
service_uuid = UUID(0x180d)
# handle for HR notifications
char_uuid = UUID(0x2a37)
# start HR stream
notify_start = '0\0\1\0'

class MyDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)
        print "delegate init"
        # ... initialise here

    def handleNotification(self, cHandle, data):
        print "delegate got data"
        # ... perhaps check cHandle
        # ... process 'data'

print "connecting to device", device_mac, " in random mode"
p = Peripheral(device_mac, "random")
print "...connected"
p.setDelegate( MyDelegate())

try:
    svc = p.getServiceByUUID( service_uuid )
    print "Got service"

    ch_list = svc.getCharacteristics( char_uuid )
    if len(ch_list) < 1:
        raise ValueError("Error, received no characteristics")

    print ch_list
    
    ch = ch_list[0] 
    print "Got characteristic, writing init sequence"
    ch.write(notify_start)
    while True:
        if p.waitForNotifications(1.0):
            print "got data"
            # handleNotification() was called
            continue

        print "Waiting..."
finally:
    p.disconnect()
    print "Disconnected..."
