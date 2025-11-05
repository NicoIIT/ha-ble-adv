# <img width="64" height="64" alt="icon@2x" src="https://github.com/user-attachments/assets/29025370-fa25-41a1-ad18-5ca567dbf120" />  Home Assistant BLE ADV Ceiling Fan / Lamps

[![GitHub release](https://img.shields.io/github/v/release/NicoIIT/ha-ble-adv.svg)](https://github.com/NicoIIT/ha-ble-adv/releases/)
![Usage](https://img.shields.io/badge/dynamic/json?color=9932CC&logo=home-assistant&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.ble_adv.total)

Home Assistant Custom Integration to control Ceiling Fan / Lamp Devices from various Brands using **_BLE Raw Advertising_** as communication method.

This integration **is not limited to any specific device type or brand**: it is able to recognize and reproduce the communication protocols used by various [Phone Apps](#supported-ceiling-fans--lamps-protocols) and Remotes.

## Features
* Discover your device configuration simply by listening to an already paired controller (Android Phone App, Physical Remote, ESPHome ble_adv_controller)
* Create Home Assistant Fan / Light Entities using existing Home Assistant UI to control them
* Listen to the command emitted by the Phone App and updates Home Assistant Entities state
* Synchronize another controller: allows to have a Phone App and a remote both updating Home Assistant entities state
* Guided configuration fully based on Home Assistant User Interface configuration flow
* Use either the bluetooth of the HomeAssistant host or an ESPHome based [ble_adv_proxy](https://github.com/NicoIIT/esphome-ble_adv_proxy) similar to the ESPHome `bluetooth_proxy` but supporting _BLE Raw Advertising_

## Requirements
* Your Home Assistant must _either_:
  * Be on a LINUX host, on a Standard HA Install (HAOS) and have a Bluetooth Adapter directly accessible on the Host (internal or via USB and not using a VM layer) and (even if not strictly necessary) discovered by the [Bluetooth Integration](https://www.home-assistant.io/integrations/bluetooth/). For **advanced** users that defined their own HA docker container (non root or non 'host' network), a solution is available [here](https://github.com/NicoIIT/ha-ble-adv/wiki/Workaround-for-HA-non-'network_mode:-host'-or-non-root-installations).
  * Have one or several ESPHome [ble_adv_proxy](https://github.com/NicoIIT/esphome-ble_adv_proxy) linked to your Home Assistant instance. If you already have some [bluetooth_proxy](https://esphome.io/components/bluetooth_proxy/) they can easily be extended to `ble_adv_proxy`.
* Your device can be reached by Bluetooth from the Home Assistant Host or from the `ble_adv_proxy`.
* Have an up-to-date Home Assistant Core (2025.2.4 minimum) and HACS (2.0.1 minimum)

## Supported Ceiling Fans / Lamps Protocols
The Protocols supported are the ones used by the following Android Phone Apps (and iOS for most of them):

* [LampSmart Pro](https://play.google.com/store/apps/details?id=com.jingyuan.lamp)
* [FanLamp Pro](https://play.google.com/store/apps/details?id=com.jingyuan.fan_lamp)
* [ApplianceSmart](https://play.google.com/store/apps/details?id=com.jingyuan.smart_home)
* [Vmax smart](https://play.google.com/store/apps/details?id=com.jingyuan.vmax_smart)
* [Zhi Jia](https://play.google.com/store/apps/details?id=com.cxw.cxwblelight)
* [Zhi Guang](https://play.google.com/store/apps/details?id=com.cxw.zhiguang)
* [Zhi Mei Deng Kong](http://mihuan.iotworkshop.com/zhiguang/) (not available on Play Store)
* [Mantra Lighting](https://play.google.com/store/apps/details?id=com.newenergy.baolilan)
* [Smart Light / Argrace Smart](https://apkpure.com/argrace-smart/ai.argrace.oem) (No RGB, Only the control by device, not the Master Control) (not available on Play Store anymore, seems abandoned)
* [LE Light Pro / 乐智光Pro](https://openapi.lelight.top/dl/cqan) (not available on Play Store)
* [RuiXin](https://rx-etech.com/rxzn.html) Sanweyter devices (No RGB, no Timer, Remote Temperature Switch not reflected in HA) (not available on Play Store)
* [RW.LIGHT](https://play.google.com/store/apps/details?id=com.rw.rwblelight) (No control by Group, No support for AURA / IR / FIBER types)
* [Smart Elfin](https://play.google.com/store/apps/details?id=com.warpfuture.wfiot.g)
* Other (Legacy), removed app from play store: 'FanLamp', 'ControlSwitch', 'Lamp Smart Pro - Soft Lighting / Smart Lighting'

If the protocols of your application are not supported yet you can request for their support [here](https://github.com/NicoIIT/ha-ble-adv/issues/new?template=new_app.yml).

## Supported Physical Remote
There are lots of different Physical Remote so it is impossible to know if a Physical Remote is supported without testing it. Some of them are using the same protocols than the Phone Apps, others are using their own protocol, or even RF or IR...

If your remote is not recognized by the integration then you can check if it could be supported and request for its support, see [How To](https://github.com/NicoIIT/ha-ble-adv/wiki/How-to-know-if-my-Physical-Remote-is-using-BLE-Advertising-to-control-my-device).

## Installing the component
Download and install directly through [HACS (Home Assistant Community Store)](https://www.hacs.xyz/) following the [my-link](https://my.home-assistant.io/) link:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=NicoIIT&repository=ha-ble-adv)

Alternatively if you do not want to use HACS, you can simply clone this repository and copy the 'custom_components' directly at the root of your HA config (at the same place than your configuration.yaml):
```
/ha_root:
  |-> custom_components
  |    |-> ble_adv
  |-> configuration.yaml
```
Still with this method you will not be warned when a new Release will be available.

In any case, once the repository is added, you need to restart Home Assistant so that it could be taken into account.

## Adding Integrations
Once the component is installed, you can now [add](https://www.home-assistant.io/getting-started/integration/) a **"BLE ADV Ceiling Fan / Lamps"** integration for each of the Devices you want to control.

The configuration flow will listen to the commands emitted by your phone / physical remote and/or try to control your device (make the lamp blink) so you have to be **located in the same room than the device** in order to be sure:
* a bluetooth adapter is able to listen to the commands from where they will be used.
* the same bluetooth adapter is able to control your device
* you can check if the lamp blinked

The main steps of the configuration flow are the following:
* **Configuration discovery**, with 3 ways to proceed:
  * **The recommended way - Duplicate Config**: Press on a button on your Phone App (OR Physical Remote OR HA Entity from ESPHome controller) already paired and controlling your device, the configuration process will automatically detect the potential configurations.
  * **The expert way - Manual Input**: directly specifies the configuration parameters (codec / forced_id / index) if already known from a previous install or ESPHome config
  * **Pairing**: the last chance if you do not have an already paired controlling device, the process will try to pair with your device
* **Validation**: Find the first of the potential configurations discovered / entered that can control the lamp by trying to make it blink
* **Definition**: Define the **Entities** to be created (Main Light, Second Light, Fan, ...) and their characteristics (RGB / Cold White Warm / Binary / Fan Speed / Min Brightness...), add a supplementary remote controller or modify the technical parameters. This step can be modified afterwards by reconfiguring the integration (see [Wiki](https://github.com/NicoIIT/ha-ble-adv/wiki/Configuration-Guide)).
* **Finalization**: Specify the name of the Device and save your changes.


## Future Developments
Future developments are tracked in [github feature requests](https://github.com/NicoIIT/ha-ble-adv/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement), do not hesitate to vote for them if you need them giving it a :thumbsup:, or open new ones!

## More Info on Wiki
* [Configuration Guide](https://github.com/NicoIIT/ha-ble-adv/wiki/Configuration-Guide)
* [Troubleshooting Guide](https://github.com/NicoIIT/ha-ble-adv/wiki/Troubleshooting-Guide)


