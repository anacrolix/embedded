# Have alternating blue/some other color leds for bluetooth or wifi mode.
# Show heat on RGBLED

import asyncio
import aioble
from picozero import pico_led
import bluetooth
import sys
import aioble.core

GAP_SERVICE = bluetooth.UUID(0x1800)

def print_ble_device(scan_result):
    r = scan_result    
    print(r.name())
    print(r.device)
    print(r.adv_data)
    print(r.resp_data)
    print(r.rssi)
    print(r.connectable)
    for m in r.manufacturer():
        print(m)
    for svc in r.services():
        print(svc)

async def get_name_from_gatt(device):
    print('getting name from gatt', device)
    try:
        conn = await device.connect()
    except asyncio.TimeoutError:
        aioble.core.ble.gap_connect(None)
        return
    except Exception as exc:
        sys.print_exception(exc)
        aioble.core.ble.gap_connect(None)
        return
    async with conn:
        if False:
            gap_service = None
            async for svc in conn.services():
                print(svc)
                if svc.uuid == GAP_SERVICE:
                    gap_service = svc
        else:
            gap_service = await conn.service(uuid=bluetooth.UUID(GAP_SERVICE))
        if gap_service is None:
            return
        if True:
            chars = []
            async for char in gap_service.characteristics():
                chars.append(char)
            for char in chars:
                print(await char.read())
            return None
        else:
            name_char = await gap_service.characteristic(uuid=bluetooth.UUID(0x2A00))
        name_bytes = await name_char.read()
        return name_bytes.decode()

async def scan_for_new_devices(devices):
    pico_led.blink()
    try:
        async with aioble.scan(duration_ms=0, interval_us=30000, window_us=30000, active=False) as scanner:
            async for result in scanner:
                if not hasattr(result, 'device'):
                    print('result with no device:', result)
                    continue
                device = result.device
                name = result.name()
                if name:
                    print(f'device {device} advertised name {name}')
                if device not in devices:
                    return result
    finally:
        pico_led.off()

async def scan_main():
    devices = set()
    while True:
        result = await scan_for_new_devices(devices)
        new_dev = result.device
        name = await get_name_from_gatt(new_dev)
        print(name)
        devices.add(new_dev)
            
asyncio.run(scan_main())