# Home Assistant BLE ADV Ceiling Fan / Lamps
[![GitHub release](https://img.shields.io/github/v/release/NicoIIT/ha-ble-adv.svg)](https://github.com/NicoIIT/ha-ble-adv/releases/)

Home Assistant Custom Integration to control Ceiling Fan / Lamps using BLE Advertising.

Same as [ESPHome integration](https://github.com/NicoIIT/esphome-components) but directly in Home Assistant, using the Bluetooth stack of the host if possible.

## Features
* Discover your device configuration simply by listening to an already paired controller (Android Phone App, Physical Remote, ESPHome ble_adv_controller)
* Create Home Assistant Fan / Light Entities using existing Home Assistant UI to control them
* Listen to the command emitted by the Phone App and updates Home Assistant Entities state
* Synchronize another controller: allows to have a Phone App and a remote both updating Home Assistant entities state
* Guided configuration fully based on Home Assistant User Interface configuration flow
* Use either the bluetooth of the HomeAssistant host or an ESPHome based `ble_adv_proxy` similar to the ESPHome `bluetooth_proxy`

## Requirements
* Your Home Assistant must either:
  * be on a LINUX host, have a Bluetooth Adapter available and (even if not strictly necessary) discovered by the [Bluetooth Integration](https://www.home-assistant.io/integrations/bluetooth/). This integration communicates directly with the Host bluetooth adapters using HCI Sockets (cannot use the HA Bluetooth Adapters directly due to the need to use BLE Advertising in RAW mode), so your Home Assistant must have a direct authorized access to the Bluetooth adapter (run as root, direct network access - network mode 'host') which is the case for standard Home Assistant installations. For **advanced** users that defined their own HA docker container in a dedicated docker network behind nginx for example, a solution is available [here](https://github.com/NicoIIT/ha-ble-adv/wiki/Workaround-for-HA-non-'network_mode:-host'-or-non-root-installations).
  * have one or several ESPHome [ble_adv_proxy](https://github.com/NicoIIT/esphome-ble_adv_proxy) linked to your Home Assistant instance.
* Your device can be reached by Bluetooth from the Home Assistant Host or from the `ble_adv_proxy`.
* Have an up-to-date Home Assistant Core (2025.2.4 minimum) and HACS (2.0.1 minimum)

## Supported Ceiling Fans / Lamps Protocols
This integration **does not support any specific device type or brand**, but protocols used by the ANDROID apps controlling them. Protocols supported are the ones used by the following Apps:

* LampSmart Pro
* Lamp Smart Pro - Soft Lighting / Smart Lighting
* FanLamp Pro
* Zhi Jia
* Zhi Guang
* ApplianceSmart
* Vmax smart
* Zhi Mei Deng Kong
* Smart Light (BETA, No RGB, users wanted!) (Only the control by device, not the Master Control)
* Other (Legacy), removed app from play store: 'FanLamp', 'ControlSwitch'

## Installing the component
This component is an [HACS](https://www.hacs.xyz/) Custom Repository. With HACS installed, the repository installation procedure can be found [here](https://www.hacs.xyz/docs/faq/custom_repositories/), with parameters:
* **Repository**: "NicoIIT/ha-ble-adv"
* **Type**: "Integration"

Alternatively if you do not want to use HACS, you can simply clone this repository and copy the 'custom_components' directly at the root of your HA config (at the same place than your configuration.xml):
```
/ha_root:
  |-> custom_components
  |    |-> ble_adv
  |-> configuration.yaml
```

Once the repository is added, you need to restart Home Assistant so that it could be taken into account.
Still with this method you will not be warned when a new Release will be available.

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
* **Validation**: For each of the potential configurations discovered / entered, verify if the lamp is properly controlled by trying to make it blink
* **Definition**: Define the **Entities** to be created (Main Light, Second Light, Fan, ...) and their characteristics (RGB / Cold White Warm / Binary / Fan Speed / Min Brightness...), add a supplementary remote controller or modify the technical parameters. This step can be modified afterwards by reconfiguring the integration (see FAQ).
* **Finalization**: Specify the name of the Device and save your changes.


## Future Developments
Future developments are tracked in [github feature requests](https://github.com/NicoIIT/ha-ble-adv/issues?q=is%3Aissue%20state%3Aopen%20label%3Aenhancement), do not hesitate to vote for them if you need them giving it a :thumbsup:, or open new ones!

## FAQ

### The 'Duplicate config' flow detects some potential configurations but none of them manages to make the light blink
The fact configurations are detected means your controller(phone app or remote) is recognized and properly handled. Each of the codecs are designed (and validated) such as decoding / re-encoding is done in the exact same way so the commands that are emmitted by HA will be the exact same as the ones emmitted by the duplicated controller.

As a consequence this is probably a Bluetooth range issue: the bluetooth adapter is too far from the device to be controlled. Try to place it next to your device (less than 3 meters, in direct view) and retry.

If it does not solve the issue then open a Bug Report.

### Can I change the entity parameters / technical parameters / bluetooth adapter / supplementary remote controller after having finished the configuration?
Yes, you can use the HA 'Reconfigure' option:
* Find the 'Modifying the integration' in this [page](https://www.home-assistant.io/getting-started/integration/)
* Apply the same procedure (1) but click on 'Reconfigure' instead of 'Rename'
What you cannot change still is the dicovered config (codec, id, index) that identifies your device in a unique way and are used as key.

### When I perform changes very fast on the light or fan, sometimes the command is not taken into account
Some devices are not available to receive commands while they are still processing one. You can increase the 'Minimum Duration' in between 2 commands in the 'Technical' part of the configuration to be sure we will wait this delay before sending new commands to the Device.

### When I change the color of my Cold / Warm White light from COLD to WARM in HA, it results in the reversed action on the device
The issue is not understood, but there is an option to fix it: modify the entity parameters (see first question) and check the box "Reverse Cold / Warm"

### When I switch OFF my entity, the device fully resets its state to the default and is then not aligned with HA state when I switch it back ON (color, brightness, fan direction, ...)
You can force the re send of the HA state when the entity is switched ON: modify the entity parameters (see first question) and check the box "Force (...) refresh when switched ON".

Please note this will send several distinct commands very fast when the entity is switched ON: depending on your device it may be too fast, see second question.

Please also note some Fan does not support the re send of the same state for oscillation or direction (act as _toggle_) resulting in direction / oscillation changed on each 'switch ON' if those options are activated: this is the main reason why those options are not activated by default. If your Fan does not support it there is nothing I can do for you, simply do not use it.

### When I try to add an integration for the first time my ble_adv_proxy is not detected
Home assistant does not automatically loads components if they have no integration, and then the ble_adv_proxy cannot be detected by the unloaded component, so you have to force the component to be loaded at start by adding the line in the `configuration.yaml`:
```yaml
ble_adv:

```
Alternatively, the first time you start a config flow the component is loaded, so you just have to wait for up to 1 minute after that to have the `ble_adv_proxy` detected and available.

### Why should I choose / test different configs while the Phone Application does not need to do so but manages to make it work?
We could indeed broadcast ALL possible messages from all configs as what is done by Phone applications, but it is useless as only ONE effectively controls the device. The goal here is to be smarter than Phone apps and:
* avoid polluting the bluetooth network with hundreds of useless messages
* improve the response time by emitting immediately the message that will work instead of emitting 3 or 4 useless ones before

### I have several ble_adv_proxy / bluetooth adapters but I am forced to choose one and only one for my device, why I cannot use ALL?
First of all it is only a matter of choosing the best adapter at config time, so not a big deal. This is done for those reasons:
* Same as previous answer: we optimize a maximum the bluetooth network and we try to avoid polluting it with useless messages.
* The synchronization in between the Phone App / Physical remote and the HA State is done by listening to the messages emitted, so to keep them in sync we have to be sure those messages are listened by BOTH the bluetooth adapter and the device, and this is most ensured when only one bluetooth adapter is considered, and if possible when it is near the device (in the same room at least).
* The device may be reached by several commands coming from several adapters and may act in a stupid may, as for instance considering 2 ON commands coming from different places are in fact a first ON/OFF toggle followed by another ON/OFF toggle from another controller (and then accepted) and then resulting in ON then immediate OFF...

### But I am a __smart__ guy with a __smart__ setup and I NEED several adapters for an integration
First of all, this is a **BAD** idea, there is no point in doing so without drawbacks as highlighted in the previous questions. But if you think it is best for you, who am I to prevent you from doing it... You can select several adapters in the `Technical` part of the setup.

Still in this case:
* no help will be provided
* no `Bug Report` will be accepted
* no `Feature request` such as 'I am still forced to select one adapter at config time, please let me select more' will be accepted

### When I perform a change on HA, it is not taken into account the phone app
Well the main issue here is that those devices are never sending anything to any controller: they are just listening to commands. The consequence is that each individual controller is controlling the device in a standalone way (the remote does not update the Phone App state for instance, nor HA does).

Still, this HA integration is able to listen to commands sent from the Phone App, or from the Remote if it is linked, and update its state accordingly.