import logging

from pyplanet.contrib.command import Command

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
			Command(command='status', namespace='cup', target=self.cmd_status, admin=False,
				description='Show the active cup status.'),
			Command(command='results', namespace='cup', target=self.cmd_results, admin=False,
				description='Show the cup standings.'),
		)

	# ------------------------------------------------------------------- admin

	async def cmd_on(self, player, data, **kwargs):
		name = ' '.join(data.name).strip() if getattr(data, 'name', None) else None
		cup = await self.cup.start_cup(cup_key=data.key, name=name)
		await self.instance.chat(
			'$ff0>>> $fff{}$ff0 started a cup: $fff{}$ff0 (edition {}).'.format(
				player.nickname, cup.name, cup.edition)
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
