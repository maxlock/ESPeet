import micropython
import gc
import ubinascii
from math import atan2,sin,cos,radians,degrees
from umqtt.robust import MQTTClient
from time import ticks_ms, ticks_diff
from machine import Pin, Timer, unique_id, freq, Signal

freq(160000000)
micropython.alloc_emergency_exception_buf(100)

# return average of angles in degrees
def circMean(samples_):
  cosSum_ = 0
  sinSum_ = 0
  n_ = len(samples_)
  for sample_ in samples_:
    cosSum_ += cos(radians(sample_))
    sinSum_ += sin(radians(sample_))
  return (degrees(atan2(sinSum_/n_, cosSum_/n_ )) + 360) % 360

# return speed in kmph from rotation duration in ms
def toSpeed(time_ms_):
  rps_ = 1/(time_ms_/1000)
  if rps_ < 0.05: #20,000ms
    return 0
  elif rps_ < 3.229:
    return (-0.1095*(rps_*rps_) + 2.9318*rps_ - 0.1412) * 1.60934
  elif rps_ < 54.362:
    return (0.0052*(rps_*rps_) + 2.1980*rps_ + 1.1091) * 1.60934
  elif rps_ < 66.332:
    return (0.1104*(rps_*rps_) - 9.5685*rps_ + 329.87) * 1.60934

# handle sendTimer interrupt
def sendData(x):
  global sendData_
  sendData_ = True

debounceDelay_ = 20
vane_pin_ = 5
anem_pin_ = 4
led_pin_ = 2

vane_ = Pin(vane_pin_, Pin.IN, Pin.PULL_UP)
anem_ = Pin(anem_pin_, Pin.IN, Pin.PULL_UP)
led_ = Pin(led_pin_, Pin.OUT)
ledsig_ = Signal(led_, invert=True)

anemDebounceTimeStamp_ = 0
vaneDebounceTimeStamp_ = 0
anemTimeStamp_ = 0
anemLastTimeStamp_ = 0
anemGpioLastVal_ = anem_.value()
vaneGpioLastVal_ = vane_.value()
anemGpioState_ = 1
vaneState_ = 0
speeds_ = []
angles_ = []

sendData_ = False
sendTimer_ = Timer(-1)
sendTimer_.init(period=2000,mode=Timer.PERIODIC,callback=sendData)

mqtt_server_ = 'homeassistant.technoghetto.int'
mqtt_clientid_ = ubinascii.hexlify(unique_id()).decode('ascii')
mq_ = MQTTClient(mqtt_clientid_,mqtt_server_)
mq_.connect()

# Loop forever
while True:
  # Read GPIOs
  anemGpioVal_ = anem_.value()
  vaneGpioVal_ = vane_.value()
  now_ = ticks_ms()

  # If anemometer gpio state changed, record time in anemDebounceTimeStamp_
  if anemGpioVal_ != anemGpioLastVal_:
    anemDebounceTimeStamp_ = now_

  # If anemometer gpio state is stable and debounced
  if (ticks_diff(now_,anemDebounceTimeStamp_) > debounceDelay_):
    # if anemometer gpio state has changed
    if (anemGpioVal_ != anemGpioState_):
      # record new anemometer state
      anemGpioState_ = anemGpioVal_
      ledsig_.value(anemGpioState_)
      # if new anemometer state is high
      if (anemGpioState_ == 1):
        # move last rotations start time to anemLastTime
        anemLastTimeStamp_ = anemTimeStamp_
        # move this rotations start time to anemTimeStamp_
        anemTimeStamp_ = anemDebounceTimeStamp_
        # record this rotations duration
        anemDuration_ = ticks_diff(anemTimeStamp_,anemLastTimeStamp_)
        # calculate this rotations speed from duration, and append to speeds array
        speeds_.append(toSpeed(anemDuration_))

  # If vane gpio state changed, record time in vaneDebounceTimeStamp_
  if vaneGpioVal_ != vaneGpioLastVal_:
    vaneDebounceTimeStamp_ = now_

  # If we have a rotation duration
  if anemTimeStamp_ > 0:
    # if vane gpio state is stable and debounced
    if (ticks_diff(now_,vaneDebounceTimeStamp_) > debounceDelay_):
      # if vane gpio state has changed
      if (vaneGpioVal_ != vaneState_):
        # record new vane state
        vaneState_ = vaneGpioVal_
        # if new vane state is low
        if (vaneState_ == 0):
          # record this rotations vane time
          vaneTimeStamp_ = vaneDebounceTimeStamp_
          # record time from start of this rotation to vane state change
          vaneDelay_ = ticks_diff(vaneTimeStamp_,anemTimeStamp_)
          # calculate angle from from rotation duration and vane delay time. Append it to angles array
          angles_.append((vaneDelay_/anemDuration_)*360)

  if sendData_ == True:
    sendData_ = False
    gc.collect
    if not speeds_:
      speed_ = "NULL"
    else:
      speed_ = str("%.1f" % (sum(speeds_)/len(speeds_)))
    if not angles_:
      angle_ = "NULL"
    else:
      angle_ = str("%.0f" % circMean(angles_))
    print(speed_+" kmph "+angle_+" deg")
    mq_.publish("espeet/"+mqtt_clientid_+"/wxmesh","TIME:0,windSpeed:"+speed_+",windDir:"+angle_)
    mq_.publish("espeet/"+mqtt_clientid_+"/speed",speed_)
    mq_.publish("espeet/"+mqtt_clientid_+"/angle",angle_)
    angles_.clear()
    speeds_.clear()

  anemGpioLastVal_ = anemGpioVal_
  vaneGpioLastVal_ = vaneGpioVal_
