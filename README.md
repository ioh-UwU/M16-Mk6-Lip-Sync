# Protogen Visor Lipsync

Based on [coolledux-linux-uploader](https://github.com/zackmcmurrin-dev/coolledux-linux-uploader?tab=MIT-1-ov-file) by zackmcmurrin-dev.<br>
Driver software to allow real-time animation from pre-made frames on CoolLEDUX devices.<br>
Originally designed for M16 Studios' Mk6 visor, which uses a flexible 64x16 CoolLEDUX display.<br>
The program uses an I2S microphone input into a Raspberry Pi Pico 2W to send idle/speech viseme animation frames to the visor. I have not tested it on a Pico (1) W, but you do need a Pico (or other microcontroller) with BLE support.<br>
This code can be modified for other CoolLEDUX devices, and more complex animations are also possible, but those go beyond the purpose of this implementation.

# Requirements

Helper files - Python 3.13 (other versions may work, not tested)
- bleak (Bluetooth discovery)
- pillow (image data processing)

Driver - MicroPython 
- aioble (Bluetooth communication)

# Instructions

## Setup
1. `git clone` this repository
2. [Download Thonny](https://thonny.org/) *(Easiest to interact with the Pi Pico, other IDEs also work, but these instructions will use Thonny)*
3. `Tools` > `Manage Packages` > Search for and install `bleak` and `pillow`
4. Connect your Pi Pico to your computer in BOOTSEL mode. *(hold the BOOTSEL button, plug it in, release the BOOTSEL button)*
5. `Run` > `Configure interpreter`. In the bottom right, click `Install or update MicroPython`
6. `Target volume` should populate automatically. Set `MicroPython family` to `RP2` and `variant` to `Raspberry Pi • Pico 2 W`
7. Click `Install`, wait for the program to finish. Close the `Options` window

# Software

## 1. Find your display's MAC address.
If you do not already know your visor's MAC address, power on the CoolLEDUX display and run `device_scanner.py`.<br>
You should see an output similar to `Address: 01:02:03:04:05:06 | Name: CoolLEDUX`. Paste the MAC address into `MAC_ADDR` for `main.py`. *(~line 19)*

## 2. Create and process your animation frames
Included is an example set of animation frames, which are already loaded in `main.py`. To create your own, choose your favorite digital drawing software (I really like Krita) and either open one of the examples or create a new canvas 64 pixels wide and 16 pixels tall. Create a frame for each of the speech visemes `("Viseme_PP", "Viseme_FF", "Viseme_TH", "Viseme_SS", "Viseme_A", "Viseme_E", "Viseme_I", "Viseme_O", "Viseme_U")` and save them as their respective `[viseme].png` inside the `visemes` folder. Blinking and regular idle (silent) animation sequences can be any length, but must be named sequentially as `SIL_#` and `BL_#` inside `visemes/SIL`, starting at 0. (See example for clarification.)<br>
Once all your frames are set inside the `visemes` directory, run `frame_preprocessor.py`. This should generate a file called `frame_data.txt` which contains the __frame data code__ to be pasted into `main.py` *(section starting at ~line 30)* If you do not wish to have blinking animations, set `BLINK_ENABLED` in `main.py` to `False`. <br>
__*For advanced users:*__ you may wish to add, remove, and otherwise customize the visemes, their prefixes, and audio processing thresholds. The viseme names are only used inside of the `VoiceReactiveController` class in `main.py`. Speech visemes and audio thresholds are set in the `_get_current_viseme` function. The minimum and maximum volume limits for speech may be modified with the class's `self.MIN_VOLUME` and `self.MAX_VOLUME`. When modifying these values, please ensure `DEBUG` is set to `True` to print out the raw volume data.

## 3. Upload main.py
Ensure your Pi Pico is connected normally *(Not in BOOTSEL)* and Thonny's interpreter in the bottom right is set to `MicroPython (Raspberry Pi Pico)`. You should see your board connected to the right of the interpreter. There should be no errors in the Shell at the bottom. If not, click `Stop/Restart Backend` *(stop sign)* at the top. If this still doesn't work, restart your computer. <br>
To upload `main.py`, right-click it in your local files and select `Upload to /`. Wait for the program to finish. If you do not see the Pi Pico's files, select `View` > `Files`. You should see `main.py`

# Hardware

## 1. Preparations
Remove one of the black circular gaskets from the mask, then remove the rubber part. This is where you will mount the Pi and the microphone. In addition to the Pi Pico 2W and the I2S microphone chip, you will need a USB-C splitter (1F -> 2M) and a USB-C Female to MicroUSB Male adapter for the Pico. The splitter will deliver power from the regulator to the USB power for the visor's flexible panel and the Pico.<br>
In addition to a soldering iron and wire, you will also need either small screws or glue to fix the pico and microphone to the plastic gasket. You will also need some way to fill the hole in the gasket once everything is attached, so the visor does not fog up from breathing and talking. *(I recommend hot glue)*

## 2. Soldering
The Microphone should be connected to the Pico on the pins shown in the circuit diagram below. Connect all wires to one of the devices first, then pass them through one hole in the middle of the plastic gasket. Solder them to the corresponding pins on the other device. Before continuing the installation, verify that the connections are correct and everything is working by either turning on the visor and powering on the Pico, or by running the code while the Pico is connected to your PC with `DEBUG` set to `True`. Tapping the microphone port should be enough to verify that audio is being received and processed.<br>
<img src="/documentation_resources/circuit_diagram.png" height=250>
<img src="/documentation_resources/wire_routing.jpg" height=250>

## 3. Installation
Fix the microphone to one side of the gasket, and the Pico to the other. *(see images for example)* You may wish to zip-tie wires to prevent them from breaking loose from the solder *(if using stranded wire)*<br>
<img src="/documentation_resources/construction_mic.jpg" width=200>
<img src="/documentation_resources/construction_pi.jpg" width=200><br>
Once these are in place, fill the remaining gaps with hot glue or your preferred method. Be sure not to block the microphone port. Put the finished module back into the hole in the mask, with the microphone near the bottom.<br>
<img src="/documentation_resources/installed.jpg" width=200><br>

## If lipsync does not look right
Please ensure the microphone is in a good location. You may need to modify the `MIN_VOLUME` and `MAX_VOLUME` thresholds in `main.py` to work better with your specific voice.
