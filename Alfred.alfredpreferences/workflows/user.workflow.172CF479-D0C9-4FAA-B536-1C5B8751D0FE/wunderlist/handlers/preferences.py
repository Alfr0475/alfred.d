# encoding: utf-8

from wunderlist.models.user import User
from wunderlist.models.preferences import Preferences
from wunderlist.util import workflow, parsedatetime_calendar, parsedatetime_constants, format_time, update_prerelease_channel
from wunderlist import icons

def _parse_time(phrase):
	from datetime import date, time

	cal = parsedatetime_calendar()

	# Use a sourceTime so that time expressions are relative to 00:00:00
	# rather than the current time
	datetime_info = cal.parse(phrase, sourceTime=date.today().timetuple())

	# Ensure that only a time was provided and not a date
	if datetime_info[1] == 2:
		return time(*datetime_info[0][3:5])
	return None

def _format_time_offset(t):
	if t is None:
		return 'disabled'

	offset = []

	if t.hour > 0:
		offset.append('%sh' % t.hour)
	if t.minute > 0:
		offset.append('%sm' % t.minute)

	return ' '.join(offset)

def filter(args):
	prefs = Preferences.current_prefs()

	if 'reminder' in args:
		reminder_time = _parse_time(' '.join(args))

		if reminder_time is not None:
			workflow().add_item(
				'Change default reminder time',
				u'⏰ %s' % format_time(reminder_time, 'short'),
				arg=' '.join(args), valid=True, icon=icons.REMINDER
			)
		else:
			workflow().add_item(
				'Type a new reminder time',
				'Date offsets like the morning before the due date are not supported yet',
				valid=False, icon=icons.REMINDER
			)

		workflow().add_item(
			'Cancel',
			autocomplete=':pref', icon=icons.BACK
		)
	elif 'reminder_today' in args:
		reminder_today_offset = _parse_time(' '.join(args))

		if reminder_today_offset is not None:
			workflow().add_item(
				'Set a custom reminder offset',
				u'⏰ now + %s' % _format_time_offset(reminder_today_offset),
				arg=' '.join(args), valid=True, icon=icons.REMINDER
			)
		else:
			workflow().add_item(
				'Type a custom reminder offset',
				'Use the formats hh:mm or 2h 5m',
				valid=False, icon=icons.REMINDER
			)

		workflow().add_item(
			'30 minutes',
			arg=':pref reminder_today 30m', valid=True, icon=icons.REMINDER
		)

		workflow().add_item(
			'1 hour',
			'(default)',
			arg=':pref reminder_today 1h', valid=True, icon=icons.REMINDER
		)

		workflow().add_item(
			'90 minutes',
			arg=':pref reminder_today 90m', valid=True, icon=icons.REMINDER
		)

		workflow().add_item(
			'Always use the default reminder time',
			'Avoids adjusting the reminder based on the current date',
			arg=':pref reminder_today disabled', valid=True, icon=icons.CANCEL
		)

		workflow().add_item(
			'Cancel',
			autocomplete=':pref', icon=icons.BACK
		)
	else:
		current_user = User.get()

		if current_user and current_user.name:
			workflow().add_item(
				'Sign out',
				'You are logged in as ' + current_user.name,
				autocomplete=':logout', icon=icons.CANCEL
			)

		workflow().add_item(
			'Default reminder time',
			u'⏰ %s    Reminders without a specific time will be set to this time' % format_time(prefs.reminder_time, 'short'),
			autocomplete=':pref reminder ', icon=icons.REMINDER
		)

		workflow().add_item(
			'Default reminder when due today',
			u'⏰ %s    Default reminder time for tasks due today is %s' % (_format_time_offset(prefs.reminder_today_offset), 'relative to the current time' if prefs.reminder_today_offset else 'always %s' % format_time(prefs.reminder_time, 'short')),
			autocomplete=':pref reminder_today ', icon=icons.REMINDER
		)

		workflow().add_item(
			'Automatically set a reminder on the due date',
			u'Sets a default reminder for tasks with a due date.',
			arg=':pref automatic_reminders', valid=True, icon=icons.TASK_COMPLETED if prefs.automatic_reminders else icons.TASK
		)

		workflow().add_item(
			'Require explicit due keyword',
			'Requires the due keyword to avoid accidental due date extraction',
			arg=':pref explicit_keywords', valid=True, icon=icons.TASK_COMPLETED if prefs.explicit_keywords else icons.TASK
		)

		workflow().add_item(
			'Check for experimental updates to this workflow',
			'The workflow automatically checks for updates; enable this to include pre-releases',
			arg=':pref prerelease_channel', valid=True, icon=icons.TASK_COMPLETED if prefs.prerelease_channel else icons.TASK
		)

		workflow().add_item(
			'Force sync',
			'The workflow syncs automatically, but feel free to be forcible.',
			arg=':pref sync', valid=True, icon=icons.SYNC
		)

		workflow().add_item(
			'Switch theme',
			'Toggle between light and dark icons',
			arg=':pref retheme',
			valid=True,
			icon=icons.PAINTBRUSH
		)

		workflow().add_item(
			'Main menu',
			autocomplete='', icon=icons.BACK
		)

def commit(args):
	prefs = Preferences.current_prefs()
	relaunch_alfred = False

	if 'sync' in args:
		from wunderlist.sync import sync
		sync()
	elif 'explicit_keywords' in args:
		relaunch_alfred = True

		prefs.explicit_keywords = not prefs.explicit_keywords

		if prefs.explicit_keywords:
			print 'Remember to use the "due" keyword'
		else:
			print 'Implicit due dates enabled (e.g. "Recycling tomorrow")'
	elif 'reminder' in args:
		relaunch_alfred = True
		reminder_time = _parse_time(' '.join(args))

		if reminder_time is not None:
			prefs.reminder_time = reminder_time

			print 'Reminders will now default to %s' % format_time(reminder_time, 'short')
	elif 'reminder_today' in args:
		relaunch_alfred = True
		reminder_today_offset = None

		if not ('disabled' in args):
			reminder_today_offset = _parse_time(' '.join(args))

		prefs.reminder_today_offset = reminder_today_offset

		print 'The offset for current-day reminders is now %s' % _format_time_offset(reminder_today_offset)
	elif 'automatic_reminders' in args:
		relaunch_alfred = True

		prefs.automatic_reminders = not prefs.automatic_reminders

		if prefs.automatic_reminders:
			print 'A reminder will automatically be set for due tasks'
		else:
			print 'A reminder will not be added automatically'
	elif 'retheme' in args:
		relaunch_alfred = True
		prefs.icon_theme = 'light' if icons.icon_theme() == 'dark' else 'dark'

		print 'The workflow is now using the %s icon theme' % (prefs.icon_theme)
	elif 'prerelease_channel' in args:
		relaunch_alfred = True

		prefs.prerelease_channel = not prefs.prerelease_channel

		# Update the workflow settings and reverify the update data
		update_prerelease_channel()
		workflow().check_update(True)

		if prefs.prerelease_channel:
			print 'The workflow will prompt you to update to experimental pre-releases'
		else:
			print 'The workflow will only prompt you to update to final releases'
	if relaunch_alfred:
		import subprocess
		subprocess.call(['/usr/bin/env', 'osascript', 'bin/launch_alfred.scpt', 'wl:pref'])
