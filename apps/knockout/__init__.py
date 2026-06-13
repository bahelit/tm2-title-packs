from pyplanet.apps.config import AppConfig
from pyplanet.core.events import Callback, Signal
from pyplanet.contrib.setting import Setting
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals

from .capture import CaptureController
from .cup import CupController
from .commands import CupCommands
from .models import MatchInfo, PlayerScore, CupInfo, CupMatch  # noqa: F401  (registers tables)


# Custom scripted callbacks for Knockout
knockout_callbacks = [
	Callback(
		call='ModeScriptCallback',
		namespace='script',
		code='KOPlayerAdded',
	),
	Callback(
		call='ModeScriptCallback',
		namespace='script',
		code='KOPlayerRemoved',
	),
	Callback(
		call='ModeScriptCallback',
		namespace='script',
		code='KOSendWinner',
	),
]


class KnockoutConfig(AppConfig):
	game_dependencies = ['trackmania']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setting_notifications = Setting(
			'notifications',
			'Enable Chat Notifications',
			Setting.CAT_BEHAVIOUR,
			type=bool,
			description='Send chat notifications for Knockout events',
			default=True,
		)
		self.setting_show_join = Setting(
			'show_join',
			'Show Player Join Notifications',
			Setting.CAT_BEHAVIOUR,
			type=bool,
			description='Notify when players join Knockout',
			default=True,
		)
		self.setting_show_knockout = Setting(
			'show_knockout',
			'Show Knockout Notifications',
			Setting.CAT_BEHAVIOUR,
			type=bool,
			description='Notify when players are knocked out',
			default=True,
		)
		self.setting_show_winner = Setting(
			'show_winner',
			'Show Winner Notifications',
			Setting.CAT_BEHAVIOUR,
			type=bool,
			description='Notify when a match winner is determined',
			default=True,
		)

	async def on_init(self):
		await self.context.setting.register(
			self.setting_notifications,
			self.setting_show_join,
			self.setting_show_knockout,
			self.setting_show_winner,
		)

	async def on_start(self):
		for cb in knockout_callbacks:
			self.context.signals.register_signal(cb)
			self.context.signals.listen('script:{}'.format(cb.code), self.handle_knockout_callback)

		self._match_winner = None

		# Cup controllers: state machine, score capture, and commands.
		self.cup = CupController(self)
		await self.cup.on_start()

		self.capture = CaptureController(self)
		await self.capture.on_start()

		self.commands = CupCommands(self)
		await self.commands.on_start()

	async def on_match_recorded(self, map_start_time, standings):
		"""Called by capture after a finished map's standings are persisted."""
		await self.cup.on_match_recorded(map_start_time, standings)

	async def handle_knockout_callback(self, signal, **kwargs):
		enabled = await self.setting_notifications.get_value()
		if not enabled:
			return

		code = signal.code
		payload = kwargs.get('player_login') or kwargs.get('login')

		if code == 'KOPlayerAdded':
			await self._handle_player_added(payload)
		elif code == 'KOPlayerRemoved':
			await self._handle_player_removed(payload)
		elif code == 'KOSendWinner':
			await self._handle_winner(payload)

	async def _resolve_player_name(self, login):
		try:
			player = await self.instance.get_player(login=login)
			return player.name
		except Exception:
			return login

	async def _handle_player_added(self, payload):
		show_join = await self.setting_show_join.get_value()
		if not show_join:
			return

		login = payload[0] if isinstance(payload, (list, tuple)) and len(payload) > 0 else str(payload)
		name = await self._resolve_player_name(login)
		msg = '$f90>>> $fff{name} $f90joined Knockout!'.format(name=name)
		await self.instance.chat(msg)

	async def _handle_player_removed(self, payload):
		show_knockout = await self.setting_show_knockout.get_value()
		if not show_knockout:
			return

		login = payload[0] if isinstance(payload, (list, tuple)) and len(payload) > 0 else str(payload)
		name = await self._resolve_player_name(login)
		msg = '$f00>>> $fff{name} $f00was knocked out!'.format(name=name)
		await self.instance.chat(msg)

	async def _handle_winner(self, payload):
		show_winner = await self.setting_show_winner.get_value()
		if not show_winner:
			return

		login = payload[0] if isinstance(payload, (list, tuple)) and len(payload) > 0 else str(payload)
		name = await self._resolve_player_name(login)
		self._match_winner = login
		msg = '$0f0>>> $fff{name} $0f0is the winner!'.format(name=name)
		await self.instance.chat(msg)
