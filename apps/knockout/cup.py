import logging

from .models import CupInfo, CupMatch

logger = logging.getLogger(__name__)


class CupController:
	"""
	Owns the active-cup lifecycle and links finished matches to the active cup.
	State is persisted, so an active cup survives a PyPlanet restart.
	"""

	def __init__(self, app):
		self.app = app
		self.instance = app.instance
		self.active_cup = None

	async def on_start(self):
		rows = list(await CupInfo.execute(
			CupInfo.select().where(CupInfo.is_active == True).order_by(CupInfo.id.desc())
		))
		self.active_cup = rows[0] if rows else None
		if self.active_cup:
			logger.info('Knockout: resumed active cup "%s" (edition %s)',
				self.active_cup.name, self.active_cup.edition)

	# ---------------------------------------------------------------- lifecycle

	async def start_cup(self, cup_key, name=None, map_count=0, score_mode='default', mode_script=None):
		# Only one active cup at a time; close any existing one first.
		if self.active_cup:
			await self.stop_cup()

		# Continue the edition counter from the most recent cup with this key.
		previous = list(await CupInfo.execute(
			CupInfo.select().where(CupInfo.cup_key == cup_key).order_by(CupInfo.edition.desc())
		))
		edition = (previous[0].edition + 1) if previous else 1

		cup = CupInfo(
			cup_key=cup_key,
			name=name or cup_key,
			edition=edition,
			map_count=map_count,
			score_mode=score_mode,
			mode_script=mode_script,
			is_active=True,
		)
		await cup.save()
		self.active_cup = cup
		logger.info('Knockout: started cup "%s" edition %s (map_count=%s)', cup.name, edition, map_count)
		return cup

	async def stop_cup(self):
		if not self.active_cup:
			return None
		cup = self.active_cup
		cup.is_active = False
		await cup.save()
		self.active_cup = None
		logger.info('Knockout: stopped cup "%s"', cup.name)
		return cup

	async def set_map_count(self, count):
		if not self.active_cup:
			return False
		self.active_cup.map_count = max(0, int(count))
		await self.active_cup.save()
		return True

	async def set_edition(self, edition):
		if not self.active_cup:
			return False
		self.active_cup.edition = int(edition)
		await self.active_cup.save()
		return True

	async def set_score_mode(self, score_mode):
		if not self.active_cup:
			return False
		self.active_cup.score_mode = score_mode
		await self.active_cup.save()
		return True

	# ------------------------------------------------------------------ matches

	async def last_cup(self):
		"""Return the most recently created cup (active or not), or None."""
		rows = list(await CupInfo.execute(
			CupInfo.select().order_by(CupInfo.id.desc())
		))
		return rows[0] if rows else None

	async def cup_matches(self, cup=None):
		"""Return the CupMatch rows for a cup, ordered by map index."""
		cup = cup or self.active_cup
		if not cup:
			return []
		return list(await CupMatch.execute(
			CupMatch.select().where(CupMatch.cup == cup.id).order_by(CupMatch.map_index)
		))

	async def on_match_recorded(self, map_start_time, standings):
		"""Called by capture after a map's standings are stored."""
		if not self.active_cup:
			return

		existing = await self.cup_matches()
		if any(match.map_start_time == map_start_time for match in existing):
			return

		index = len(existing)
		await CupMatch.execute(CupMatch.insert(
			cup=self.active_cup.id,
			map_start_time=map_start_time,
			map_index=index,
			counts=True,
		))
		played = index + 1

		target = self.active_cup.map_count
		progress = '{} / {}'.format(played, target) if target else str(played)
		await self.instance.chat(
			'$ff0>>> $fffCup {}$ff0 — map {} recorded.'.format(self.active_cup.name, progress)
		)

		if target and played >= target:
			await self.complete_cup()

	async def complete_cup(self):
		cup = self.active_cup
		if not cup:
			return
		await self.stop_cup()
		await self.instance.chat('$0f0>>> $fffCup {}$0f0 complete!'.format(cup.name))
		# Final standings window is shown by the results controller (Phase 4).
		on_complete = getattr(self.app, 'on_cup_complete', None)
		if on_complete:
			await on_complete(cup)
