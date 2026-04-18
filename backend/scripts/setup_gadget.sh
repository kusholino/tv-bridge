#!/bin/bash
#
# TV-Bridge USB HID Gadget Setup Script
# 
# Konfiguriert Raspberry Pi Zero 2 W als Composite USB-HID-Gerät
# mit Mouse und Keyboard Interface.
#
# Muss als root ausgeführt werden.
# Wird automatisch von systemd beim Boot ausgeführt.

set -e

GADGET_NAME="tvbridge"
GADGET_DIR="/sys/kernel/config/usb_gadget/${GADGET_NAME}"

# USB IDs (Generic USB Device)
VENDOR_ID="0x1d6b"   # Linux Foundation
PRODUCT_ID="0x0104"  # Multifunction Composite Gadget
BCD_DEVICE="0x0100"  # v1.0.0
BCD_USB="0x0200"     # USB 2.0

# Device Descriptors
MANUFACTURER="TV-Bridge Project"
PRODUCT="TV Remote HID"
SERIAL="$(grep Serial /proc/cpuinfo | cut -d ' ' -f 2 | tail -c 9)"

# USB Konfiguration
CONFIG_NAME="c.1"
MAX_POWER=250  # mA

echo "[TV-Bridge Gadget] Starting USB HID Gadget setup..."

# 1. ConfigFS mounten (falls nicht bereits gemountet)
if ! mountpoint -q /sys/kernel/config; then
    echo "[Gadget] Mounting configfs..."
    mount -t configfs none /sys/kernel/config
fi

# 2. libcomposite-Modul laden
if ! lsmod | grep -q libcomposite; then
    echo "[Gadget] Loading libcomposite module..."
    modprobe libcomposite
fi

# 3. Altes Gadget entfernen falls vorhanden
if [ -d "${GADGET_DIR}" ]; then
    echo "[Gadget] Removing existing gadget..."
    
    # UDC unbinden falls gebunden
    if [ -f "${GADGET_DIR}/UDC" ]; then
        echo "" > "${GADGET_DIR}/UDC" 2>/dev/null || true
    fi
    
    # Warten bis unbind abgeschlossen
    sleep 0.5
    
    # Symlinks entfernen
    rm -f "${GADGET_DIR}/configs/${CONFIG_NAME}/hid.mouse" 2>/dev/null || true
    rm -f "${GADGET_DIR}/configs/${CONFIG_NAME}/hid.keyboard" 2>/dev/null || true
    
    # Functions entfernen
    rmdir "${GADGET_DIR}/functions/hid.mouse" 2>/dev/null || true
    rmdir "${GADGET_DIR}/functions/hid.keyboard" 2>/dev/null || true
    
    # Strings entfernen
    rmdir "${GADGET_DIR}/configs/${CONFIG_NAME}/strings/0x409" 2>/dev/null || true
    rmdir "${GADGET_DIR}/configs/${CONFIG_NAME}" 2>/dev/null || true
    rmdir "${GADGET_DIR}/strings/0x409" 2>/dev/null || true
    
    # Gadget entfernen
    rmdir "${GADGET_DIR}" 2>/dev/null || true
fi

# 4. Neues Gadget erstellen
echo "[Gadget] Creating gadget directory..."
mkdir -p "${GADGET_DIR}"
cd "${GADGET_DIR}"

# 5. USB Device Descriptor setzen
echo "[Gadget] Setting device descriptors..."
echo "${VENDOR_ID}" > idVendor
echo "${PRODUCT_ID}" > idProduct
echo "${BCD_DEVICE}" > bcdDevice
echo "${BCD_USB}" > bcdUSB

# Device Class (siehe USB spec)
echo "0x00" > bDeviceClass
echo "0x00" > bDeviceSubClass
echo "0x00" > bDeviceProtocol

# 6. Strings (Englisch)
echo "[Gadget] Setting device strings..."
mkdir -p strings/0x409
echo "${MANUFACTURER}" > strings/0x409/manufacturer
echo "${PRODUCT}" > strings/0x409/product
echo "${SERIAL}" > strings/0x409/serialnumber

# 7. Configuration erstellen
echo "[Gadget] Creating configuration..."
mkdir -p "configs/${CONFIG_NAME}"
echo "${MAX_POWER}" > "configs/${CONFIG_NAME}/MaxPower"

mkdir -p "configs/${CONFIG_NAME}/strings/0x409"
echo "HID Mouse + Keyboard" > "configs/${CONFIG_NAME}/strings/0x409/configuration"

# 8. HID Mouse Function erstellen
echo "[Gadget] Creating HID Mouse function..."
mkdir -p functions/hid.mouse

# HID Parameters
echo 1 > functions/hid.mouse/protocol    # 1 = Mouse
echo 1 > functions/hid.mouse/subclass    # 1 = Boot Interface
echo 3 > functions/hid.mouse/report_length  # 3 Bytes

# Mouse HID Report Descriptor
# Boot Protocol Mouse (3-Byte: Buttons, X-Delta, Y-Delta)
cat > functions/hid.mouse/report_desc << 'EOF_MOUSE'
0x05, 0x01,        // Usage Page (Generic Desktop)
0x09, 0x02,        // Usage (Mouse)
0xA1, 0x01,        // Collection (Application)
0x09, 0x01,        //   Usage (Pointer)
0xA1, 0x00,        //   Collection (Physical)
0x05, 0x09,        //     Usage Page (Button)
0x19, 0x01,        //     Usage Minimum (Button 1)
0x29, 0x03,        //     Usage Maximum (Button 3)
0x15, 0x00,        //     Logical Minimum (0)
0x25, 0x01,        //     Logical Maximum (1)
0x95, 0x03,        //     Report Count (3)
0x75, 0x01,        //     Report Size (1)
0x81, 0x02,        //     Input (Data, Variable, Absolute)
0x95, 0x01,        //     Report Count (1)
0x75, 0x05,        //     Report Size (5)
0x81, 0x01,        //     Input (Constant) - Padding
0x05, 0x01,        //     Usage Page (Generic Desktop)
0x09, 0x30,        //     Usage (X)
0x09, 0x31,        //     Usage (Y)
0x15, 0x81,        //     Logical Minimum (-127)
0x25, 0x7F,        //     Logical Maximum (127)
0x75, 0x08,        //     Report Size (8)
0x95, 0x02,        //     Report Count (2)
0x81, 0x06,        //     Input (Data, Variable, Relative)
0xC0,              //   End Collection
0xC0               // End Collection
EOF_MOUSE

# 9. HID Keyboard Function erstellen
echo "[Gadget] Creating HID Keyboard function..."
mkdir -p functions/hid.keyboard

echo 1 > functions/hid.keyboard/protocol    # 1 = Keyboard
echo 1 > functions/hid.keyboard/subclass    # 1 = Boot Interface
echo 8 > functions/hid.keyboard/report_length  # 8 Bytes

# Keyboard HID Report Descriptor
# Boot Protocol Keyboard (8-Byte: Modifier, Reserved, Key1-6)
cat > functions/hid.keyboard/report_desc << 'EOF_KEYBOARD'
0x05, 0x01,        // Usage Page (Generic Desktop)
0x09, 0x06,        // Usage (Keyboard)
0xA1, 0x01,        // Collection (Application)
0x05, 0x07,        //   Usage Page (Key Codes)
0x19, 0xE0,        //   Usage Minimum (Left Control)
0x29, 0xE7,        //   Usage Maximum (Right GUI)
0x15, 0x00,        //   Logical Minimum (0)
0x25, 0x01,        //   Logical Maximum (1)
0x75, 0x01,        //   Report Size (1)
0x95, 0x08,        //   Report Count (8)
0x81, 0x02,        //   Input (Data, Variable, Absolute) - Modifier byte
0x95, 0x01,        //   Report Count (1)
0x75, 0x08,        //   Report Size (8)
0x81, 0x01,        //   Input (Constant) - Reserved byte
0x95, 0x06,        //   Report Count (6)
0x75, 0x08,        //   Report Size (8)
0x15, 0x00,        //   Logical Minimum (0)
0x25, 0x65,        //   Logical Maximum (101)
0x05, 0x07,        //   Usage Page (Key Codes)
0x19, 0x00,        //   Usage Minimum (0)
0x29, 0x65,        //   Usage Maximum (101)
0x81, 0x00,        //   Input (Data, Array) - Key array
0xC0               // End Collection
EOF_KEYBOARD

# 10. Functions zur Configuration linken
echo "[Gadget] Linking functions to configuration..."
ln -s functions/hid.mouse "configs/${CONFIG_NAME}/hid.mouse"
ln -s functions/hid.keyboard "configs/${CONFIG_NAME}/hid.keyboard"

# 11. Gadget aktivieren
echo "[Gadget] Activating gadget..."

# UDC (USB Device Controller) finden
UDC_DEVICE=$(ls /sys/class/udc | head -n 1)

if [ -z "${UDC_DEVICE}" ]; then
    echo "[Gadget] ERROR: No UDC device found!"
    echo "[Gadget] Check if dwc2 module is loaded and OTG is enabled in config.txt"
    exit 1
fi

echo "[Gadget] Using UDC: ${UDC_DEVICE}"
echo "${UDC_DEVICE}" > UDC

# 12. Warten bis HID-Devices verfügbar sind
echo "[Gadget] Waiting for HID devices..."
for i in {1..10}; do
    if [ -e "/dev/hidg0" ] && [ -e "/dev/hidg1" ]; then
        break
    fi
    sleep 0.5
done

# 13. Berechtigungen setzen
if [ -e "/dev/hidg0" ] && [ -e "/dev/hidg1" ]; then
    echo "[Gadget] Setting permissions on HID devices..."
    chmod 666 /dev/hidg0  # Mouse
    chmod 666 /dev/hidg1  # Keyboard
    
    echo "[Gadget] SUCCESS: USB HID Gadget configured!"
    echo "[Gadget]   - Mouse: /dev/hidg0"
    echo "[Gadget]   - Keyboard: /dev/hidg1"
    echo "[Gadget]   - UDC: ${UDC_DEVICE}"
else
    echo "[Gadget] ERROR: HID devices not created!"
    echo "[Gadget] Expected /dev/hidg0 and /dev/hidg1"
    exit 1
fi

exit 0
