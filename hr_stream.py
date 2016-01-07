# credits to code from: https://github.com/IanHarvey/bluepy/issues/53

# TODO: get all RR values?

from bluepy.bluepy.btle import Peripheral, ADDR_TYPE_RANDOM, AssignedNumbers
from pylsl import StreamInfo, StreamOutlet

import time, struct

# replace with MAC of actual device
device_mac = "E3:81:6B:4B:C1:99"

# ugly global variable go retrieve value from delegate
last_bpm = 0
last_rr = 0

# will likely interpolate data if greater than 1Hz
samplingrate = 16

# create LSL StreamOutlet
print "creating LSL outlet for heart-rate, sampling rate:", samplingrate, "Hz"
info_hr = StreamInfo('hr','hr',1,samplingrate,'float32','conphyturehr1337')
outlet_hr = StreamOutlet(info_hr)

print "creating LSL outlet for RR intervals, sampling rate:", samplingrate, "Hz"
info_rr = StreamInfo('rr','rr',1,samplingrate,'float32','conphyturehr1337')
outlet_rr = StreamOutlet(info_rr)

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
            global last_bpm, last_rr
            bpm = ord(data[1])
            last_bpm = bpm
            print "BPM:", bpm, "- time: %.2f"%(time.time()-t0),
            # if retrieved data is longer, we got RR interval, take the first
            if len(data) >= 4:
                # UINT16 format
                rr = struct.unpack('H', data[2:4])[0]
                # units of RR interval is 1/1024 sec
                rr = rr/1024.
                last_rr = rr
                print "- RR:", rr,
            print ""

        hrm.delegate.handleNotification = print_hr

        while True:
            hrm.waitForNotifications(1./samplingrate)
            outlet_hr.push_sample([last_bpm])
            outlet_rr.push_sample([last_rr])

    finally:
        if hrm:
            # way get ""
            try:
                hrm.disconnect()
                print "disconnected"
            except:
                # may get "ValueError: need more than 1 value to unpack"??
                print "error while disconnecting"
