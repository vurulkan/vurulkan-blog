---
title: "Lenovo ThinkPad E490 (20N8) Hackintosh (macOS Monterey + OpenCore 1.0.4)"
date: 2025-11-29 21:00:00 +0300
last_modified_at: 2026-11-09 17:30:00 +0300
description: "OpenCore 1.0.4 notes for a Lenovo ThinkPad E490 running macOS Monterey, including hardware details, working features and important NVRAM limitations."
categories: [MacOS, Hackintosh]
tags: [lenovo, macos, hackintosh, opencore]
toc: true
published: true
robots: index, follow
---

> **Disclaimer**  
> I am **not responsible** for any damage, data loss, or malfunction that may occur on your device.  
> If you do not fully understand the process, **please do not proceed**.  
> Use at your own risk.  
>
> **Important:** On this specific Lenovo E490 model (maybe other ThinkPad models too), performing an **NVRAM reset** may cause the system to fail to boot permanently, potentially requiring motherboard repair or replacement.  
> **Avoid NVRAM reset** unless you fully understand the consequences.

**macOS Version:** Monterey (12.x)  
**OpenCore Version:** 1.0.4  
**Model:** Lenovo ThinkPad E490 (Type: 20N8)  
**Status:** Daily-driver configuration with the limitations listed below

[Show project on GitHub](https://github.com/vurulkan/Lenovo-Thinkpad-E490-20N8-Hackintosh){:target="_blank"}

---

## 📦 Device Specifications

| Component      | Details |
|----------------|---------|
| **Model**      | Lenovo ThinkPad E490 (Type: 20N8) |
| **CPU**        | Intel Core i7-8565U (Whiskey Lake, 4C/8T, 1.8GHz Base / 4.6GHz Turbo) |
| **iGPU**       | Intel UHD Graphics 620 (1536MB VRAM) |
| **dGPU**       | AMD Radeon RX 550X |
| **RAM**        | 16GB DDR4 2400MHz |
| **Storage**    | 512GB NVMe SSD + 1TB SATA HDD |
| **Display**    | 14" FHD (1920x1080) IPS |
| **Wi-Fi / BT** | Intel Wireless-AC 9260 |
| **Audio**      | Realtek ALC257 |
| **Touchpad**   | Synaptics TrackPad + TrackPoint |
| **Camera**     | Integrated 720p Camera |
| **Keyboard**   | Backlit ThinkPad Keyboard |

---

## 🛠️ Kexts Used

| Kext Name                              | Version                  | Purpose |
|----------------------------------------|--------------------------|---------|
| AirportItlwm                           | 2.3.0 (For Monterey)     | Intel Wi-Fi |
| AppleALC                               | 1.9.5                    | Audio support |
| BlueToolFixup                          | 2.7.1                    | Bluetooth fix for Monterey+ |
| BrightnessKeys                         | 1.0.3                    | Brightness control keys |
| CPUFriend                              | 1.3.0                    | CPU power management |
| CPUFriendDataProvider (BalancedQuiet)  | 1.0                      | Custom CPU power profile (Balanced + Quiet) |
| ECEnabler                              | 1.0.6                    | Embedded controller fix |
| IntelBluetoothFirmware                 | 2.4.0                    | Intel Bluetooth |
| IntelBTPatcher                         | 2.4.0                    | Bluetooth patching |
| Lilu                                   | 1.7.1                    | Core patching framework |
| NoTouchID                              | 1.0.3                    | Disable Touch ID check |
| NVMeFix                                | 1.1.3                    | NVMe SSD optimizations |
| SMCBatteryManager                      | 1.3.7                    | Battery status |
| SMCProcessor                           | 1.3.7                    | CPU sensors |
| SMCSuperIO                             | 1.3.7                    | Fan & temperature sensors |
| VirtualSMC                             | 1.3.7                    | SMC emulator |
| VoodooPS2Controller                    | 2.3.7                    | Keyboard, TrackPad, TrackPoint |
| VoodooInput                            | 1.1.6                    | Input support |
| VoodooPS2Keyboard                      | 2.3.7                    | PS/2 keyboard |
| VoodooPS2Mouse                         | 2.3.7                    | PS/2 mouse |
| VoodooPS2Trackpad                      | 2.3.7                    | PS/2 trackpad |
| WhateverGreen                          | 1.7.0                    | GPU support / patching |
| RealtekRTL8111                         | 2.5.0                    | Ethernet driver |
| UTBMap                                 | 1.1                      | Custom USB port map |
| USBToolBox                             | 1.1.1                    | USB mapping utility |

---

## ✅ What Works

- Intel UHD 620 Graphics (full acceleration)
- Audio (internal speakers, microphone, headphone jack)
- Brightness control (Fn keys)
- Wi-Fi (AirportItlwm)
- Bluetooth (IntelBluetoothFirmware + BlueToolFixup)
- Keyboard (including Fn keys)
- TrackPad & TrackPoint
- Sleep/Wake
- Battery status
- USB ports (mapped)
- Ethernet (RealtekRTL8111)
- Integrated Camera
- CPU power management (with CPUFriend profiles)

---

## ⚠️ Known Issues

- **Balanced+Quiet CPUFriend profile** — slightly reduces performance for quieter operation.
- **AMD Radeon RX 550X** disabled for compatibility reasons.  
- **Windows shutdown/restart issue** — If Windows fails to fully shutdown or restart when dual-booting, **disable Fast Startup** in Windows:  
  1. Open **Control Panel → Hardware and Sound → Power Options**  
  2. Click **Choose what the power buttons do**  
  3. Click **Change settings that are currently unavailable**  
  4. Under **Shutdown settings**, uncheck **Turn on fast startup (recommended)**  
  5. Click **Save changes** and reboot

---

## 📄 SSDTs

All SSDTs were custom-extracted and compiled for this device:

- **SSDT-EC.aml** – Adds Embedded Controller  
- **SSDT-RTCAWAC.aml** – Fix system clock/timers (RTC/AWAC patch)  
- **SSDT-USBX.aml** – USB power properties  
- **SSDT-PLUG.aml** – CPU power management  
- **SSDT-PNLF.aml** – Backlight control  

---

## ⚙️ CPUFriendDataProvider Profiles

Two variants are included in `/OC/Kexts`:

1. **`CPUFriendDataProvider.kext.stock`** – Stock macOS power management  
2. **`CPUFriendDataProvider.kext.balanced`** – Slightly reduced turbo boost for quieter fan and lower temps  

**Switching:**
- In `/OC/Kexts`, **rename** the desired profile by removing `.stock` or `.balanced` from the end, so it becomes `CPUFriendDataProvider.kext`
- Delete the other unused profile  

---

## 🚀 Installation Instructions

1. Clone this repo OR download latest release from releases
2. Copy EFI to your USB’s EFI partition
3. Use GenSMBIOS:
```bash
1 (Select config.plist)
3 (Type: MacBookPro15,4)
```
4. Replace SMBIOS info in config.plist with generated values
5. Boot from USB and test before installing to internal disk

## 📝 Notes

    Tested with macOS Monterey 12.x

    Built with OpenCore 1.0.4

    All SSDTs extracted & patched manually

    Wi-Fi & Bluetooth use Intel kexts — already included

    Balanced+Quiet profile recommended for daily use


## Related hardware notes

The [HP ZBook Fury 15 G7 guide](/posts/hp-zbook-fury-15-g7-hackintosh/) documents a separate OpenCore configuration and its limitations. Use the EFI and device notes for the exact machine; a working configuration on one model does not establish compatibility with another.
