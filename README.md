# Home Assistant BLE ADV Ceiling Fan / Lamps

Home Assistant Custom Integration to control Ceiling Fan / Lamps using BLE Advertising.

Same as [ESPHome integration](https://github.com/NicoIIT/esphome-components) but directly in Home Assistant, using the Bluetooth stack of the host if possible.

## Requirements
* Your Home Assistant must be on a LINUX host, have a Bluetooth Adapter available and, even if not strictly necessary, discovered by the [Bluetooth Integration](https://www.home-assistant.io/integrations/bluetooth/)
* Your device can be reached by Bluetooth from the Home Assistant Host. ESPHome bluetooth proxies cannot be used (for now).
* Have an up-to-date Home Assistant Core (2025.2.4 minimum) and HACS (2.0.1 minimum)
* This integration communicates directly with the bluetooth adapters using HCI Sockets (cannot use the HA Bluetooth Adapters directly due to the need to use BLE Advertising in RAW mode), so your Home Assistant must have a direct authorized access to the Bluetooth adapter (run as root, direct network access - network mode 'host') for now.

## Supported Ceiling Fans / Lamps
This integration does not support any specific device brand, but protocols used by the ANDROID apps controlling them. Protocols supported are the ones used by the following ANDROID Apps:

* LampSmart Pro
* Lamp Smart Pro - Soft Lighting / Smart Lighting
* FanLamp Pro
* ApplianceSmart
* Vmax smart
* Other (Legacy), removed app from play store: 'FanLamp', 'ControlSwitch'

## Installing the component
This component is an [HACS](https://www.hacs.xyz/) Custom Repository. With HACS installed, the repository installation procedure can be found [here](https://www.hacs.xyz/docs/faq/custom_repositories/), with parameters:
* **Repository**: "NicoIIT/ha-ble-adv"
* **Type**: "Integration"

Once the repository is added, you need to restart Home Assistant so that it could be taken into account.

## Adding Integrations
Once the component is installed, you can now [add](https://www.home-assistant.io/getting-started/integration/) a **"BLE ADV Ceiling Fan / Lamps"** integration for each of the Devices you want to control.

The main steps of the configuration flow are the following:
* **Configuration discovery**, with 3 ways to proceed:
  * **The recommended way - Duplicate Config**: Press on a button on your Phone App (OR Physical Remote OR HA Entity from ESPHome controller) already paired and controlling your device, the configuration process will automatically detect the potential configurations.
  * **The expert way - Manual Input**: directly specifies the configuration parameters (codec / forced_id / index) if already known them from a previous install or ESPHome config
  * **Pairing**: the last chance if you do not have an already paired controlling device, the process will try to pair with your device
* **Validation**: For each of the potential configurations discovered / entered, verify if the lamp is properly controlled by trying to make it blink
* **Finalization**: Specify the name of the Device and the **Entities** to be created (Main Light, Second Light, Fan, ...) and their characteristics (RGB / Cold White Warm / Binary / Fan Speed / Min Brightness...). This last step (and only this step) can be modified afterwards by reconfiguring the integration, similar to the "Modifying the integration" steps described [here](https://www.home-assistant.io/getting-started/integration/) but by selecting the "Reconfigure" instead of "Rename".


## Future Developments
Those changes are on going, no need to open a feature request for that.

### Supplementary apps to be supported
* Zhi Jia
* Zhi Guang
* ZhiMeiDengKong
* Smart Light (Only the control by device, not the Master Control)

### Support for "Reversed" Option
Support the reversing of Cold / White colors in CWW Lamps.
Well in fact understanding this option first as it is not clear AT ALL why this is needed, there must be a gap in our understanding of the protocols...

### Support for Supplementary controlling devices
Support to link an additional controlling device such as a Physical Remote.

### Support Device specific features as a Service
Features such as Pair / Unpair / Timer are not handled by the standard HA Entities and have to be defined as services.

### BLE ADV Adapters
* Docker Proxy (or even Host Proxy), in case your Home Assistant does not have a direct access to the HCI Bluetooth Adapter (not in network mode 'host', or not 'root'). The idea is to have another docker container with root access / network mode 'host' that will communicate with the HA Container using a Unix Socket shared on a docker volume. This would be a kind of 'low cost dbus'.
* ESPHome BLE ADV Proxy, as done by standard ESPHome bluetooth proxy, if your HA is far from the device

## FAQ

### When I perform changes very fast on the light or fan, sometimes the command is not taken into account
Some devices are not available to receive commands while they are still processing one. You can increase the 'Minimum Duration' in between 2 commands in the 'Technical' part of the configuration to be sure we will wait this delay before sending new commands to the Device.

### When I change the Oscillation or Direction of the Fan when it is OFF, nothing happens despite the change is taken into account in the UI
Those settings cannot be changed while the Fan is OFF, and they are not changed on the HA Entity side. Still there is a UI bug: the change should be reverted by the UI immediately to reflect the effective state of the Entity (that has not changed) but it is not, feel free to open them an issue.