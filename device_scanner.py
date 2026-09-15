import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning for Bluetooth devices...")
    devices = await BleakScanner.discover(timeout=5.0)

    n_dev = 0
    for d in devices:
        if d.name:    
            if "coolled" in d.name.lower():
                n_dev += 1
                print(f"Address: {d.address} | Name: {d.name}")
    if n_dev == 0:
        print("No CoolLED devices found.")

if __name__ == "__main__":
    asyncio.run(main())