from __future__ import annotations
import argparse
import time
from .discovery import DiscoveryAdvertisement

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Advertise the Projected AI desktop receiver on the local network')
    parser.add_argument('--name', default='Projected AI Desktop')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    advertisement = DiscoveryAdvertisement(port=args.port, name=args.name)
    advertisement.start()
    print(f'Advertising {args.name} on _projected-ai._tcp at port {args.port}. Press Ctrl+C to stop.')
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: return 0
    finally: advertisement.stop()

if __name__ == '__main__': raise SystemExit(main())
