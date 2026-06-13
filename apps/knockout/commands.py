import logging

from pyplanet.contrib.command import Command

from . import payouts

logger = logging.getLogger(__name__)


class CupCommands:
	"""Registers the //cup admin commands and the /cup public commands."""

	def __init__(self, app):
		self.app = app
		self.instance = app.instance

	@property
	def cup(self):
		return self.app.cup

	async def on_start(self):
		await self.instance.command_manager.register(
			Command(command='on', namespace='cup', target=self.cmd_on, admin=True,
				description='Start a Knockout cup.')
				.add_param(name='key', required=False, default='cup', help='Cup key / preset id.')
				.add_param(name='name', required=False, nargs='*', help='Display name (optional).'),
			Command(command='off', namespace='cup', target=self.cmd_off, admin=True,
				description='Stop the active cup.'),
			Command(command='mapcount', namespace='cup', target=self.cmd_mapcount, admin=True,
				description='Set the number of maps in the cup (0 = open-ended).')
				.add_param(name='count', required=True, type=int),
			Command(command='edition', namespace='cup', target=self.cmd_edition, admin=True,
				description='Set the cup edition number.')
				.add_param(name='edition', required=True, type=int),
			Command(command='scoremode', namespace='cup', target=self.cmd_scoremode, admin=True,
				description='Set the points-by-placement table.')
				.add_param(name='mode', required=True),
			Command(command='setup', namespace='cup', target=self.cmd_setup, admin=True,
				description='Apply a mode/settings preset to the server.')
				.add_param(name='preset', required=True),
			Command(command='pay', namespace='cup', target=self.cmd_pay, admin=True,
				description='Pay planets to the cup standings (must be enabled).')
				.add_param(name='payout', required=False),
			Command(command='status', namespace='cup', target=self.cmd_status, admin=False,
				description='Show the active cup status.'),
			Command(command='results', namespace='cup', target=self.cmd_results, admin=False,
				description='Show the cup standings.'),
		)

	# ------------------------------------------------------------------- admin

	async def cmd_on(self, player, data, **kwargs):
		explicit_name = ' '.join(data.name).strip() if getattr(data, 'name', None) else None

		# Pull defaults from a named cup definition in the presets file, if any.
		cup_cfg = self.app.presets.get_cup(data.key) or {}
		name = explicit_name or cup_cfg.get('name')
		map_count = int(cup_cfg.get('mapcount', 0) or 0)
		score_mode = cup_cfg.get('scoremode')
		if not score_mode:
			score_mode = await self.app.setting_default_score_mode.get_value()

		cup = await self.cup.start_cup(
			cup_key=data.key, name=name, map_count=map_count, score_mode=score_mode,
		)
		await self.instance.chat(
			'$ff0>>> $fff{}$ff0 started a cup: $fff{}$ff0 (edition {}, {}).'.format(
				player.nickname, cup.name, cup.edition,
				'{} maps'.format(map_count) if map_count else 'open-ended')
		)

	async def cmd_off(self, player, data, **kwargs):
		cup = await self.cup.stop_cup()
		if cup:
			await self.instance.chat('$ff0>>> Cup $fff{}$ff0 stopped.'.format(cup.name))
		else:
			await self.instance.chat('$f00>>> No active cup.', player)

	async def cmd_mapcount(self, player, data, **kwargs):
		if not await self.cup.set_map_count(data.count):
			await self.instance.chat('$f00>>> No active cup.', player)
			return
		await self.instance.chat('$ff0>>> Cup map count set to $fff{}$ff0.'.format(data.count))

	async def cmd_edition(self, player, data, **kwargs):
		if not await self.cup.set_edition(data.edition):
			await self.instance.chat('$f00>>> No active cup.', player)
			return
		await self.instance.chat('$ff0>>> Cup edition set to $fff{}$ff0.'.format(data.edition))

	async def cmd_scoremode(self, player, data, **kwargs):
		if not await self.cup.set_score_mode(data.mode):
			await self.instance.chat('$f00>>> No active cup.', player)
			return
		await self.instance.chat('$ff0>>> Cup score mode set to $fff{}$ff0.'.format(data.mode))

	async def cmd_setup(self, player, data, **kwargs):
		preset = self.app.presets.get_preset(data.preset)
		if not preset:
			await self.instance.chat('$f00>>> Unknown preset "{}".'.format(data.preset), player)
			return
		script = preset.get('script')
		settings = preset.get('settings') or {}
		if script:
			await self.instance.mode_manager.set_next_script(script)
		if settings:
			await self.instance.mode_manager.update_settings(settings)
		await self.instance.chat(
			'$ff0>>> Applied preset $fff{}$ff0 ({} setting(s)){}.'.format(
				data.preset, len(settings),
				' — new script loads on next map' if script else '')
		)

	async def cmd_pay(self, player, data, **kwargs):
		if not await self.app.setting_payouts_enabled.get_value():
			await self.instance.chat(
				'$f00>>> Cup payouts are disabled (enable the cup_payouts_enabled setting).', player)
			return

		cup = self.cup.active_cup or await self.cup.last_cup()
		if not cup:
			await self.instance.chat('$f00>>> No cup to pay out.', player)
			return

		payout_key = data.payout if getattr(data, 'payout', None) else None
		if not payout_key:
			payout_key = (self.app.presets.get_cup(cup.cup_key) or {}).get('payout')
		amounts = self.app.presets.get_payout(payout_key) if payout_key else []
		if not amounts:
			await self.instance.chat(
				'$f00>>> No payout "{}" configured.'.format(payout_key), player)
			return

		standings = await self.app.results.compute_standings(cup)
		plan = payouts.plan_payout(standings, amounts)
		if not plan:
			await self.instance.chat('$f00>>> Nothing to pay.', player)
			return

		paid = await payouts.pay_planets(self.instance, plan, label='{} payout'.format(cup.name))
		await self.instance.chat(
			'$ff0>>> Paid $fff{}$ff0 of {} player(s) for cup $fff{}$ff0.'.format(
				len(paid), len(plan), cup.name)
		)

	# ------------------------------------------------------------------ public

	async def cmd_status(self, player, data, **kwargs):
		cup = self.cup.active_cup
		if not cup:
			await self.instance.chat('$bbb>>> No cup is currently active.', player)
			return
		matches = await self.cup.cup_matches()
		target = '{} / {}'.format(len(matches), cup.map_count) if cup.map_count else str(len(matches))
		await self.instance.chat(
			'$bbb>>> Cup $fff{}$bbb (edition {}) — maps played: $fff{}$bbb, score mode: $fff{}$bbb.'.format(
				cup.name, cup.edition, target, cup.score_mode),
			player,
		)

	async def cmd_results(self, player, data, **kwargs):
		results = getattr(self.app, 'results', None)
		if results is None:
			await self.instance.chat('$bbb>>> Cup results are not available yet.', player)
			return
		await results.show(player)
