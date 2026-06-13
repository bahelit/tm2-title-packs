"""
Unit tests for the pure (pyplanet-free) Knockout match-HUD helpers in
apps/knockout/hud_format.py. Loaded by path so they run without pyplanet.

Run with:  python -m pytest tests/test_knockout_hud.py
       or:  python tests/test_knockout_hud.py
"""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_KO = os.path.join(_HERE, '..', 'apps', 'knockout')


def _load(name, filename):
	spec = importlib.util.spec_from_file_location(name, os.path.join(_KO, filename))
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


hud = _load('ko_hud_format', 'hud_format.py')


# --------------------------------------------------------------- race times

def test_format_race_time_under_a_minute():
	assert hud.format_race_time(42123) == '42.123'
	assert hud.format_race_time(0) == '0.000'
	assert hud.format_race_time(5) == '0.005'


def test_format_race_time_over_a_minute():
	assert hud.format_race_time(61000) == '1:01.000'
	assert hud.format_race_time(125678) == '2:05.678'


def test_format_race_time_unset_is_dash():
	assert hud.format_race_time(-1) == '—'
	assert hud.format_race_time(None) == '—'
	assert hud.format_race_time('nope') == '—'


# --------------------------------------------------------------- row colours

def test_row_color_priority():
	# Danger wins even if the player has finished (they are still on the bubble).
	assert hud.row_color(True, True) == 'FF3333'
	assert hud.row_color(True, False) == 'FF3333'
	assert hud.row_color(False, True) == '66FF66'
	assert hud.row_color(False, False) == 'FFFFFF'


# --------------------------------------------------------------- round label

def test_round_label_bounded_and_unbounded():
	assert hud.round_label(3, 5) == 'ROUND 3 / 5'
	assert hud.round_label(3, 0) == 'ROUND 3'
	assert hud.round_label(1, 1) == 'ROUND 1 / 1'


def test_round_label_before_first_round():
	assert hud.round_label(0, 5) == 'KNOCKOUT'
	assert hud.round_label('x', 5) == 'KNOCKOUT'


if __name__ == '__main__':
	import sys
	import traceback

	failures = 0
	for name, fn in sorted(globals().items()):
		if name.startswith('test_') and callable(fn):
			try:
				fn()
				print('ok   ', name)
			except Exception:
				failures += 1
				print('FAIL ', name)
				traceback.print_exc()
	sys.exit(1 if failures else 0)
