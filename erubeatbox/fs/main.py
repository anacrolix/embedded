from picozero import Speaker, LED, pico_led, pico_temp_sensor, Button
from asyncio import sleep
import gc
import network
import socket
from asyncio import create_task
import asyncio
import _thread
import time
import random
import sys

speaker = Speaker(5)
led = LED(15)
button = Button(14)
dot_led = LED(16)

BEAT = 0.25 # 240 BPM

liten_mus = [ ['d5', BEAT / 2], ['d#5', BEAT / 2], ['f5', BEAT], ['d6', BEAT], ['a#5', BEAT], ['d5', BEAT],  
              ['f5', BEAT], ['d#5', BEAT], ['d#5', BEAT], ['c5', BEAT / 2],['d5', BEAT / 2], ['d#5', BEAT], 
              ['c6', BEAT], ['a5', BEAT], ['d5', BEAT], ['g5', BEAT], ['f5', BEAT], ['f5', BEAT], ['d5', BEAT / 2],
              ['d#5', BEAT / 2], ['f5', BEAT], ['g5', BEAT], ['a5', BEAT], ['a#5', BEAT], ['a5', BEAT], ['g5', BEAT],
              ['g5', BEAT], ['', BEAT / 2], ['a#5', BEAT / 2], ['c6', BEAT / 2], ['d6', BEAT / 2], ['c6', BEAT / 2],
              ['a#5', BEAT / 2], ['a5', BEAT / 2], ['g5', BEAT / 2], ['a5', BEAT / 2], ['a#5', BEAT / 2], ['c6', BEAT],
              ['f5', BEAT], ['f5', BEAT], ['f5', BEAT / 2], ['d#5', BEAT / 2], ['d5', BEAT], ['f5', BEAT], ['d6', BEAT],
              ['d6', BEAT / 2], ['c6', BEAT / 2], ['b5', BEAT], ['g5', BEAT], ['g5', BEAT], ['c6', BEAT / 2],
              ['a#5', BEAT / 2], ['a5', BEAT], ['f5', BEAT], ['d6', BEAT], ['a5', BEAT], ['a#5', BEAT * 1.5]]

# Hack speeds for testing.
beat_mult = 1.2

def duration(tempo, t):
    
    # calculate the duration of a whole note in milliseconds (60s/tempo)*4 beats
    wholenote = (60000 / beat_mult / tempo) * 4
    
    # calculate the duration of the current note
    # (we need an integer without decimals, hence the // instead of /)
    if t > 0:
      noteDuration = wholenote / t
    elif (t < 0):
      # dotted notes are represented with negative durations
      noteDuration = wholenote / abs(t)
      noteDuration *= 1.5 # increase their duration by a half
    
    return noteDuration

def play_all():
    try:
        speaker.play(liten_mus)
           
    finally: # Turn speaker off if interrupted
        speaker.off()

def play_each():
    try:
        for note in liten_mus:
            led.on()
            speaker.play(note)
            led.off()
            sleep(0.1) # leave a gap between notes
           
    finally: # Turn speaker off if interrupted
        speaker.off()

def collect(msg):
    before = gc.mem_alloc()
    gc.collect()
    after = gc.mem_alloc()
    print(f'collecting memory at {msg}: {before} -> {after}')

def load_melodies(keep=None):
    collect('load melodies')
    global melody
    from melodies import melody as a    
    collect('imported melodies')   
    melody = a
    if keep is not None:
        for i in reversed(range(len(melody))):
            if i not in keep:
                melody.pop(i)
    melody.sort(key=len)
    collect('sorted melodies')

from notes import notes as freqs

def show_melodies():
    i = 0
    for mel in melody:
        name, tempo, *sounds = mel
        print(f'#{i}: {name}: tempo={tempo}, notes={len(sounds)//2}')
        i += 1

song_skip = False
cur_song_name = None

def play_song(song):
    name = song[0]
    global cur_song_name
    cur_song_name = song[0]
    tempo = song[1]
    print(f'playing {name}: tempo {tempo}')
    sound_iter = iter(song[2:])
    start_time = time.ticks_us()
    while not skip_song:
        try:
            note = next(sound_iter)
        except StopIteration:
            break
        dur = int(next(sound_iter))
        freq = freqs[note]
        dur_ms = duration(tempo, dur)
        dur_s_f = dur_ms/1000
        dur_us = dur_ms*1000
        print(note, dur, dur_s_f, dur_us)
        if freq is not None:
            led.on()
            if dur < 0:
                dot_led.on()
        drift = time.ticks_diff(start_time, time.ticks_us())/1e6
        print(f'drift: {drift}')
        start_time = time.ticks_add(start_time, round(dur_us))
        speaker.play([freq, dur_s_f*0.9])
        led.off()
        dot_led.off()
        time.sleep(0.1*dur_s_f)

def play(melodies):
    global skip_song
    for mel in melodies:
        skip_song = False
        play_song(mel)
        sleep(1)    

def play_all_melodies():
    play(melody)

def melodies_at_random():
    remaining = melody.copy()
    while remaining:
        yield remaining.pop(random.randrange(len(remaining)))
            
def play_randomly():
    play(melodies_at_random())

def play_in_order():
    play(melody)

# Take this from erumplib...
def wlan_status_name(status):
    prefix = 'STAT_'
    for name in dir(network):
        if not name.startswith(prefix):
            continue
        value = getattr(network, name)
        if value == status:
            return name[len(prefix):].lower()
    raise KeyError(status)

async def start_ap():
    ap = network.WLAN(network.WLAN.IF_AP) # create access-point interface
    ap.config(ssid='EruBeatBox', security=0, key='')              # set the SSID of the access point
    #ap.config(max_client=1)             # set how many clients can connect to the network
    ap.active(True)
    def print_status():
        status_str = wlan_status_name(ap.status())
        print(f'ap status: {status_str}, {ap.ifconfig()}')
#     while not ap.isconnected():
#         print_status()
#         await sleep(1)
    print('ap ready')
    print_status()
    return ap

cunt = 1
    
async def serve_counter(client):
    global cunt
    buf = b''
    while True:
        await readable(client)
        buf += client.recv(1024)
        print(buf)
        if b'\r\n\r\n' in buf:
            break
    if not buf.startswith('GET / '):
        return
    send_ret = client.send(f'''
HTTP/1.1 200 OK\r
Content-Type: text/plain\r
Refresh: 1\r
\r
g\'day cunt #{cunt}. the cpu temperature is {pico_temp_sensor.temp}

The current track is {cur_song_name}
'''.lstrip())
    print(f'socket send returned {send_ret}')
    cunt += 1

async def print_recv(conn):
    while True:
        await readable(conn)
        try:
            buf = conn.recv(1024)
        except Exception as exc:
            print(f'error receiving from {conn}: {exc}')
            return
        print(buf)
        if not buf:
            return

async def serve_http(conn):
    try:
        # TODO: Have this on when there are any outstanding conns.
        #pico_led.on()
        await serve_counter(conn)
    finally:
        conn.close()
        #pico_led.off()

async def serve(conn):
    while True:
        await readable(conn)
        client, addr = conn.accept()
        print(f'accepted http connection from {addr}')
        asyncio.create_task(serve_http(client))        
    
def open_socket():
    address = ('', 80)
    conn = socket.socket()
    conn.bind(address)
    conn.listen(1)
    conn.setblocking(False)
    return conn

async def http_server():
    conn = open_socket()
    await serve(conn)

def create_dns_catchall_reply(request, ip):
    response = request[:2] # request id
    response += b"\x81\x80" # response flags
    response += request[4:6] + request[4:6] # qd/an count
    response += b"\x00\x00\x00\x00" # ns/ar count
    response += request[12:] # origional request body
    response += b"\xC0\x0C" # pointer to domain name at byte 12
    response += b"\x00\x01\x00\x01" # type and class (A record / IN class)
    response += b"\x00\x00\x00\x3C" # time to live 60 seconds
    response += b"\x00\x04" # response length (4 bytes = 1 ipv4 address)
    response += bytes(map(int, ip.split("."))) # ip address parts
    return response

async def readable(socket):
    yield asyncio.core._io_queue.queue_read(socket)

async def serve_catchall_dns(socket, catchall_ip):
    while True:
        await readable(socket)
        request, client = socket.recvfrom(256)
        print(f'received dns query from {client}: {request}')
        response = create_dns_catchall_reply(request, catchall_ip) 
        socket.sendto(response, client)

async def dns_catchall_server(ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    print(f'creating dns server on {ip}')
    sock.bind((ip, 53))
    sock.setblocking(False)
    await serve_catchall_dns(sock, ip)
    
def run_ap():
    ap = start_ap()
    infos = socket.getaddrinfo(ap.ifconfig()[0], 53, 0, socket.SOCK_DGRAM)
    print(f'getaddrinfo for dns server: {infos}')
    #pico_led.on()
    addrinfo_ip = infos[0][-1][0]
    return dns_server(addrinfo_ip)
    
async def network_main():
    ap = await start_ap()
    ap_ifconfig = ap.ifconfig()
    print(f'ap started, ifconfig: {ap_ifconfig}')
    await asyncio.gather(
        create_task(dns_catchall_server(ap_ifconfig[0])),
        create_task(http_server()),
    )              

async def async_main():
    await asyncio.gather(
        asyncio.create_task(network_main()),
    )

def set_skip_song():
    print('skip song')
    global skip_song
    skip_song = True

button.when_pressed = set_skip_song 

def music_thread():
    play_in_order()
    while True:
        play_randomly()

def main():
    pico_led.on()
    led.pulse()
    #dot_led.pulse()
    load_melodies([0, 4, 7, 8, 13, 23, 25, 26, 27, 33, 37])
    _thread.start_new_thread(asyncio.run, (async_main(),))
    wait_for_button_press()
    music_thread()

def wait_for_button_press():
    pico_led.blink()
    while not button.is_pressed:
        pass
    pico_led.off()    

def main_crash_log():
    try:
        f = open('crash.log', 'w')
        main()
    except Exception as exc:
        sys.print_exception(exc, f)
        raise
    finally:
        f.close()
    led.off()
    pico_led.on()
    
def for_jack():
    load_melodies([4, 8, 27])
    wait_for_button_press()
    play_in_order()

if __name__ == '__main__':
    main_crash_log()
    #for_jack()
    