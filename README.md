# HA Addon for QUCC Smart BMS

Home assistant addon that monitors QUCC BMS via SERIAL interface


## Install

Add https://github.com/DanielCerejo/home-assistant-addons to the addon store repositories.


## Energy and power

To get `kWh` for energy "Battery Power Charging" and "Battery Power Discharging", you can create an integration sensor from  https://www.home-assistant.io/integrations/integration/ 
- select:
    - Integration method: Left Riemann sum
    - Metric prefix: select k (kilo)

The Left "Integration method" is important, BMS will enter offline (low power mode) at 0A current.  Irterpolation will give the wrong value.

To track consumptions use Utility Meter: 
https://www.home-assistant.io/integrations/utility_meter/