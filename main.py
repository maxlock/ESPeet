import micropython
import gc
import ubinascii
from math import atan2,sin,cos,radians,degrees
from umqtt.robust import MQTTClient
from time import ticks_ms, ticks_diff
from machine import Pin, Timer, unique_id, freq, Signal

freq(160000000)
micropython.alloc_emergency_exception_buf(100)

def circMean(samples_):
  cosSum_ = 0
  sinSum_ = 0
  n_ = len(samples_)
  for sample_ in samples_:
    cosSum_ += cos(radians(sample_))
    sinSum_ += sin(radians(sample_))
  return (degrees(atan2(sinSum_/n_, cosSum_/n_ )) + 360) % 360

def toSpeed(time_ms_):
  rps_ = 1/(time_ms_/1000)
  if rps_ < 0.05: #20,000ms
    return 0
  elif rps_ < 3.229:
    return -0.1095*(rps_*rps_) + 2.9318*rps_ - 0.1412
  elif rps_ < 54.362:
    return 0.0052*(rps_*rps_) + 2.1980*rps_ + 1.1091
  elif rps_ < 66.332:
    return 0.1104*(rps_*rps_) - 9.5685*rps_ + 329.87

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

anemDebounceTime_ = 0
vaneDebounceTime_ = 0
anemTime_ = 0
anemLastTime_ = 0
anemLastVal_ = anem_.value()
vaneLastVal_ = vane_.value()
anemState_ = 1
vaneState_ = 0
speeds_ = []
directions_ = []

sendData_ = False
sendTimer_ = Timer(-1)
sendTimer_.init(period=2000,mode=Timer.PERIODIC,callback=sendData)

mqtt_server_ = 'homeassistant.technoghetto.int'
mqtt_clientid_ = ubinascii.hexlify(unique_id()).decode('ascii')
mq_ = MQTTClient(mqtt_clientid_,mqtt_server_)
mq_.connect()

while True:
  anemVal_ = anem_.value()
  vaneVal_ = vane_.value()
  now_ = ticks_ms()

  if anemVal_ != anemLastVal_:
    anemDebounceTime_ = now_

  if (ticks_diff(now_,anemDebounceTime_) > debounceDelay_):
    if (anemVal_ != anemState_):
      anemState_ = anemVal_
      ledsig_.value(anemState_)
      if (anemState_ == 1):
        anemLastTime_ = anemTime_
        anemTime_ = anemDebounceTime_
        anemDuration_ = ticks_diff(anemTime_,anemLastTime_)
        speeds_.append(toSpeed(anemDuration_))

  if vaneVal_ != vaneLastVal_:
    vaneDebounceTime_ = now_

  if anemTime_ > 0:
    if (ticks_diff(now_,vaneDebounceTime_) > debounceDelay_):
      if (vaneVal_ != vaneState_):
        vaneState_ = vaneVal_
        if (vaneState_ == 0):
          vaneTime_ = vaneDebounceTime_
          vaneDelay_ = ticks_diff(vaneTime_,anemTime_)
          directions_.append((vaneDelay_/anemDuration_)*360)

  if sendData_ == True:
    sendData_ = False
    gc.collect
    if not speeds_:
      speed_ = "NULL"
    else:
      speed_ = str("%.1f" % (sum(speeds_)/len(speeds_)))
    if not directions_:
      direction_ = "NULL"
    else:
      direction_ = str("%.0f" % circMean(directions_))
    print(speed_+" mph "+direction_+" deg")
    mq_.publish("esp8266/"+mqtt_clientid_+"/wind","TIME:0,WIND:"+speed_+",WDIR:"+direction_)
    directions_.clear()
    speeds_.clear()

  anemLastVal_ = anemVal_
  vaneLastVal_ = vaneVal_
