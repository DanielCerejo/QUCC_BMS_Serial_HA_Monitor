# Changelog

## 1.0.14 (2025-08-28)

- Added support for /dev/ttyUSB1 device in addition to /dev/ttyUSB0

## 1.0.13 (2025-05-29)

- Add 'device_polling_interval' option for configurable monitoring frequency

## 1.0.12 (2025-05-28)

- Corrected undefined "power" variable when BMS enters sleep mode

## 1.0.11 (2025-05-26)

- Add battery power calculation (positive for charging, negative for discharging)

## 1.0.10 (2024-01-17)

- Add Cell Max and Min voltage monitoring

## 1.0.9 (2023-12-21)

- Fix error installing python3 and dependencies on latest Alpine container image

## 1.0.8 (2022-10-26)

- Add individual cell voltage monitoring

## 1.0.7 (2022-10-24)

- Keep measurements after BMS power down to maintain last known state

## 1.0.6 (2022-10-23)

- Fix issue #1 - improved error handling

## 1.0.5 (2022-10-21)

- Printf now includes timestamps for better debugging
- Do not repeat error messages when BMS goes offline
- Update README.md with better documentation

## 1.0.4 (2022-10-15)

- Correct addon name and power_discharging signal handling

## 1.0.3 (2022-10-15)

- Separate battery power into charging and discharging metrics
- Add LICENSE file
- Code cleanup and improvements

## 1.0.2 (2022-10-15)

- Second initial commit with core functionality

## 1.0.1 (2022-10-13)

- First initial commit