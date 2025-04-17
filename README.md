# 🌀 iaqualink_iqpump01 - Home Assistant Integration

Custom integration for Home Assistant to control **Jandy variable-speed pool pumps** via the **iQPump01 Wi-Fi module**, using the **iAquaLink cloud API**.

This integration allows you to start/stop the pump, adjust its speed, and monitor its status — all from Home Assistant.

---

## 🌟 Features

- ✅ Control your Jandy VS pumps (e.g., VSFHP165JEP)
- 🔁 Set pump speed via a `number` entity
- 🔍 Monitor current operating mode and state
- 🧠 Works with Home Assistant automations and dashboards
- 🐛 Debug logging included for troubleshooting
- ☁️ Uses the official iAquaLink API (cloud-based)

---

## ⚠️ Compatibility

This integration is designed for devices detected as **`i2d`** type in iAquaLink (such as the iQPump01 controller).

---

## 🔧 Installation

### Option 1 – HACS (Recommended)
1. Go to **HACS > Integrations > + Explore & Add Repositories**
2. Search for `iaqualink_iqpump01`
3. Install the integration
4. Restart Home Assistant

### Option 2 – Manual Installation
1. Download or clone this repository into your Home Assistant config directory:
   ```
   custom_components/iaqualink_iqpump01/
   ```
2. Restart Home Assistant

---

## ⚙️ Configuration

After installation:

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **iAquaLink iQPump01**
3. Enter your **iAquaLink email and password**
4. The integration will automatically:
   - Log in to the API
   - Detect supported devices
   - Create entities 
   

## 🧪 Debugging

Enable debug logs in `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.iaqualink_iqpump01: debug
```

You can view logs in **Settings > System > Logs**.

---

## 🙏 Credits

This integration is independently developed by Quentin Clarenne, based on reverse-engineering of the iAquaLink API using `mitmproxy`.

---

## 🛑 Disclaimer

This integration is not affiliated with, endorsed by, or supported by Zodiac®, Jandy®, or Fluidra®. Use at your own risk. Cloud APIs may change at any time.
