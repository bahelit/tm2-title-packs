# ManiaPlanet scripts
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](http://www.gnu.org/licenses/gpl-3.0) ![GitHub contributors](https://img.shields.io/github/contributors/bahelit/tm2-title-packs.svg) ![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/bahelit/tm2-title-packs.svg)

All ManiaScript libraries written by Dommy for ManiaPlanet gaming system. Files include sources of ShootMania Galaxy pack game modes and libraries used by TrackMania² Pursuit game mode. Feel free to use them for your projects, but remember to credit Dommy in your final work. If you got any ideas or suggestions for my work, or you want to contribute to the translations collection, don't be afraid to open an issue or do a pull request! ❤️️

## Useful links

* [ManiaPlanet - platform for TrackMania² and ShootMania games by Nadeo](http://maniaplanet.com/)
* [ManiaPark - Find car models, car skins, texture mods and other community content](https://maniapark.com/)
* [TM Exchange - Find tracks, replays and community content](https://tm.mania.exchange/)
* [PyPlanet -  A Maniaplanet/Trackmania Dedicated Server Controller](https://pypla.net/en/latest/index.html)

## Knockout mode with PyPlanet

### Prerequisites

1. **TrackMania Nations Forever** — free on Steam
2. **TrackMania Stadium 2 (TM2)** — the main title pack
3. **Dedicated Server** — running the TM2 title pack
4. **PyPlanet** — installed and connected to the server

### Files needed

Copy the PyPlanet app (the whole `apps/knockout/` folder) and the game-mode scripts to your server:

```
<pyplanet>/apps/knockout/                       # PyPlanet app (copy the ENTIRE folder)
<pyplanet>/config.yaml                          # PyPlanet config (add app to APPS list)
<tm2>/Scripts/Modes/TrackMania/Knockout.Script.txt   # Game mode script
<tm2>/Scripts/Libs/domino54/SentenceBank.Script.txt  # Dependency
<tm2>/Scripts/Libs/domino54/Translations.Script.txt  # Dependency
```

`apps/knockout/` is a Python package — copy the directory and everything in it:

```
apps/knockout/
  __init__.py            # AppConfig: notifications + cup wiring
  capture.py             # records each map's standings to the database
  cup.py                 # cup lifecycle (start/stop, mapcount, edition, scoremode)
  commands.py            # //cup and /cup chat commands
  results.py             # cross-map score summation + results UI
  score_modes.py         # points-by-placement tables
  config.py              # loads the cup presets JSON
  payouts.py             # planet payouts by placement
  presets_example.json   # sample presets file (copy & edit, then set cup_presets_path)
  models/                # database models (cup, match, player score)
  views/                 # results / matches windows + live widget
  templates/             # widget ManiaLink template
```

PyPlanet creates the database tables automatically on first start; there is nothing to
migrate by hand.

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
  <setting name="S_PracticeRounds" type="integer" value="0"/>
  <setting name="S_EnableShields" type="boolean" value="0"/>
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

The Knockout app listens for scripted callbacks and sends chat notifications:

| Callback | Notification |
|---|---|
| `KOPlayerAdded` | `$f90>>> {name} joined Knockout!` |
| `KOPlayerRemoved` | `$f00>>> {name} was knocked out!` |
| `KOSendWinner` | `$0f0>>> {name} is the winner!` |

The mode also emits callbacks consumed by the broadcast overlays (no chat
notification): `KORoundOrder` (live running order each round, for danger
highlighting), `KOShieldAwarded`, and `KOShieldUsed`.

These are controlled by settings in PyPlanet:

| Setting | Default | Description |
|---|---|---|
| `notifications` | `true` | Master switch for all Knockout messages |
| `show_join` | `true` | Join notifications |
| `show_knockout` | `true` | Knockout notifications |
| `show_winner` | `true` | Winner notifications |
| `show_match_hud` | `true` | Always-on left-side match HUD (round, players alive, KOs/round, live times) shown to everyone |
| `show_overlays` | `false` | Broadcast overlays: players-remaining ticker + elimination lower-third |
| `show_cup_widget` | `false` | Live cup standings widget during an active cup (experimental) |
| `vod_markers_enabled` | `false` | Append timestamped highlight markers to a file |
| `vod_markers_path` | `""` | Path to the VOD markers file (blank = disabled) |

### Match HUD

- **Live match HUD** (`show_match_hud`, **on by default**): an always-on panel on
  the left of the screen, shown to racers and spectators alike, with the round
  number, how many players are still alive, how many get knocked out this round,
  and the running order with each player's time (bubble player(s) tinted red,
  safe finishers green). It stays up for the whole Knockout while that mode is
  loaded — including **warm-up**, where it lists the players on the server with
  their best lap so far (from the standard finish callback) and fills in the
  round/elimination detail once scored rounds begin. It only hides when the
  loaded mode is not Knockout, or when nobody is on the server. The round number
  needs the updated `Knockout.Script.txt` deployed to the dedicated server;
  without it the HUD still works but the header reads `KNOCKOUT` instead of
  `ROUND x / y`. Use `//ko hud` (admin) to print the HUD's live state and force a
  test render when diagnosing.

### Streaming / broadcast features

For livestreamed nights, the app adds spectator-facing extras (all opt-in):

- **Live ticker + danger highlighting** (`show_overlays`): a "players remaining"
  ticker, with the player(s) currently on the elimination bubble tinted red,
  driven by the mode's `KORoundOrder` callback. The final two trigger a
  "showdown" treatment.
- **Elimination lower-third** (`show_overlays`): a transient banner on each
  knockout, the round winner, and shield events.
- **Earned shields** (`S_EnableShields`): the fastest finisher of a round banks a
  one-time save; it auto-spends to keep them in when they'd otherwise be knocked
  out (the elimination passes to the next-slowest finisher). Shields never save a
  DNF or give-up.
- **Practice rounds** (`S_PracticeRounds`): the opening N rounds run with no
  eliminations, so a bad spawn lap doesn't end someone's night instantly.
- **Season leaderboard & stats** (`/cup season`, `/cup stats <login>`): totals
  across every cup — points, wins, podiums — with per-player history.
- **VOD highlight markers** (`vod_markers_enabled` + `vod_markers_path`): a file
  of timestamped events (map starts, eliminations, showdowns, winners, shields)
  for fast clipping afterwards. `//ko streamstart` sets the stream-relative clock.

### Knockout game settings

| Setting | Default | Description |
|---|---|---|
| `S_RoundsPerMap` | `0` | Number of rounds per map (0 = infinite) |
| `S_DoubleKnockUntil` | `20` | Knock 2 players simultaneously until this count (0 = disabled) |
| `S_PracticeRounds` | `0` | Opening rounds with no eliminations (0 = disabled) |
| `S_EnableShields` | `false` | Earned shields: the round winner banks a one-time save, auto-spent to avoid a knockout |
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
- **Match HUD never appears** — confirm `show_match_hud` is `true` in `//settings` (it defaults on). Run `//ko hud`: the first line shows `enabled(cached)=… setting=…` (both should be `True`) and `phase=…`. The HUD only shows while a **Knockout** mode is loaded and at least one player is on the server. During warm-up it lists players with their best lap; `phase=idle` there is normal. If the `callbacks:` line shows `KORoundOrder=0`/`KORoundStart=0` during a scored round, the stock mode script is loaded instead of the updated `Knockout.Script.txt` (so the round number and live order won't populate). A `Last real HUD refresh error` line, if present, is the exact reason the panel is blank.

## Knockout Cup Manager

The `apps.knockout` app also runs **cups**: it records each map's result and sums
scores across a list of maps into an overall standing. This is built into the app —
you do **not** need the separate `pyplanet-cup_manager` plugin.

### How it works

At the end of each map the Knockout mode emits a `KOMatchStandings` callback with every
player's final survival score. The app stores one match + per-player rows in its
database, and (while a cup is running) links the map to the active cup. Each map's
finishing order is turned into cup points via a **score mode** table, and points are
summed across the cup's maps. All cup state is persisted, so it survives a PyPlanet
restart.

> Requires the updated `Knockout.Script.txt` from this repo (it adds the
> `KOMatchStandings` callback). The weekly map list comes from your dedicated-server
> matchsettings file — the cup just tracks results across whatever maps it rotates.

### Commands

Admin (`//`):

| Command | Description |
|---|---|
| `//cup on [key] [name]` | Start a cup. `key` can match a preset name; `name` is optional. |
| `//cup off` | Stop the active cup. |
| `//cup setup <preset>` | Push a preset's mode script + settings to the server. |
| `//cup mapcount <n>` | Set the number of maps (cup auto-completes when reached; 0 = open-ended). |
| `//cup edition <n>` | Set the edition/week number. |
| `//cup scoremode <id>` | Set the points table (`default`, `f1`, `flat`, `survival`). |
| `//cup edit <index>` | Toggle whether the map at that index counts towards totals. |
| `//cup export` | Write CSV + Discord-markdown files of the standings. |
| `//cup pay [payout]` | Pay planets to the standings (requires `cup_payouts_enabled`). |
| `//ko streamstart` | Mark t=0 for VOD highlight markers (stream-relative clock). |
| `//ko mark <note>` | Write a manual VOD highlight marker. |

Public (`/`):

| Command | Description |
|---|---|
| `/cup status` | Show the active cup and progress. |
| `/cup results` | Open the cup standings window. |
| `/cup matches` | List the maps played in the cup. |
| `/cup season [key]` | Open the season leaderboard across all cups (optionally one cup key). |
| `/cup stats <login>` | Open a player's cup history (cups, wins, podiums, places). |

### Score modes

| Id | Points by placement |
|---|---|
| `default` | 10, 8, 6, 5, 4, 3, 2, 1 |
| `f1` | 25, 18, 15, 12, 10, 8, 6, 4, 2, 1 |
| `flat` | 1 for the win |
| `survival` | sum of raw knockout survival points |

Tied players (same survival score on a map) share a placement and its points.

### Presets file

Point the `cup_presets_path` setting at a JSON file (see
`apps/knockout/presets_example.json`) with three sections:

- **names** — cup definitions: display name + linked `preset`/`payout`/`scoremode`/`mapcount`.
- **presets** — a mode `script` and `settings` to push with `//cup setup`.
- **payouts** — planet amounts by placement, e.g. `[500, 250, 100]`.

`//cup on weekly` then pulls the name, score mode and map count from the `weekly`
definition; `//cup setup knockout_rotate` applies that preset's script/settings.

### Cup settings (PyPlanet)

| Setting | Default | Description |
|---|---|---|
| `cup_presets_path` | `""` | Path to the presets JSON file |
| `cup_default_score_mode` | `default` | Score mode for cups started without a preset |
| `cup_payouts_enabled` | `false` | Allow `//cup pay` to send real planets |
| `cup_export_path` | `""` | Directory for `//cup export` files (blank = working dir) |
| `show_cup_widget` | `false` | Show an experimental live standings widget |

### Weekly cup workflow

1. Update the matchsettings map list for the week and restart the server.
2. `//cup setup <preset>` to apply the cup's mode settings (optional if already set).
3. `//cup on weekly` to start collecting results.
4. Play through the maps; `/cup results` shows running standings.
5. The cup auto-completes at `mapcount` (or `//cup off`); `//cup export` saves the
   results, and `//cup pay` distributes planets if enabled.
