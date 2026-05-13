[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/CLARENNE-Q/iaqualink_iqpump01)
![version](https://img.shields.io/badge/version-1.0.6-blue)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-%23FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/clarenneq)

# iAquaLink iQPump01

Control your Jandy iQPump01 variable-speed pool pump directly from Home Assistant — no third-party libraries, using the native iAquaLink/Zodiac API.

## ✅ Features

- Turn the pump on/off
- Set custom target using percentage-based control for 6 hours
- Monitor current speed, power consumption, motor temperature, Wi-Fi status, etc.
- View advanced attributes like firmware version, priming status, min/max RPM, serial number
- Auto-refresh pump data every 60 seconds (with cache)
- HACS compatible for easy installation

## 🛠 Installation via HACS (recommended)

1. In HACS > Integrations, click the 3-dot menu > Custom Repositories
2. Add this repository: `https://github.com/CLARENNE-Q/iaqualink_iqpump01`
3. Choose category: Integration
4. Install the integration and restart Home Assistant
5. Go to **Settings > Devices & Services > Add Integration**, search for `iAquaLink iQPump01`

## ⚙️ Configuration

During setup, you'll need to provide:
- Your iAquaLink email
- Your iAquaLink password

No further configuration is needed.

## 📈 Entities created

| Entity | Description |
|--------|-------------|
| `switch.pump_i2d` | Turn the pump on or off |
| `number.pump_rpm_target_percentage` | Target RPM (%) — mapped to actual RPM using min/max range |
| `sensor.pump_power` | Power consumption (W) |
| `sensor.pump_speed` | Current speed (RPM) |
| ... | Additional attributes on switch.pump_i2d such as temperature, runstate, firmware, priming, max/min-speed, serial, Wi-Fi, and more |


## 📌 Current limitations

- Only supports a single pump (first device of type `i2d`)
- No multi-pump support yet (planned for future release)
- Requires a valid iAquaLink account with a registered iQPump01 pump
- Only compatible with iQPump01: This integration is designed specifically for the Jandy iQPump01 controller. 
- Refresh rate is limited to 60 seconds: To avoid overloading the vendor's API and triggering rate limits, the integration uses a caching mechanism with a refresh interval of 60 seconds. All data sensors and status updates rely on this rate.

## 🐞 Debugging

If you have another pump model and it doesn’t work out of the box, I may be able to investigate further **if you share the full raw API payloads** returned by your device.

### 🔍 How to enable debug logs

1. Edit your `configuration.yaml` (or go to **Settings > System > Logs > Configure**)
2. Add the following to enable detailed logs:

```yaml
logger:
  default: warning
  logs:
    custom_components.iaqualink_iqpump01: debug
```

3. Restart Home Assistant

### 📤 How to extract debug logs

Run this command from your Home Assistant terminal or SSH:

```bash
cat /config/home-assistant.log | grep iaqualink_iqpump01
```

This will filter the relevant debug messages from the integration.

> ⚠️ **Important**: Before pasting logs in an issue, always review them and **remove your email, password, authentication tokens, and serial numbers**. These are private and should never be shared publicly.


## 🚀 Planned Features

- Support for multiple pumps (`i2d` devices)
- Automatic discovery of other iAquaLink-compatible devices
- Local API fallback (if available)
- Pump scheduling and advanced automation templates
- UI card suggestions for Lovelace Dashboard


## ⚖️ Disclaimer

This project is not affiliated with or endorsed by Zodiac, Jandy, or iAquaLink.  
It is a community-driven effort to bridge iQPump01 devices with Home Assistant using public and reverse-engineered API behavior.  
Use at your own risk.


## 🙏 Thanks

Big thanks to the Home Assistant community and to all the explorers diving into Zodiac APIs 🌊

Special thanks to Zodiac / iAquaLink / Jandy for creating reliable, high-quality smart pool equipment.

This project is not only a technical exploration, but also a way to promote and showcase the value of your connected pool systems. Many Home Assistant users are eager to integrate their iQPump01 into their smart home ecosystem.

If you are part of the Zodiac team, feel free to reach out via a GitHub issue. I’d be happy to explore collaboration opportunities — including the possibility of a local API for better real-time control and offline access.
