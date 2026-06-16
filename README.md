# ManiaPlanet scripts
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](http://www.gnu.org/licenses/gpl-3.0) ![GitHub contributors](https://img.shields.io/github/contributors/bahelit/tm2-title-packs.svg) ![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/bahelit/tm2-title-packs.svg)

ManiaScript libraries and game modes for the ManiaPlanet gaming system, plus a
PyPlanet app that runs **Knockout** nights (matches, cups, and the daily Bowl of
the Evening). Originally written by Dommy — credit Dommy if you reuse the scripts.
Issues and PRs welcome. ❤️

**Links:** [ManiaPlanet](http://maniaplanet.com/) · [ManiaPark](https://maniapark.com/) · [TM Exchange](https://tm.mania.exchange/) · [PyPlanet](https://pypla.net/en/latest/index.html)

---

## Quick start (Knockout)

### Prerequisites

1. **TrackMania Nations Forever** — [free on Steam](https://store.steampowered.com/app/11020/TrackMania_Nations_Forever/)
2. **TrackMania Stadium 2 (TM2)** — [on sale on Steam](https://store.steampowered.com/app/232910/TrackMania_Stadium/)
3. **Dedicated Server** — running the TM2 title pack
4. **PyPlanet** — installed and connected to the server

### 1. Copy files to the server

```
apps/knockout/                                          -> <pyplanet>/apps/knockout/   (whole folder)
Scripts/Modes/TrackMania/Knockout.Script.txt            -> <tm2>/Scripts/Modes/TrackMania/
Scripts/Libs/domino54/SentenceBank.Script.txt           -> <tm2>/Scripts/Libs/domino54/
Scripts/Libs/domino54/Translations.Script.txt           -> <tm2>/Scripts/Libs/domino54/
```

### 2. Register the app — `config.yaml`

```yaml
settings:
  pyplanet:
    APPS:
      - 'core.maniaplanet'
      - 'core.admin'
      - 'core.chat'
      - 'core.players'
      - 'apps.knockout'   # <-- add
```

### 3. Set the mode in the playlist XML

Set the script and remove `S_UseLegacyXmlRpcCallbacks` (PyPlanet forces it to `0`):

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
  <setting name="S_FinishTimeout" type="integer" value="20"/>
</script_settings>
```

### 4. Restart

```bash
sudo systemctl restart pyplanet
```

PyPlanet creates its database tables on first start — nothing to migrate by hand.

> **Upgrading an existing DB:** the `save_to_season` toggle adds a `count_in_season`
> column. PyPlanet auto-creates new *tables* but not new *columns*, so run once:
> `ALTER TABLE knockout_cup ADD COLUMN count_in_season INTEGER NOT NULL DEFAULT 1;`

---

## Commands

**Admin (`//`)**

| Command | Description |
|---|---|
| `//cup on [key] [name]` | Start a cup (`key` can match a preset). |
| `//cup off` | Stop the active cup. |
| `//cup setup <preset>` | Push a preset's mode script + settings. |
| `//cup mapcount <n>` | Maps in the cup (0 = open-ended). |
| `//cup edition <n>` | Set edition/week number. |
| `//cup scoremode <id>` | Points table (`default`, `f1`, `flat`, `survival`). |
| `//cup edit <index>` | Toggle whether a map counts. |
| `//cup export` | Write CSV + Discord-markdown standings. |
| `//cup pay [payout]` | Pay planets (needs `cup_payouts_enabled`). |
| `//cotd on [HH:MM]` | Start a Bowl of the Evening (optional cutoff override). |
| `//cotd off` | Cancel it. |
| `//cotd start` | End practice now, start the knockout. |
| `//cotd countdown <seconds>` | Set practice→knockout countdown (default 900). |
| `//ko hud` | Print HUD live state + force a test render. |
| `//ko streamstart` | Mark t=0 for VOD markers. |
| `//ko mark <note>` | Write a manual VOD marker. |

**Public (`/`)**

| Command | Description |
|---|---|
| `/cup status` | Active cup and progress. |
| `/cup results` | Cup standings window. |
| `/cup matches` | Maps played in the cup. |
| `/cup season [key]` | Season leaderboard across all cups. |
| `/cup stats <login>` | A player's cup history. |
| `/cotd status` | Bowl phase, cutoff, current fastest practice time. |

---

## Settings (PyPlanet `//settings`)

**App / notifications**

| Setting | Default | Description |
|---|---|---|
| `notifications` | `true` | Master switch for all Knockout messages. |
| `show_join` / `show_knockout` / `show_winner` | `true` | Join / knockout / winner chat notifications. |
| `show_match_hud` | `true` | Always-on left-side match HUD (match/round/players/KOs + gap-to-leader order). |
| `show_season_points` | `true` | Add a season-total PTS column to the HUD during a cup. |
| `show_overlays` | `false` | Broadcast overlays: players-remaining ticker + elimination lower-third. |
| `show_cup_widget` | `false` | Live cup standings widget (experimental). |
| `save_to_season` | `true` | Off = new cups excluded from the season leaderboard. |
| `cotd_cutoff_time` | `"17:00"` | Server-local `HH:MM` when practice ends and the knockout begins. |
| `cotd_countdown_seconds` | `900` | Seconds between practice closing and knockout start. |
| `cotd_fastest_shield` | `true` | Grant the fastest practice time a one-time shield. |
| `vod_markers_enabled` | `false` | Append timestamped highlight markers to a file. |
| `vod_markers_path` | `""` | Path to the VOD markers file (blank = disabled). |

> Bowl of the Evening timing uses the dedicated server's local clock — the game mode has no wall-clock access.

**Cup**

| Setting | Default | Description |
|---|---|---|
| `cup_presets_path` | `""` | Path to the presets JSON file. |
| `cup_default_score_mode` | `default` | Score mode for cups started without a preset. |
| `cup_payouts_enabled` | `false` | Allow `//cup pay` to send real planets. |
| `cup_export_path` | `""` | Directory for `//cup export` files (blank = working dir). |

**Game mode (`<script_settings>` in the playlist XML)**

| Setting | Default | Description |
|---|---|---|
| `S_RoundsPerMap` | `0` | Rounds per map (0 = infinite). |
| `S_DoubleKnockUntil` | `20` | Knock 2 players at once until this count (0 = off). |
| `S_PracticeRounds` | `0` | Opening rounds with no eliminations (0 = off). |
| `S_EnableShields` | `false` | Round winner banks a one-time auto-spent save. |
| `S_DebugBotsCount` | `0` | Fake bots for testing. |
| `S_FinishTimeout` | `20` | Seconds between rounds. |
| `S_ForceLapsNb` | `0` | Laps per round (0 = 1). |
| `S_AdminHoldStart` | `false` | Admins can pause next round start. |
| `S_AdminSetPause` | `false` | Admins can pause before next round. |
| `S_ShowMultilapInfo` | `true` | Show multi-lap info on screen. |
| `S_CustomLayerPath` | `""` | Optional custom background layer XML. |
| `S_PreShieldLogins` | `""` | Logins granted a shield at match start (set by the Bowl handoff; needs `S_EnableShields`). |

---

## Score modes

| Id | Points by placement |
|---|---|
| `default` | 10, 8, 6, 5, 4, 3, 2, 1 |
| `f1` | 25, 18, 15, 12, 10, 8, 6, 4, 2, 1 |
| `flat` | 1 for the win |
| `survival` | sum of raw knockout survival points |

Tied players (same survival score on a map) share a placement and its points.

---

## Workflows

**Weekly cup**

1. Update the matchsettings map list and restart the server.
2. `//cup setup <preset>` (optional if settings already applied).
3. `//cup on weekly` to start collecting results.
4. Play; `/cup results` shows running standings.
5. Auto-completes at `mapcount` (or `//cup off`); `//cup export`, then `//cup pay` if enabled.

**Bowl of the Evening** — daily one-map event: the map runs as open TimeAttack practice,
then at `cotd_cutoff_time` the app switches the *same map* into Knockout and runs it to a
single winner. Records as a one-map cup with `cup_key = cotd`, so each evening is an
edition (`/cup season cotd`, `/cup stats <login>` track the leaderboard).

1. Pick the day's map (matchsettings / current map).
2. `//cotd on` (or `//cotd on 18:30` to override the cutoff once).
3. At the cutoff, practice closes and a countdown runs (`cotd_countdown_seconds`); the
   fastest practice time gets a shield if `cotd_fastest_shield` is on.
4. The knockout plays to a winner, records into the `cotd` cup, and auto-completes.
5. `//cotd start` skips the countdown; `//cotd off` cancels.

---

## Presets file

Point `cup_presets_path` at a JSON file (see `apps/knockout/presets_example.json`):

- **names** — cup definitions: display name + linked `preset`/`payout`/`scoremode`/`mapcount`.
- **presets** — a mode `script` and `settings` to push with `//cup setup`.
- **payouts** — planet amounts by placement, e.g. `[500, 250, 100]`.

`//cup on weekly` pulls name/score mode/map count from the `weekly` definition;
`//cup setup <preset>` applies that preset's script + settings.

---

## Callbacks

The mode emits these for the app and overlays:

| Callback | Use |
|---|---|
| `KOPlayerAdded` / `KOPlayerRemoved` / `KOSendWinner` | Join / knockout / winner chat notifications. |
| `KOMatchStandings` | Final per-player survival scores → cup points (required for cups). |
| `KORoundOrder` | Live running order each round (danger highlighting). |
| `KOShieldAwarded` / `KOShieldUsed` | Shield events for overlays. |

> Cups and the live order need the updated `Knockout.Script.txt` from this repo. With the
> stock mode script the HUD still works but the round reads `—` and gaps won't populate.

---

## Troubleshooting

- **"Script not found"** — check the 4 script files are at the right paths under `<tm2>/Scripts/`.
- **Callbacks not firing** — ensure `S_UseLegacyXmlRpcCallbacks` isn't `1` (PyPlanet forces `0`).
- **Match HUD blank** — confirm `show_match_hud` is `true`, then run `//ko hud`: the first line
  should read `enabled(cached)=True setting=True`. The HUD only shows while a Knockout mode is
  loaded with a player present. `KORoundOrder=0`/`KORoundStart=0` during a scored round means the
  stock mode script is loaded instead of this repo's. A `Last real HUD refresh error` line, if
  shown, is the exact reason it's blank.
