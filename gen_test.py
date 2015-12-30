# credits to code from: https://github.com/IanHarvey/bluepy/issues/53

# TODO: get RR values

from bluepy.bluepy.btle import Peripheral, ADDR_TYPE_RANDOM, AssignedNumbers
from pylsl import StreamInfo, StreamOutlet

import time

# replace with MAC of actual device
device_mac = "E3:81:6B:4B:C1:99"

# ugly global variable go retrieve value from delegate
last_bpm = 0

# will likely interpolate data if greater than 1Hz
samplingrate = 10

# create LSL StreamOutlet
print "creating LSL outlet, sampling rate:", samplingrate, "Hz"
info = StreamInfo('hr','hr',1,samplingrate,'float32','conphyturehr1337')
outlet = StreamOutlet(info)

class HRM(Peripheral):
    def __init__(self, addr):
        print "connecting to device", addr, " in random mode"
        Peripheral.__init__(self, addr, addrType=ADDR_TYPE_RANDOM)
        print "...connected"

if __name__=="__main__":
    cccid = AssignedNumbers.client_characteristic_configuration
    hrmid = AssignedNumbers.heart_rate
    hrmmid = AssignedNumbers.heart_rate_measurement

    hrm = None
    try:
        hrm = HRM(device_mac)

        service, = [s for s in hrm.getServices() if s.uuid==hrmid]
        print "Got service"
        ccc, = service.getCharacteristics(forUUID=str(hrmmid))
        print "Got characteristic"
        desc = hrm.getDescriptors(service.hndStart, service.hndEnd)
        d, = [d for d in desc if d.uuid==cccid]
        print "Got descriptor, writing init sequence"
        hrm.writeCharacteristic(d.handle, '\1\0')

        t0=time.time()
        def print_hr(cHandle, data):
            global last_bpm
            bpm = ord(data[1])
            last_bpm = bpm
            print bpm,"%.2f"%(time.time()-t0)
        hrm.delegate.handleNotification = print_hr

        while True:
            hrm.waitForNotifications(1./samplingrate)
            outlet.push_sample([last_bpm])

    finally:
        if hrm:
            # way get ""
            try:
                hrm.disconnect()
                print "disconnected"
            except:
                # may get "ValueError: need more than 1 value to unpack"??
                print "error while disconnecting"
