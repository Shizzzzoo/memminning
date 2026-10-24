import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from memminning.core import Engine, OperationError, Store
from memminning.progress import Profile, defaults, tier, unlocked_themes
from test_core import FakeBackend, EXT


def restored_session(identifier='one', **changes):
    result = {'id': identifier, 'status': 'restored', 'activation_complete': True,
              'started': 100, 'completed_at': 200,
              'actions': [{'status': 'restored', 'kind': 'gnome', 'action': 'disable', 'target': EXT}]}
    result.update(changes)
    return result


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.profile = Profile(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_legacy_character_selection_preserves_progress(self):
        state = defaults()
        state.update(companion='byte', professional=True, sound=True)
        state['milestones'] = {'scan': 123}
        self.profile.write(state)
        restored = self.profile.read()
        self.assertEqual(restored['companion'], 'alex')
        self.assertEqual(restored['milestones'], {'scan': 123})
        self.assertTrue(restored['professional'])
        self.assertTrue(restored['sound'])
        self.profile.preference('companion', 'jett')
        self.assertEqual(Profile(self.temp.name).read()['companion'], 'jett')

    def test_defaults_are_quiet_and_controls_are_not_locked(self):
        data = self.profile.read()
        self.assertFalse(data['sound'])
        self.assertFalse(data['custom_avatar'])
        self.assertEqual(unlocked_themes(data), ['emerald'])
        self.assertEqual(tier(data), 'Explorer')

    def test_awards_are_one_time(self):
        self.assertEqual(self.profile.award('scan'), ['scan'])
        for _ in range(5):
            self.assertEqual(self.profile.award('scan'), [])
        self.assertEqual(len(self.profile.read()['milestones']), 1)

    def test_only_cosmetic_rewards_unlock(self):
        self.profile.award('scan')
        self.assertEqual(unlocked_themes(self.profile.read()), ['emerald', 'amber'])
        self.profile.award('review')
        self.assertIn('teal', unlocked_themes(self.profile.read()))
        self.assertEqual(tier(self.profile.read()), 'Planner')
        with self.assertRaises(ValueError):
            self.profile.preference('theme', 'violet')
        self.profile.completed(restored_session())
        self.profile.preference('theme', 'violet')
        self.assertEqual(self.profile.read()['theme'], 'violet')

    def test_complete_sessions_count_once_and_persist(self):
        self.assertEqual(self.profile.completed(restored_session()), ['restore'])
        for _ in range(4):
            self.assertEqual(self.profile.completed(restored_session()), [])
        self.assertEqual(len(Profile(self.temp.name).read()['sessions']), 1)

    def test_five_safe_returns(self):
        for i in range(4):
            self.profile.completed(restored_session(str(i)))
        self.assertNotIn('five_restores', self.profile.read()['milestones'])
        self.assertEqual(self.profile.completed(restored_session('4')), ['five_restores'])

    def test_failed_apply_recovery_empty_timer_and_errors_do_not_count(self):
        for changes in ({'activation_complete': False}, {'status': 'active'},
                        {'status': 'recovery-needed'}, {'actions': []},
                        {'actions': [{'status': 'error'}]}):
            with self.subTest(changes=changes):
                self.assertEqual(self.profile.completed(restored_session(**changes)), [])
        self.assertFalse(self.profile.read()['sessions'])

    def test_session_achievement_cannot_be_directly_awarded(self):
        for name in ('restore', 'five_restores', 'fake'):
            with self.assertRaises(ValueError):
                self.profile.award(name)

    def test_preferences_are_persisted_and_validated(self):
        for key, value in [('professional', True), ('sound', True), ('reduced_motion', True), ('companion', 'reyna')]:
            self.profile.preference(key, value)
            self.assertEqual(Profile(self.temp.name).read()[key], value)
        for key, value in [('professional', 'yes'), ('companion', 'unknown'), ('execute', '/bin/sh')]:
            with self.assertRaises(ValueError):
                self.profile.preference(key, value)

    def test_corrupt_profile_is_preserved(self):
        self.profile.path.write_text('not json')
        with self.assertRaises(OperationError):
            self.profile.preference('sound', True)
        self.assertEqual(self.profile.path.read_text(), 'not json')

    def test_progress_is_private_and_separate_from_recovery(self):
        recovery = Store(self.temp.name)
        recovery.write({'schema': 1, 'status': 'active', 'actions': []})
        original = recovery.path.read_text()
        self.profile.award('scan')
        self.assertEqual(recovery.path.read_text(), original)
        self.assertEqual(self.profile.path.stat().st_mode & 0o777, 0o600)

    def test_engine_restoration_records_progress_without_gui(self):
        engine = Engine(FakeBackend(), Store(self.temp.name))
        engine.begin([(f'gnome:{EXT}', 'disable')], 5)
        self.assertEqual(engine.restore(), [])
        self.assertIn('restore', self.profile.read()['milestones'])
        self.assertEqual(len(self.profile.read()['sessions']), 1)
        engine.restore()
        self.assertEqual(len(self.profile.read()['sessions']), 1)

    def test_profile_write_failure_never_blocks_restoration(self):
        backend = FakeBackend()
        engine = Engine(backend, Store(self.temp.name))
        engine.begin([(f'gnome:{EXT}', 'disable')], 5)
        with patch.object(Profile, 'completed', side_effect=OSError('disk full')):
            self.assertEqual(engine.restore(), [])
        self.assertIn(EXT, backend.enabled)
        self.assertEqual(engine.store.read()['status'], 'restored')

    def test_failed_begin_does_not_create_progress(self):
        backend = FakeBackend()
        backend.fail_disable = True
        engine = Engine(backend, Store(self.temp.name))
        with self.assertRaises(OperationError):
            engine.begin([(f'gnome:{EXT}', 'disable')], 5)
        self.assertEqual(self.profile.read()['sessions'], {})


if __name__ == '__main__':
    unittest.main()
