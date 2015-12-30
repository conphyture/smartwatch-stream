# credits to code from: https://github.com/IanHarvey/bluepy/issues/53

from bluepy.bluepy.btle import Peripheral, ADDR_TYPE_RANDOM, AssignedNumbers

import time

# replace with MAC of actual device
device_mac = "E3:81:6B:4B:C1:99"

class HRM(Peripheral):
    def __init__(self, addr):
        Peripheral.__init__(self, addr, addrType=ADDR_TYPE_RANDOM)

if __name__=="__main__":
    cccid = AssignedNumbers.client_characteristic_configuration
    hrmid = AssignedNumbers.heart_rate
    hrmmid = AssignedNumbers.heart_rate_measurement

    hrm = None
    try:
        hrm = HRM(device_mac)

        service, = [s for s in hrm.getServices() if s.uuid==hrmid]
        ccc, = service.getCharacteristics(forUUID=str(hrmmid))

        desc = hrm.getDescriptors(service.hndStart, service.hndEnd)
        d, = [d for d in desc if d.uuid==cccid]
        hrm.writeCharacteristic(d.handle, '\1\0')

        t0=time.time()
        def print_hr(cHandle, data):
            bpm = ord(data[1])
            print bpm,"%.2f"%(time.time()-t0)
        hrm.delegate.handleNotification = print_hr

        while True:
            hrm.waitForNotifications(5.)

    finally:
        if hrm:
            hrm.disconnect()
            print "disconnected"
