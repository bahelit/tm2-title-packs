# ManiaPlanet scripts
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](http://www.gnu.org/licenses/gpl-3.0) ![GitHub contributors](https://img.shields.io/github/contributors/bahelit/tm2-title-packs.svg) ![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/bahelit/tm2-title-packs.svg)

All ManiaScript libraries written by Dommy for ManiaPlanet gaming system. Files include sources of ShootMania Galaxy pack game modes and libraries used by TrackMania² Pursuit game mode. Feel free to use them for your projects, but remember to credit Dommy in your final work. If you got any ideas or suggestions for my work, or you want to contribute to the translations collection, don't be afraid to open an issue or do a pull request! ❤️️

## Useful links

* [ManiaPlanet - platform for TrackMania² and ShootMania games by Nadeo](http://maniaplanet.com/)

## Knockout mode with PyPlanet

### Prerequisites

1. **TrackMania Nations Forever** — free on Steam
2. **TrackMania Stadium 2 (TM2)** — the main title pack
3. **Dedicated Server** — running the TM2 title pack
4. **PyPlanet** — installed and connected to the server

### Files needed

Copy these 5 files to your server:

```
<pyplanet>/apps/knockout/__init__.py            # PyPlanet app
<pyplanet>/config.yaml                          # PyPlanet config (add app to APPS list)
<tm2>/Scripts/Modes/TrackMania/Knockout.Script.txt   # Game mode script
<tm2>/Scripts/Libs/domino54/SentenceBank.Script.txt  # Dependency
<tm2>/Scripts/Libs/domino54/Translations.Script.txt  # Dependency
```

### Step 1: Register the PyPlanet app

In your PyPlanet `config.yaml`, add `apps.knockout` to the `APPS` list:

```yaml
settings:
  pyplanet:
    APPS:
      - 'core.maniaplanet'
      - 'core.admin'
      - 'core.chat'
      - 'core.players'
      - 'apps.knockout'  # <-- add this line
```

### Step 2: Update the playlist XML

In your map playlist XML (`playlist.ini` or `.xml`), set the script name and add Knockout settings. Remove `S_UseLegacyXmlRpcCallbacks` so PyPlanet controls callback format:

```xml
<gameinfos>
  <game_mode>0</game_mode>
  <script_name><![CDATA[Modes/TrackMania/Knockout.Script.txt]]></script_name>
</gameinfos>

<script_settings>
  <setting name="S_RoundsPerMap" type="integer" value="0"/>
  <setting name="S_DoubleKnockUntil" type="integer" value="20"/>
  <setting name="S_DebugBotsCount" type="integer" value="0"/>
  <setting name="S_FinishTimeout" type="integer" value="20"/>
  <setting name="S_ForceLapsNb" type="integer" value="0"/>
  <setting name="S_AdminHoldStart" type="boolean" value="0"/>
  <setting name="S_AdminSetPause" type="boolean" value="0"/>
  <setting name="S_ShowMultilapInfo" type="boolean" value="1"/>
  <setting name="S_CustomLayerPath" type="text" value=""/>
</script_settings>
```

### Step 3: Restart PyPlanet

```bash
sudo systemctl restart pyplanet
```

### What the app does

The Knockout app listens for 3 scripted callbacks and sends chat notifications:

| Callback | Notification |
|---|---|
| `KOPlayerAdded` | `$f90>>> {name} joined Knockout!` |
| `KOPlayerRemoved` | `$f00>>> {name} was knocked out!` |
| `KOSendWinner` | `$0f0>>> {name} is the winner!` |

These are controlled by settings in PyPlanet:

| Setting | Default | Description |
|---|---|---|
| `notifications` | `true` | Master switch for all Knockout messages |
| `show_join` | `true` | Join notifications |
| `show_knockout` | `true` | Knockout notifications |
| `show_winner` | `true` | Winner notifications |

### Knockout game settings

| Setting | Default | Description |
|---|---|---|
| `S_RoundsPerMap` | `0` | Number of rounds per map (0 = infinite) |
| `S_DoubleKnockUntil` | `20` | Knock 2 players simultaneously until this count (0 = disabled) |
| `S_DebugBotsCount` | `0` | Fake bot players for testing |
| `S_FinishTimeout` | `20` | Time limit between rounds in seconds |
| `S_ForceLapsNb` | `0` | Force laps per round (0 = 1 lap) |
| `S_AdminHoldStart` | `false` | Allow admins to pause next round start |
| `S_AdminSetPause` | `false` | Allow admins to pause match before next round |
| `S_ShowMultilapInfo` | `true` | Show multi-lap info on screen |
| `S_CustomLayerPath` | `""` | Optional path to custom background layer XML |

### Troubleshooting

- **"Script not found" errors** — verify the 4 script files are in the correct relative paths under `<tm2>/Scripts/`
- **RoundsBase errors** — the TM2 base title pack isn't loading correctly
- **Callbacks not firing** — make sure `S_UseLegacyXmlRpcCallbacks` is not set to `1` in your XML; PyPlanet overrides it to `0`
