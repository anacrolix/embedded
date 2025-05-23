import network
import time
import socket
import erumplib
import requests
import gc
import math

from picozero import pico_led, LED

red_led = LED(18)
yellow_led = LED(17)
green_led = LED(16)

LED_SUFFIX = '_led'

def get_all_colors():
    return ['red', 'yellow', 'green']

def set_leds(*colors):
    for a in globals():
        if a.endswith(LED_SUFFIX) and a[:-len(LED_SUFFIX)] not in colors:
            globals()[a].off()
    for a in colors:
        globals()[a+'_led'].on()

async def cycle_leds():
    while True:
        for color in get_all_colors():
            yield
            set_leds(color)

def test_cycle_leds():
    do_leds = cycle_leds()
    while True:
        do_leds.send(None)
        time.sleep(1)

def connect_wlan(deets):
    set_leds()
    yellow_led.blink()
    wlan = network.WLAN(network.WLAN.IF_STA)
    print('initial wlan status:', erumplib.wlan_status_name(wlan.status()))
    print('initial ssid:', wlan.config('ssid'))
    wlan.active(True)
    print(wlan.isconnected())
    if wlan.config('ssid') != deets[0]:
        for a in wlan.scan():
            print(a)
        wlan.connect(*deets)
        while not wlan.isconnected():
            print('not yet connected')
            time.sleep(1)
    print(wlan.ifconfig())

class Socket(socket.socket):
    _superclass = socket.socket    
    if not hasattr(_superclass, '__enter__') and not hasattr(_superclass, '__exit__'):
        def __enter__(self):
            return self
        def __exit__(self, *_):
            self.close()

def ntfy():
    resp = requests.post("https://ntfy.sh/erupinger", data=str(delay).encode())
    assert resp.status_code == 200, resp.status_code
    took = (time.time_ns()-start)/1e9
    resp.close()
    print(f'ntfy took {took}')
    
def mean(data):
    return sum(data)/len(data)

def stdev(data):
    n = len(data)
    if n == 1:
        return 0
    m = mean(data)
    return math.sqrt(sum((a-m)**2 for a in data)/(n-1))

def pstdev(data, mu):
    n = len(data)
    return math.sqrt(sum((a-mu)**2 for a in data)/n)

def time_connect():
    addr = socket.getaddrinfo('micropython.org', 80)[0][-1]
    latest_times = []
    p_n = 0
    p_sum = 0
    while True:
        pico_led.on()
        with Socket() as s:
            start = time.time_ns()
            s.settimeout(10)
            try:
                s.connect(addr)
            except Exception as exc:
                print(f'error connecting: {exc}')
                set_leds('red')
        pico_led.off()
        ns = time.time_ns() - start
        delay = ns/1e9
        p_sum += delay
        p_n += 1
        latest_times.append(delay)
        while len(latest_times) > 10:
            latest_times.pop(0)
        mu = p_sum/p_n
        _pstdev = pstdev(latest_times, mu)
        #print(delay, gc.mem_free())
        print(mu, mu+_pstdev, delay, _pstdev, stdev(latest_times))
        avg = sum(latest_times)/len(latest_times)
        if delay >= 10:
            set_leds('red')
        elif delay > 0.5:
            set_leds()
            yellow_led.blink()
        elif delay > mu+_pstdev:
            set_leds('yellow', 'green')
        else:
            set_leds('green')
        start = time.time_ns()
        time.sleep(1)

TPLINK = ('fleetwind_tplink', 'Foxlow#5')
STARLINK24 = ('fleetwind_starlink-2.4GHz', 'Foxlow$5')

def main():
    try:
        connect_wlan(STARLINK24)
        time_connect()
    except:
        set_leds()
        red_led.blink()
        pico_led.blink()
        raise

main()
#test_cycle_leds()