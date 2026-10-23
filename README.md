# HAutoClicker (HAC)

We are moving to Rust, the HAC's v1 will be release in this [repo](https://github.com/JMF-Alex/hac), and all the new releases will be there.

A fast, lightweight autoclicker for Windows and Linux, built with Python and Tkinter. Pick a key or mouse button, set the interval, and start or stop from any window with a single hotkey.

[![License](https://img.shields.io/github/license/JMF-Alex/HAC?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/JMF-Alex/HAC?style=flat-square)](https://github.com/JMF-Alex/HAC/stargazers)
[![Issues](https://img.shields.io/github/issues/JMF-Alex/HAC?style=flat-square)](https://github.com/JMF-Alex/HAC/issues)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-0078D4?style=flat-square)

![HAutoClicker main window](docs/images/main.png)

## Table of Contents

1. [Features](#features)
2. [Getting Started](#getting-started)
   * [Prerequisites](#prerequisites)
   * [Installation](#installation)
3. [Usage](#usage)
4. [Configuration](#configuration)
5. [Building an Executable](#building-an-executable)
6. [Running the Tests](#running-the-tests)
7. [Project Structure](#project-structure)
8. [Roadmap](#roadmap)
9. [Contributing](#contributing)
10. [License](#license)
11. [Acknowledgments](#acknowledgments)

## Features

- **Two modes**: *Click* repeats the key or button at your interval, *Hold* keeps it pressed until you stop.
- **Flexible intervals**: from 0.001 seconds (1 ms) up to one hour, with optional random variation.
- **Any target**: the left, right or middle mouse button, or a keyboard key (letters, arrows, `space`, `shift`, `ctrl`, `alt`, `enter`, `tab`).
- **Profiles**: create, rename, duplicate and delete profiles. Each one has its own settings and its own global hotkey.
- **Global hotkeys**: `F6` by default, work from any window. Pressing another profile's hotkey switches to it and starts it.
- **Stop after**: stop automatically after a number of clicks or seconds, and add a countdown before the first click.
- **Fail-safe corner**: move the mouse into a chosen screen corner to stop clicking at once.
- **Settings that stick**: everything is saved and restored on the next launch.
- **Safe by design**: settings are locked while clicking, and a held key is released when you close the app.
- **Modern dark interface**: rounded cards, toggle switches and a matching dark title bar on Windows 10 and 11. Sharp on high-DPI screens.

## Getting Started

### Prerequisites

- Windows 10 or 11, or Linux with an X11 session.
- [Python 3.11+](https://www.python.org/downloads/) with Tkinter. Tkinter ships with the official Windows installer; on Debian/Ubuntu install `python3-tk`.

### Installation

1. Clone the repository and enter it:

```bash
git clone https://github.com/JMF-Alex/HAC.git
cd HAC
```

2. Install the dependencies (`keyboard` on Windows, `pynput` on Linux):

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python src/main.py
```

## Usage

1. Set the **interval** between clicks, in seconds. For example, `0.01` is one click every 10 ms.
2. Choose the **mode** and the **key or button** to press.
3. Click **Start clicking**, or press the profile's hotkey (`F6` by default).
4. Click **Stop clicking**, or press the hotkey again, to stop.

![HAutoClicker while clicking](docs/images/running.png)

While HAC is running, the profile's settings are locked so that what you see is what is being sent. The status badge in the top right turns green, the main button turns red, and the line under it shows a live click counter.

| Mode  | What it does                                                           |
| ----- | ---------------------------------------------------------------------- |
| Click | Presses and releases the key or button once per interval.              |
| Hold  | Presses the key or button and keeps it down until you stop. The interval is ignored. |

The **Advanced** tab adds random variation, a start delay and a stop condition. The **Settings** tab holds the fail-safe corner, always-on-top and sound options, which apply to every profile.

### Changing the hotkey

Click **Change**, then press the key you want. Press `Esc` to keep the current one. The new hotkey is saved right away.

The hotkey is global, so it also fires while you type in other programs. Pick a key you do not use during that time, such as one of the `F` keys, and avoid letters.

### Tips

- If the program you want to click in runs as administrator, start HAC as administrator too. Windows blocks input from a normal program to an elevated one.
- Mouse buttons are named `mouse_left`, `mouse_right` and `mouse_middle`. The plain `left` and `right` entries are the keyboard arrow keys.
- Values outside the allowed range are corrected automatically to the nearest limit.

## Configuration

HAC stores its settings in `%APPDATA%\HAutoClicker\config.json` on Windows and `~/.config/HAutoClicker/config.json` on Linux, next to a `hac.log` file that records errors. Set the `HAC_CONFIG_DIR` environment variable to use another folder. You do not need to edit the file by hand, but you can:

```json
{
    "version": 5,
    "active_profile": "Default",
    "profiles": {
        "Default": {
            "interval": 0.01,
            "hotkey": "F6",
            "mode": "Click",
            "target_key": "mouse_left",
            "jitter": 0.0,
            "limit_kind": "Never",
            "limit_value": 100.0,
            "start_delay": 0.0
        }
    },
    "settings": {
        "failsafe": "Off",
        "always_on_top": false,
        "sound": false
    }
}
```

| Key           | Meaning                                    | Valid values                                                           |
| ------------- | ------------------------------------------ | ---------------------------------------------------------------------- |
| `interval`    | Seconds between clicks                     | `0.001` to `3600`                                                      |
| `hotkey`      | Key that starts and stops this profile     | A key name, for example `F6`, or empty for none                        |
| `mode`        | How the key or button is pressed           | `Click` or `Hold`                                                      |
| `target_key`  | What is pressed                            | `mouse_left`, `mouse_right`, `mouse_middle`, `a` to `z`, `space`, `shift`, `ctrl`, `alt`, `enter`, `tab`, `up`, `down`, `left`, `right` |
| `jitter`      | Random variation of each delay, in percent | `0` to `100`                                                           |
| `limit_kind`  | When to stop on its own                    | `Never`, `Clicks` or `Time`                                            |
| `limit_value` | Clicks or seconds for the limit            | `1` to `1000000`                                                       |
| `start_delay` | Countdown before the first click, seconds  | `0` to `60`                                                            |
| `failsafe`    | Screen corner that stops clicking          | `Off`, `Top-left`, `Top-right`, `Bottom-left`, `Bottom-right`          |

Invalid or missing values fall back to the defaults, and a corrupted file never stops the app from starting. Settings from older versions (including `hac_config.json` in your home folder) are migrated automatically.

## Building an Executable

Install the development dependencies, then run the build script for your platform:

```bash
pip install -r requirements-dev.txt
./build.ps1      # Windows: dist/HAC_Autoclicker.exe
bash build.sh    # Linux:   dist/HAC_Autoclicker
```

## Running the Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests live in `tests/` and mirror the layout of `src/`: the tests for `src/core/storage/config.py` are in `tests/core/storage/test_config.py`, and so on.

## Project Structure

```text
HAC/
├── src/
│   ├── main.py                  Entry point (sets up logging and starts the app)
│   ├── assets/icon.ico          Application icon
│   ├── core/                    Everything that works without a window
│   │   ├── constants.py         Limits, defaults and choices shared by the app
│   │   ├── engine/              Clicker thread and fail-safe corner check
│   │   ├── storage/             Config file, profile names and app folders
│   │   └── system/              OS access: global hotkeys, input simulation, timer resolution
│   └── gui/                     Tkinter interface
│       ├── app.py               Creates the window and wires everything together
│       ├── controller.py        App logic between the clicker and the views
│       ├── theme.py             Colors, fonts and DPI scaling
│       ├── formatting.py        Text helpers (durations, counters, intervals)
│       ├── views/               Main window, sidebar, action bar and the tab pages
│       ├── widgets/             Reusable rounded widgets (buttons, cards, fields, switches...)
│       └── utils/               Icon loading and Windows title-bar styling
├── tests/                       Pytest suite, same layout as src/
└── docs/images/                 Screenshots used in this README
```

## Roadmap

- [x] Save and restore settings
- [x] Dark redesign with a profiles sidebar
- [x] Profile management: create, rename, duplicate, delete and switch profiles
- [x] Per-profile settings: hotkey, interval, key and mode
- [x] Click and time limits, start delay and random variation
- [x] Fail-safe corner, always on top and sound

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch (`git checkout -b feature/MyFeature`)
3. Commit your changes (`git commit -m "Add new feature"`)
4. Push to your branch (`git push origin feature/MyFeature`)
5. Open a Pull Request

## License

Distributed under the MIT license.

See the [`LICENSE`](LICENSE) file for more information.

## Acknowledgments

- Base template inspired by [Othneil Drew's Best-README-Template](https://github.com/othneildrew/Best-README-Template)
- README Generated with [README-Generator](https://github.com/JMF-Alex/README-Generator)
- Developed by [JMF-Alex](https://github.com/JMF-Alex)
