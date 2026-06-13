import logging

from pyplanet.apps.core.maniaplanet import callbacks as mp_signals
from pyplanet.core.events import Callback

logger = logging.getLogger(__name__)


def _flatten(source):
	"""
	Normalise the shapes a ModeScript array callback can arrive in into a flat
	list of strings. Mirrors capture._flatten so KORoundOrder is parsed the same
	way as KOMatchStandings.
	"""
	data = source
	if isinstance(data, dict):
		data = data.get('data') or data.get('params') or list(data.values())
	if (isinstance(data, (list, tuple)) and len(data) == 2
			and isinstance(data[1], (list, tuple))):
		data = data[1]
	if not isinstance(data, (list, tuple)):
		data = [data]
	return [str(item) for item in data]


async def parse_round_order(source, signal, **kwargs):
	"""
	Parse a KORoundOrder payload into an ordered list (best first). Each entry is
	``login:rank:cps:time:finished``; only ``login`` is required, the rest are
	best-effort. Returns ``{'order': [ {login, rank, cps, time, finished} ... ]}``.
	"""
	order = []
	for item in _flatten(source):
		parts = str(item).split(':')
		login = parts[0] if parts else ''
		if not login:
			continue

		def _int(index, default=0):
			try:
				return int(parts[index])
			except (IndexError, ValueError):
				return default

		order.append(dict(
			login=login,
			rank=_int(1, len(order) + 1),
			cps=_int(2, 0),
			time=_int(3, 0),
			finished=_int(4, 0) == 1,
		))
	order.sort(key=lambda entry: entry['rank'])
	return dict(order=order)


async def parse_round_start(source, signal, **kwargs):
	"""
	Parse a KORoundStart payload (``["round:total"]``) into
	``{'round': int, 'total': int}``. ``total`` is 0 when the map is unbounded.
	"""
	items = _flatten(source)
	parts = str(items[0]).split(':') if items else []

	def _int(index):
		try:
			return int(parts[index])
		except (IndexError, ValueError):
			return 0

	return dict(round=_int(0), total=_int(1))


def _first_login(payload):
	"""Pull a single login out of the various payload shapes the mode sends."""
	if isinstance(payload, (list, tuple)):
		return str(payload[0]) if payload else ''
	return str(payload) if payload is not None else ''


class LiveController:
	"""
	Tracks the state of the Knockout match that is being played right now, so the
	broadcast overlays can react in real time. The mode only persists final map
	standings (see capture.py); this controller layers on the live picture:

	* ``racing`` - logins still in the match.
	* ``count``  - how many are still racing.
	* ``danger`` - the player(s) currently on the elimination bubble (from the
	  KORoundOrder callback added to the mode).
	* ``phase``  - 'idle' | 'racing' | 'showdown' (final two) | 'ended'.

	Player added/removed/winner events are routed in from the app's existing
	notification handler so we do not register those signals twice; KORoundOrder
	and the shield callbacks are owned here.
	"""

	# Number of trailing players treated as "in danger" when double-knockout is
	# not active. Re-derived from S_DoubleKnockUntil at map start.
	def __init__(self, app):
		self.app = app
		self.instance = app.instance
		self.racing = []
		self.order = []
		self.phase = 'idle'
		self.round = 0
		self.total_rounds = 0
		self._double_until = 0
		self._order_signal = None
		self._round_signal = None

	@property
	def count(self):
		return len(self.racing)

	async def on_start(self):
		# KORoundOrder: live ordering of the racing players (added in the mode).
		self._order_signal = Callback(
			call='ModeScriptCallback',
			namespace='script',
			code='KORoundOrder',
			target=parse_round_order,
		)
		self.app.context.signals.register_signal(self._order_signal)
		self.app.context.signals.listen(self._order_signal, self.on_round_order)

		# KORoundStart: the round number at the start of each round (added in the
		# mode), so the HUD can show "ROUND x / y".
		self._round_signal = Callback(
			call='ModeScriptCallback',
			namespace='script',
			code='KORoundStart',
			target=parse_round_start,
		)
		self.app.context.signals.register_signal(self._round_signal)
		self.app.context.signals.listen(self._round_signal, self.on_round_start)

		# Shield earned / spent (added in the mode); simple single-login payloads.
		for code, handler in (
			('KOShieldAwarded', self.on_shield_awarded),
			('KOShieldUsed', self.on_shield_used),
		):
			cb = Callback(call='ModeScriptCallback', namespace='script', code=code)
			self.app.context.signals.register_signal(cb)
			self.app.context.signals.listen('script:{}'.format(code), handler)

		# Reset the live picture whenever a new map (and so a new match) starts.
		self.app.context.signals.listen(mp_signals.map.map_start, self.on_map_start)

	# ----------------------------------------------------------------- lifecycle

	async def on_map_start(self, *args, **kwargs):
		self.racing = []
		self.order = []
		self.phase = 'idle'
		self.round = 0
		self.total_rounds = 0
		# Cache the double-knockout threshold so danger highlighting matches how
		# many players the mode will actually knock out this round.
		self._double_until = await self._read_double_until()
		markers = getattr(self.app, 'markers', None)
		if markers is not None:
			try:
				current = self.instance.map_manager.current_map
				await markers.log('map_start', current.name if current else '')
			except Exception:
				logger.exception('Knockout: failed to log map_start marker')
		await self._refresh_overlays()

	async def _read_double_until(self):
		try:
			settings = await self.instance.mode_manager.get_settings()
		except Exception:
			return 0
		try:
			return int(settings.get('S_DoubleKnockUntil', 0) or 0)
		except (TypeError, ValueError):
			return 0

	# ------------------------------------------------- routed from app handlers

	async def on_player_added(self, login):
		if login and login not in self.racing:
			self.racing.append(login)
		self.phase = 'showdown' if self.count == 2 else 'racing'
		await self._refresh_overlays()

	async def on_player_removed(self, login):
		if login in self.racing:
			self.racing.remove(login)
		self.order = [e for e in self.order if e['login'] != login]
		await self._flash_elimination(login)
		await self._mark('eliminated', login)
		if self.count == 2 and self.phase != 'showdown':
			self.phase = 'showdown'
			await self._mark('showdown', '')
		elif self.count <= 1:
			self.phase = 'ended'
		await self._refresh_overlays()

	async def on_winner(self, login):
		self.phase = 'ended'
		await self._flash_winner(login)
		await self._mark('winner', login)
		await self._refresh_overlays()

	# ------------------------------------------------------- owned callbacks

	async def on_round_order(self, order=None, **kwargs):
		self.order = order or []
		# The mode only emits KOPlayerAdded at the start of a fresh match, so if
		# the plugin started/reloaded mid-match we never learned who is racing and
		# the phase is stuck at 'idle' (HUD/overlays hidden). KORoundOrder carries
		# the currently-racing logins every round, so seed the racing set from it
		# when we have none -- this lets the HUD self-heal a round or so in.
		if self.order and not self.racing and self.phase in ('idle', 'ended'):
			self.racing = [entry['login'] for entry in self.order]
			self.phase = 'showdown' if self.count == 2 else 'racing'
		await self._refresh_overlays()

	async def on_round_start(self, round=0, total=0, **kwargs):
		self.round = round
		self.total_rounds = total
		await self._refresh_overlays()

	async def on_shield_awarded(self, signal=None, **kwargs):
		login = _first_login(kwargs.get('player_login') or kwargs.get('login'))
		await self._flash_shield(login, awarded=True)
		await self._mark('shield_awarded', login)

	async def on_shield_used(self, signal=None, **kwargs):
		login = _first_login(kwargs.get('player_login') or kwargs.get('login'))
		await self._flash_shield(login, awarded=False)
		await self._mark('shield_used', login)

	# --------------------------------------------------------------- derived

	@property
	def danger_count(self):
		"""How many trailing players the mode will knock out this round."""
		if self._double_until and self.count > self._double_until:
			return 2
		return 1

	def danger_logins(self):
		"""
		Logins currently on the elimination bubble: the worst-ranked racing
		players who have not yet safely finished. Empty until KORoundOrder data
		arrives, or once the match has ended.
		"""
		if self.phase == 'ended' or not self.order:
			return []
		live = [e for e in self.order if e['login'] in self.racing and not e['finished']]
		if not live:
			return []
		live.sort(key=lambda e: e['rank'])
		return [e['login'] for e in live[-self.danger_count:]]

	# --------------------------------------------------------------- helpers

	async def _refresh_overlays(self):
		# Broadcast ticker (stream overlays, opt-in) and the always-on match HUD
		# are gated independently; refresh whichever is enabled.
		ticker = getattr(self.app, 'ticker', None)
		if getattr(self.app, '_overlays_enabled', False) and ticker is not None:
			try:
				await ticker.refresh(self)
			except Exception:
				logger.exception('Knockout: failed to refresh live ticker')

		hud = getattr(self.app, 'hud', None)
		if getattr(self.app, '_match_hud_enabled', False) and hud is not None:
			try:
				await hud.refresh(self)
			except Exception:
				logger.exception('Knockout: failed to refresh match HUD')

	async def _player_name(self, login):
		try:
			player = await self.instance.player_manager.get_player(login=login)
			return player.nickname
		except Exception:
			return login

	async def _flash_elimination(self, login):
		lower = self._lower_third()
		if lower is None:
			return
		name = await self._player_name(login)
		left = self.count
		await lower.flash('$f00❌ $fff{}$f00 knocked out — $fff{}$f00 left'.format(name, left))

	async def _flash_winner(self, login):
		lower = self._lower_third()
		if lower is None:
			return
		name = await self._player_name(login)
		await lower.flash('$0f0★ $fff{}$0f0 wins the round!'.format(name))

	async def _flash_shield(self, login, awarded):
		lower = self._lower_third()
		if lower is None or not login:
			return
		name = await self._player_name(login)
		if awarded:
			msg = '$09f\U0001f6e1 $fff{}$09f earned a shield!'.format(name)
		else:
			msg = '$09f\U0001f6e1 $fff{}$09f used a shield to survive!'.format(name)
		await lower.flash(msg)

	def _lower_third(self):
		if not getattr(self.app, '_overlays_enabled', False):
			return None
		return getattr(self.app, 'lower_third', None)

	async def _mark(self, event, login):
		markers = getattr(self.app, 'markers', None)
		if markers is None:
			return
		try:
			name = await self._player_name(login) if login else ''
			await markers.log(event, name or login)
		except Exception:
			logger.exception('Knockout: failed to log VOD marker')
