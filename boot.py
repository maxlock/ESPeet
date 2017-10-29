import network
import webrepl

WIFI_ESSID = 'Technoghetto_2G4'
WIFI_PASS = 'qwertyuiopasdfghjklzxcvbnm'

def do_connect_sta():
  sta_if = network.WLAN(network.STA_IF)
  if not sta_if.isconnected():
    print('connecting to network...')
    sta_if.active(True)
    sta_if.connect(WIFI_ESSID, WIFI_PASS)
    while not sta_if.isconnected():
      pass
  print('network config:', sta_if.ifconfig())

def do_disable_ap():
  ap_if = network.WLAN(network.AP_IF)
  if ap_if.active():
    ap_if.active(False)
  print('AP interface disabled')

do_disable_ap()
do_connect_sta()
webrepl.start()

