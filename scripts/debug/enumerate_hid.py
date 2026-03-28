"""Enumerate all Logitech HID devices to discover receiver PID and interface info."""
import hid

devs = hid.enumerate(0x046d)
print(f"Found {len(devs)} Logitech HID devices\n")
for d in devs:
    print(
        f"PID=0x{d['product_id']:04x}  "
        f"usage_page=0x{d['usage_page']:04x}  "
        f"usage=0x{d['usage']:04x}  "
        f"iface={d['interface_number']}  "
        f"product=\"{d['product_string']}\"  "
    )
