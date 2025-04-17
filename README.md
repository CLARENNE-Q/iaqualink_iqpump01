# iAquaLink iQPump01

Control your Jandy iQPump01 variable-speed pool pump directly from Home Assistant — no third-party libraries, using the native iAquaLink/Zodiac API.

## ✅ Features

- Turn the pump on/off
- Set custom target RPM
- Monitor current speed, power consumption, motor temperature, Wi-Fi status, etc.
- View advanced attributes like firmware version, priming status, and serial number
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

## 📌 Current limitations

- Only supports a single pump (first device of type `i2d`)
- No multi-pump support yet (planned for future release)
- Requires a valid iAquaLink account with a registered iQPump01 pump

## 📈 Entities created

| Entity | Description |
|--------|-------------|
| `switch.pump_i2d` | Turn the pump on or off |
| `number.pump_rpm_target` | Set the target RPM |
| `sensor.pump_power` | Power consumption (W) |
| `sensor.pump_speed` | Current speed (RPM) |
| ... | Additional attributes such as temperature, runstate, firmware, priming, max/min-speed, serial, Wi-Fi, and more |

## 🙏 Thanks

Big thanks to the Home Assistant community and to all the explorers diving into Zodiac APIs 🌊
