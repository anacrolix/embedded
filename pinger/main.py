import network
import time
import socket
import erumplib
import requests
import gc
import math
import tm1637
from machine import Pin

from erumplib import LorikeetNeopixel
from picozero import pico_led, LED

red_led = LED(18)
yellow_led = LED(17)
green_led = LED(16)


class RGB(tuple):
    
    def blend(self, other, ratio=0.5):
        return RGB(a*(1-ratio)+ratio*other[i] for i, a in enumerate(self))
    
class RGBs:
    pass

for color, values in {
    'red': (255, 0, 0),
    'amber': (0xff, 0xbf, 0),
    'green': (0, 255, 0),
}.items():
    setattr(RGBs, color.upper(), RGB(values))
        


tm = tm1637.TM1637(clk=Pin(13), dio=Pin(12))
neo = LorikeetNeopixel(pin=0)
neo.clear()
neo.brightness(25)
neo[:] = [
    RGBs.GREEN,
    RGBs.GREEN.blend(RGBs.AMBER),
    RGBs.AMBER,
    RGBs.AMBER.blend(RGBs.RED),
    RGBs.RED,
]
#neo.set_pixel_line_gradient(0, 4, RGBs.green, RGBs.red)
#neo.fill(RGBs.red)
neo.show()


CONNECT_ADDRS = [
    ('micropython.org', 80),
    ('google.com', 80),
    ('192.168.1.31', 9091),
]
CONNECT_ADDR = CONNECT_ADDRS[0]
CONNECT_TIMEOUT = 10000

LED_SUFFIX = '_led'

def get_all_colors():
    return ['red', 'yellow', 'green']

def get_color_led(color):
    return globals()[color+LED_SUFFIX]

def set_leds(*colors, **methods):
    for a in colors:
        get_color_led(a).on()
    for color, method in methods.items():
        getattr(get_color_led(color), method)()
    for color in get_all_colors():
        if color in methods:
            continue
        if color in colors:
            continue
        get_color_led(color).off()

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
    tm.show('wifi')
    set_leds()
    yellow_led.blink()
    wlan = network.WLAN(network.WLAN.IF_STA)
    print('initial wlan status:', erumplib.wlan_status_name(wlan.status()))
    print('initial ssid:', wlan.config('ssid'))
    wlan.active(True)
    print(wlan.isconnected())
    if wlan.config('ssid') != deets[0] or not wlan.isconnected():
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

def decay_avg(times):
    div = 2
    sum = 0
    for t in reversed(times):
        sum += t/div
        #print(sum, t, div)
        div *= 2
    return sum

def get_neo_rgbs(last_times):
    sorted_scores = list(sorted(last_times))
    def get_index(of):
        for j, val in enumerate(sorted_scores):
            if of < val:
                return j
        else:
            return len(sorted_scores)        
    for i in range(5):
        try:
            val = last_times[-i-1]
        except IndexError:
            yield RGBs.GREEN
        else:
            pos = get_index(val)
            ratio = max(pos/len(last_times)*2-1, 0)
            print('ratio', ratio)
            yield RGBs.GREEN.blend(RGBs.RED, ratio=ratio)

def time_connect():
    addr = socket.getaddrinfo(*CONNECT_ADDR)[0][-1]
    print(addr)
    latest_times = []
    p_n = 0
    p_sum = 0
    while True:
        pico_led.on()
        try:
            with Socket() as s:
                start = time.time_ns()
                s.settimeout(CONNECT_TIMEOUT/1000)
                try:
                    s.connect(addr)
                except Exception as exc:
                    print(f'error connecting: {exc}')
                    set_leds('red')
        finally:
            pico_led.off()
        
        ns = time.time_ns() - start
        delay = ns/1e6
        p_sum += delay
        p_n += 1
        latest_times.append(delay)
        while len(latest_times) > 100:
            latest_times.pop(0)
        mu = p_sum/p_n
        _pstdev = pstdev(latest_times, mu)
        _stdev = stdev(latest_times)
        avg = sum(latest_times)/len(latest_times)
        
        #print(delay, gc.mem_free())
        if False:
            sigma = _stdev
            mean = avg
        else:
            sigma = _pstdev
            mean = mu
        
        print(
            "last", round(delay),
            "mean", round(mean),
            "pstdev", round(_pstdev),
            "stdev", round(_stdev),
        )
        #tm_n = ns//1000000
        # Ceil because my decay algorithm would always fall short without infinite data points.
        tm_n = math.ceil(decay_avg(latest_times))
        tm.number(tm_n)
        
        if delay >= CONNECT_TIMEOUT:
            set_leds(red='blink')
        elif delay > mean+3*sigma:
            set_leds(yellow='blink')
        elif delay > mean+2*sigma:
            set_leds(green='blink')
        else:
            set_leds('green')
        neo[:] = list(get_neo_rgbs(latest_times))
        neo.show()
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
        raise

main()
#test_cycle_leds()