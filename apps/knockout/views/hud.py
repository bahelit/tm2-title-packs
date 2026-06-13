from pyplanet.views.template import TemplateView

from ..hud_format import format_race_time, row_color, round_label


class MatchHud(TemplateView):
	"""
	Always-on left-side match HUD shown to everyone (players and spectators)
	during a live Knockout match: the round number, how many players are still
	alive, how many get knocked out this round, and the running order with the
	players' times. The elimination-bubble player(s) are tinted red and safe
	finishers green. Driven by LiveController.refresh().
	"""

	template_name = 'knockout/hud.xml'

	def __init__(self, app):
		super().__init__(self)
		self.app = app
		self.manager = app.context.ui
		self.id = 'knockout__match_hud'
		self.round_text = 'KNOCKOUT'
		self.count = 0
		self.danger_count = 1
		self.rows = []

	async def get_context_data(self):
		data = await super().get_context_data()
		data['round_text'] = self.round_text
		data['count'] = self.count
		data['danger_count'] = self.danger_count
		data['rows'] = self.rows
		# Background height is precomputed here so the template never depends on
		# in-template float arithmetic (the header block is ~12 units tall).
		data['bg_height'] = 12 + len(self.rows) * 4
		return data

	async def refresh(self, live):
		"""Pull the current picture from the LiveController and (re)display, or
		hide the HUD when no match is being raced."""
		if live.phase in ('idle', 'ended') or live.count <= 0:
			await self.hide()
			return

		self.round_text = round_label(getattr(live, 'round', 0), getattr(live, 'total_rounds', 0))
		self.count = live.count
		self.danger_count = live.danger_count

		danger = set(live.danger_logins())
		# Prefer the live running order; before the first KORoundOrder arrives,
		# fall back to the racing set so the HUD still lists who is in.
		order = live.order or [
			dict(login=login, rank=index + 1, time=-1, finished=False)
			for index, login in enumerate(live.racing)
		]

		rows = []
		for entry in order:
			login = entry.get('login')
			if not login or login not in live.racing:
				continue
			rows.append(dict(
				y=-12 - len(rows) * 4,
				rank=entry.get('rank', len(rows) + 1),
				name=await self._name(login),
				time=format_race_time(entry.get('time', -1)),
				color=row_color(login in danger, entry.get('finished', False)),
			))
		self.rows = rows
		await self.display()

	async def _name(self, login):
		try:
			player = await self.app.instance.player_manager.get_player(login=login)
			return player.nickname
		except Exception:
			return login
