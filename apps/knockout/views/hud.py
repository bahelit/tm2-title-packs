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
		"""Pull the current picture from the LiveController and (re)display. The HUD
		stays up for the whole Knockout: during warm-up it lists the players on the
		server with their best lap so far; once rounds start it switches to the live
		running order with elimination highlighting. It only hides when the loaded
		mode is not Knockout, or when nobody is on the server to show."""
		if not getattr(live, 'is_knockout', True):
			await self.hide()
			return

		self.round_text = round_label(getattr(live, 'round', 0), getattr(live, 'total_rounds', 0))
		self.danger_count = live.danger_count
		danger = set(live.danger_logins())

		rows = []

		async def add(rank, login, time_ms, finished):
			rows.append(dict(
				y=-12 - len(rows) * 4,
				rank=rank,
				name=await self._name(login),
				time=format_race_time(time_ms),
				color=row_color(login in danger, finished),
			))

		if live.order:
			# Live round order carries live times and finished flags.
			for entry in live.order:
				login = entry.get('login')
				if not login or login not in live.racing:
					continue
				await add(entry.get('rank', len(rows) + 1), login,
					entry.get('time', -1), entry.get('finished', False))
		else:
			# Warm-up / pre-round: roster from the server, best lap so far, fastest
			# first (players without a lap yet sort to the bottom).
			logins = await live.roster_logins()
			logins.sort(key=lambda lg: (live.best_time(lg) < 0, live.best_time(lg)))
			for login in logins:
				await add(len(rows) + 1, login, live.best_time(login), False)

		self.rows = rows
		# "alive" reflects the racing count once a round is on; in warm-up it is the
		# number of players currently listed.
		self.count = live.count if live.racing else len(rows)

		if not rows:
			await self.hide()
			return
		await self.display()

	async def _name(self, login):
		try:
			player = await self.app.instance.player_manager.get_player(login=login)
			return player.nickname
		except Exception:
			return login

	async def show_test(self, player=None):
		"""Force-render the HUD with placeholder rows, ignoring match state. Used
		by the //ko hud diagnostic to confirm the manialink renders at all. Shown
		only to ``player`` when given, otherwise to everyone (the real path)."""
		self.round_text = 'ROUND 1 / 5'
		self.count = 2
		self.danger_count = 1
		self.rows = [
			dict(y=-12, rank=1, name='Test A', time='0.000', color='66FF66'),
			dict(y=-16, rank=2, name='Test B', time='—', color='FF3333'),
		]
		if player is not None:
			await self.display(player=player)
		else:
			await self.display()
