"""Local, optional mastery tracking. Never grants access to system controls."""
from __future__ import annotations
import json
import time
from .core import Store, STATE, OperationError

COMPANIONS = (
    ('steve', 'Steve', 'Minecraft', 'Give your next Minecraft world some breathing room.'),
    ('alex', 'Alex', 'Minecraft', 'Prepare your desktop for the next build, cave, or adventure.'),
    ('jonesy', 'Jonesy', 'Fortnite', 'Your pre-game checkpoint, with Jonesy on your side.'),
    ('peely', 'Peely', 'Fortnite', 'A little less background activity. A little more Peely.'),
    ('jett', 'Jett', 'VALORANT', 'Keep your setup deliberate. Every change gets a review.'),
    ('sage', 'Sage', 'VALORANT', 'Prepare your session. Bring your desktop back safely.'),
    ('phoenix', 'Phoenix', 'VALORANT', 'Your next session starts with a clean plan.'),
    ('reyna', 'Reyna', 'VALORANT', 'Choose your changes. Stay in control of your setup.'),
)
# Display-only framing of the unchanged source artwork (normalized x/y/width/height).
CHARACTER_FRAMING = {
    'steve': (0.34, 0.0, 0.64, 0.47),
    'alex': (0.34, 0.0, 0.64, 0.47),
}
LEGACY_CHARACTERS = {'moss': 'steve', 'byte': 'alex', 'nova': 'reyna'}

THEMES = ('emerald', 'amber', 'teal', 'violet')
MILESTONES = (
    ('scan', 'Scout', 'Complete your first system scan.', 'Find what is running before changing it.'),
    ('review', 'Planner', 'Open a valid change review.', 'Inspect the exact targets and their risks.'),
    ('shortcut', 'Quick hands', 'Use Ctrl+F or Ctrl+R.', 'Learn a shortcut for a useful everyday action.'),
    ('restore', 'Safe return', 'Complete and restore one session.', 'A successful recovery is part of every session.'),
    ('five_restores', 'Steward', 'Complete and restore five sessions.', 'Build a habit of leaving your desktop as you found it.'),
)


def defaults():
    return {'schema': 1, 'companion': 'steve', 'theme': 'emerald', 'professional': False,
            'sound': False, 'reduced_motion': False, 'custom_avatar': False,
            'milestones': {}, 'sessions': {}}


class Profile(Store):
    def __init__(self, directory=STATE):
        super().__init__(directory)
        self.path = self.directory / 'profile.json'
        # Keep profile locking independent from the recovery lock.

    def lock(self):
        import contextlib
        import fcntl
        @contextlib.contextmanager
        def locked():
            with (self.directory / 'profile.lock').open('a') as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                yield
        return locked()

    def read(self):
        if not self.path.exists():
            return defaults()
        try:
            value = json.loads(self.path.read_text())
            if not isinstance(value, dict) or value.get('schema') != 1:
                raise ValueError('unsupported profile format')
            result = defaults()
            result.update({k: v for k, v in value.items() if k in result})
            result['companion'] = LEGACY_CHARACTERS.get(result['companion'], result['companion'])
            if result['companion'] not in {c[0] for c in COMPANIONS} or result['theme'] not in THEMES:
                raise ValueError('unknown companion or theme')
            for key in ('sound', 'professional', 'reduced_motion', 'custom_avatar'):
                if type(result[key]) is not bool:
                    raise ValueError(f'invalid {key} preference')
            if not isinstance(result['milestones'], dict) or not isinstance(result['sessions'], dict):
                raise ValueError('invalid progress records')
            for record in result['sessions'].values():
                if not isinstance(record, dict) or not isinstance(record.get('completed'), (int, float)):
                    raise ValueError('invalid session history')
            return result
        except (ValueError, OSError, TypeError) as exc:
            raise OperationError(f'Profile unavailable; system controls still work. Preserve profile.json for diagnosis: {exc}') from exc

    def preference(self, key, value):
        with self.lock():
            state = self.read()
            if key in ('professional', 'sound', 'reduced_motion', 'custom_avatar'):
                if type(value) is not bool:
                    raise ValueError('Expected a boolean preference')
            elif key == 'companion':
                if value not in {c[0] for c in COMPANIONS}:
                    raise ValueError('Unknown companion')
            elif key == 'theme':
                if value not in unlocked_themes(state):
                    raise ValueError('Theme milestone has not been reached')
            else:
                raise ValueError('Unknown preference')
            state[key] = value
            self.write(state)
            return state

    def award(self, name):
        if name not in ('scan', 'review', 'shortcut'):
            raise ValueError('Session milestones require a completed recovery')
        with self.lock():
            state = self.read()
            if name in state['milestones']:
                return []
            state['milestones'][name] = time.time()
            self.write(state)
            return [name]

    def completed(self, session):
        # Failed applies/rollbacks and empty timer probes are not achievements.
        if (session.get('status') != 'restored' or not session.get('activation_complete') or
                not session.get('actions') or
                any(a.get('status') != 'restored' for a in session['actions'])):
            return []
        with self.lock():
            state = self.read()
            session_id = session['id']
            if session_id in state['sessions']:
                return []
            now = session.get('completed_at', time.time())
            state['sessions'][session_id] = {'started': session.get('started', now), 'completed': now}
            earned = []
            for name, threshold in (('restore', 1), ('five_restores', 5)):
                if len(state['sessions']) >= threshold and name not in state['milestones']:
                    state['milestones'][name] = now
                    earned.append(name)
            self.write(state)
            return earned


def unlocked_themes(state):
    milestones = state['milestones']
    return ['emerald'] + [theme for milestone, theme in
        (('scan', 'amber'), ('review', 'teal'), ('restore', 'violet')) if milestone in milestones]


def tier(state):
    count = sum(m[0] in state['milestones'] for m in MILESTONES)
    return 'Steward' if count >= 4 else 'Planner' if count >= 2 else 'Explorer'
