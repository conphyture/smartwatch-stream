# credits to code from: https://github.com/IanHarvey/bluepy/issues/53

# TODO: get all RR values?

from bluepy.btle import Peripheral, ADDR_TYPE_RANDOM, AssignedNumbers
import time, timeit, struct, argparse, thread

class HRM():
    def __init__(self, addr, israte, threaded_connection = False):
        """
        Init smartwatch, will launch upon init
            addr: MAC address to connect to
            threaded_connection: will try to connect in a separate thread
            israte: sampling rate of the data coming from device (Hz)

        """
        self.addr = addr
        self.israte = israte
        self.threaded_connection = threaded_connection
        # waiting for connetion
        self.active = False
        self.connecting = False
        # we cannot change that yet, how between two connection attempts (in seconds)
        self.reco_timeout = 2
        self.last_con = 0
    
        # last value for both,
        self.bpm = -1
        self.rr = -1
    
        self.tick = timeit.default_timer()

        self.connect()
        
    def connect(self):
        """
        Attempt to (re)connect to device if not active.
        FIXME: put some lock for more reliability
        """
        # don't try to go further if already connected are getting to it
        if self.active or self.connecting:
          return 
        self.connecting = True
        if self.threaded_connection:
            print("BLE: Will attempt to connect through a separate thread.")
            thread.start_new_thread(self._do_connect, ())
        else:
            self._do_connect() 
    
    def _do_connect(self):
        """ The actual function for connection, connect() should be called to handle optional threading. """
        # we don't do double connections
        if self.active:
          return
      
         # first resolve said stream type on the network
        self.last_con = timeit.default_timer()
    
        cccid = AssignedNumbers.client_characteristic_configuration
        hrmid = AssignedNumbers.heart_rate
        hrmmid = AssignedNumbers.heart_rate_measurement
    
        try: 
            print "connecting to device", self.addr, " in random mode"
            self.per = Peripheral(self.addr, addrType=ADDR_TYPE_RANDOM)
            print "...connected"
    
            service, = [s for s in self.per.getServices() if s.uuid==hrmid]
            print "Got service"
            ccc, = service.getCharacteristics(forUUID=str(hrmmid))
            print "Got characteristic"
            desc = self.per.getDescriptors(service.hndStart, service.hndEnd)
            d, = [d for d in desc if d.uuid==cccid]
            print "Got descriptor, writing init sequence"
            self.per.writeCharacteristic(d.handle, '\1\0')
    
    
            self.per.delegate.handleNotification = self._get_hr
    
            self.active = True
            self.connecting = False

        except Exception as e:
            print "Something went wrong while connecting: ", str(e)
            self.active = False
            self.connecting = False
        
    def _get_hr(self, cHandle, data):
        """ callback for new values from self.per """
        bpm = ord(data[1])
        self.bpm = bpm
        print "BPM:", bpm, "- time: %.2f"%(timeit.default_timer()-self.tick),
        # if retrieved data is longer, we got RR interval, take the first
        if len(data) >= 4:
            # UINT16 format
            rr = struct.unpack('H', data[2:4])[0]
            # units of RR interval is 1/1024 sec
            rr = rr/1024.
            self.rr = rr
            print "- RR:", rr,
        print ""

    def process(self):
        """
        Wait to pull data. Blocking call until new data or until should have received one.
        NB: might try to connect and block for few seconds.
        """
    
        # nothing to if not connected -- but still blocking with samplingrate
        if not self.isActive():
            time.sleep(1./self.israte)
    
        if self.active:
          # FIXME: should detect disconnect
          try:
            self.per.waitForNotifications(1./self.israte)
          # on any error we quit
          except Exception as e:
            print("Something went wrong while waiting for a new sample: " + str(e))
            print("Disconnect")
            try:
              self.per.disconnect()
              print("disconnected")
            except:
              print("error while disconnecting")
            self.active = False
            
    def isActive(self):
        """ getter for state of the connection + try to reco periodically if necessary. """
        if self.active == False and abs(self.last_con-timeit.default_timer())>=self.reco_timeout:
          self.connect() 
        
        return self.active
    
    def disconnect(self):
        if self.active:
            # way get ""
            try:
                self.per.disconnect()
                print "disconnected"
            except:
                # may get "ValueError: need more than 1 value to unpack"??
                print "error while disconnecting"


if __name__=="__main__":
    from pylsl import StreamInfo, StreamOutlet
    # retrieve MAC address
    parser = argparse.ArgumentParser(description='Stream heart rate of bluetooth BLE compatible devices using LSL.')
    parser.add_argument("device_mac", help="MAC address of the MAC device")
    parser.add_argument("-id", "--id", help="Identifier for the device (default: 1), . Should be unique on the network", default=1, type=int)
    args = parser.parse_args()

    # will likely interpolate data if greater than 1Hz
    samplingrate = 16
    
    # setting type for smartwatch
    lsl_type = "watch_" + str(args.id)
    lsl_id =  "conphyturehr1337_" + str(args.id)
    
    print "creating LSL of types: ", lsl_type
    
    # create LSL StreamOutlet
    print "creating LSL outlet for heart-rate, sampling rate:", samplingrate, "Hz"
    info_hr = StreamInfo('hr',lsl_type, 1, samplingrate, 'float32', lsl_id + "_hr")
    outlet_hr = StreamOutlet(info_hr)
    
    print "creating LSL outlet for RR intervals, sampling rate:", samplingrate, "Hz"
    info_rr = StreamInfo('rr','rr',1,samplingrate,'float32', lsl_id + "_rr")
    outlet_rr = StreamOutlet(info_rr)


    hrm = HRM(args.device_mac, samplingrate, threaded_connection = True)
    
    try:
        while True:
            hrm.process()
            outlet_hr.push_sample([hrm.bpm])
            outlet_rr.push_sample([hrm.rr])
            
    finally:
        print "exiting"
        hrm.disconnect()
