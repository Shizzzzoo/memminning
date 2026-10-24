import json
import logging
logging.getLogger("memminning").addHandler(logging.NullHandler())
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from memminning.core import Engine, Item, OperationError, Snapshot, Store, extension_allowed, export_report, service_reason

TARGET = 'localsearch-3.service'
EXT = 'wallpaper@example.org'


class FakeBackend:
    def __init__(self):
        self.enabled = {EXT}
        self.props = {'Id': TARGET, 'LoadState': 'loaded', 'ActiveState': 'active',
                      'MemoryHigh': 'infinity', 'RequiredBy': '', 'BoundBy': '', 'TriggeredBy': ''}
        self.calls = []
        self.boot_id = 'boot-a'
        self.fail_arm = False
        self.fail_disable = False
        self.fail_enable = False
        self.fail_limit_after_change = False

    def extensions(self):
        return self.enabled.copy()

    def extension(self, target, enabled):
        self.calls.append(('extension', target, enabled))
        if (enabled and self.fail_enable) or (not enabled and self.fail_disable):
            raise OperationError('injected extension failure')
        if enabled:
            self.enabled.add(target)
        else:
            self.enabled.discard(target)

    def service(self, target):
        return self.props.copy()

    def stop(self, target):
        self.calls.append(('stop', target))
        self.props['ActiveState'] = 'inactive'

    def start(self, target):
        self.calls.append(('start', target))
        self.props['ActiveState'] = 'active'

    def limit(self, target, value):
        self.calls.append(('limit', target, value))
        self.props['MemoryHigh'] = value
        if self.fail_limit_after_change:
            self.fail_limit_after_change = False
            raise OperationError('lost response after mutation')

    def arm(self, session, seconds):
        self.calls.append(('arm', session, seconds))
        if self.fail_arm:
            raise OperationError('timer unavailable')

    def boot(self):
        return self.boot_id


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.backend = FakeBackend()
        self.engine = Engine(self.backend, self.store)

    def tearDown(self):
        self.temp.cleanup()

    def begin(self, choices=None):
        return self.engine.begin(choices or [(f'gnome:{EXT}', 'disable')], 5)

    def test_disable_and_restore(self):
        self.begin()
        self.assertNotIn(EXT, self.backend.enabled)
        self.assertEqual(self.engine.restore(), [])
        self.assertIn(EXT, self.backend.enabled)
        self.assertEqual(self.store.read()['status'], 'restored')

    def test_timer_armed_before_mutation(self):
        self.begin()
        self.assertEqual(self.backend.calls[0][0], 'arm')

    def test_timer_failure_makes_no_changes(self):
        self.backend.fail_arm = True
        with self.assertRaises(OperationError):
            self.begin()
        self.assertEqual(len(self.backend.calls), 1)
        self.assertIn(EXT, self.backend.enabled)

    def test_stop_and_restart_only_originally_active(self):
        self.begin([(f'user:{TARGET}', 'stop')])
        self.assertEqual(self.backend.props['ActiveState'], 'inactive')
        self.engine.restore()
        self.assertEqual(self.backend.props['ActiveState'], 'active')

    def test_memory_high_restored_exactly(self):
        self.backend.props['MemoryHigh'] = str(512 * 1048576)
        self.begin([(f'user:{TARGET}', 'limit')])
        self.assertEqual(self.backend.props['MemoryHigh'], str(256 * 1048576))
        self.engine.restore()
        self.assertEqual(self.backend.props['MemoryHigh'], str(512 * 1048576))

    def test_partial_mutation_is_rolled_back(self):
        self.backend.fail_limit_after_change = True
        with self.assertRaises(OperationError):
            self.begin([(f'user:{TARGET}', 'limit')])
        self.assertEqual(self.backend.props['MemoryHigh'], 'infinity')
        self.assertEqual(self.store.read()['status'], 'restored')

    def test_partial_plan_failure_rolls_back_prior_actions(self):
        self.backend.fail_disable = True
        with self.assertRaises(OperationError):
            self.begin([(f'user:{TARGET}', 'stop'), (f'gnome:{EXT}', 'disable')])
        self.assertEqual(self.backend.props['ActiveState'], 'active')

    def test_protected_targets_rejected(self):
        for target in ('system:sshd.service', 'user:pipewire.service', 'user:dbus.service',
                       'pid:1', 'gnome:memminning@local', 'gnome:screen-reader@example.org'):
            with self.subTest(target=target), self.assertRaises(OperationError):
                self.begin([(target, 'stop')])
        self.assertEqual(self.backend.calls, [])

    def test_service_alias_identity_rejected(self):
        self.backend.props['Id'] = 'pipewire.service'
        with self.assertRaises(OperationError):
            self.begin([(f'user:{TARGET}', 'stop')])

    def test_dependency_protection(self):
        for key in ('RequiredBy', 'BoundBy', 'TriggeredBy'):
            with self.subTest(key=key):
                self.backend.props[key] = 'important.service'
                with self.assertRaises(OperationError):
                    self.begin([(f'user:{TARGET}', 'stop')])
                self.backend.props[key] = ''

    def test_inactive_service_cannot_be_selected(self):
        self.backend.props['ActiveState'] = 'inactive'
        with self.assertRaises(OperationError):
            self.begin([(f'user:{TARGET}', 'stop')])

    def test_no_looser_limit(self):
        self.backend.props['MemoryHigh'] = str(64 * 1048576)
        with self.assertRaises(OperationError):
            self.begin([(f'user:{TARGET}', 'limit')])

    def test_duplicate_targets_rejected(self):
        with self.assertRaises(OperationError):
            self.begin([(f'user:{TARGET}', 'limit'), (f'user:{TARGET}', 'stop')])

    def test_active_session_cannot_be_overwritten(self):
        first = self.begin()
        with self.assertRaises(OperationError):
            self.begin()
        self.assertEqual(self.store.read()['id'], first['id'])

    def test_stale_timer_does_not_restore_new_session(self):
        self.begin()
        self.engine.restore('old-id')
        self.assertNotIn(EXT, self.backend.enabled)

    def test_restore_is_idempotent(self):
        self.begin()
        self.engine.restore()
        count = len(self.backend.calls)
        self.engine.restore()
        self.assertEqual(count, len(self.backend.calls))

    def test_restore_failure_keeps_journal_for_retry(self):
        self.begin()
        self.backend.fail_enable = True
        self.assertTrue(self.engine.restore())
        self.assertEqual(self.store.read()['status'], 'recovery-needed')
        self.backend.fail_enable = False
        self.assertEqual(self.engine.restore(), [])
        self.assertEqual(self.store.read()['status'], 'restored')

    def test_limit_conflict_preserved(self):
        self.begin([(f'user:{TARGET}', 'limit')])
        self.backend.props['MemoryHigh'] = '123456789'
        self.assertTrue(self.engine.restore())
        self.assertEqual(self.backend.props['MemoryHigh'], '123456789')

    def test_reboot_skips_runtime_service_mutations_but_restores_extensions(self):
        self.begin([(f'user:{TARGET}', 'stop'), (f'gnome:{EXT}', 'disable')])
        self.backend.boot_id = 'boot-b'
        self.backend.calls.clear()
        self.engine.restore()
        self.assertIn(EXT, self.backend.enabled)
        self.assertFalse(any(c[0] == 'start' for c in self.backend.calls))

    def test_pending_intent_recovered_after_crash(self):
        state = self.begin()
        state['actions'][0]['status'] = 'pending'
        self.store.write(state)
        Engine(self.backend, self.store).restore()
        self.assertIn(EXT, self.backend.enabled)

    def test_corrupt_journal_blocks_new_session(self):
        self.store.path.write_text('{invalid')
        with self.assertRaises(OperationError):
            self.begin()
        self.assertEqual(self.backend.calls, [])

    def test_unknown_schema_blocks(self):
        self.store.path.write_text('{"schema":99,"actions":[]}')
        with self.assertRaises(OperationError):
            self.engine.restore()

    def test_private_journal_permissions(self):
        self.begin()
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.directory.stat().st_mode & 0o777, 0o700)

    def test_duration_and_limit_validation(self):
        for minutes in (0, -1, 481):
            with self.assertRaises(OperationError):
                self.engine.prepare([(f'gnome:{EXT}', 'disable')], minutes)
        with self.assertRaises(OperationError):
            self.engine.prepare([(f'user:{TARGET}', 'limit')], 5, 0)

    def test_diagnostics_omit_inventory_and_redact_home(self):
        snap = Snapshot([Item('private', 'secret process', 'Processes', 'secret')],
                        [str(Path.home()) + '/private'], {}, {})
        report = export_report(snap, self.engine).read_text()
        self.assertNotIn('secret process', report)
        self.assertNotIn(str(Path.home()), report)
        self.assertIn('~/private', report)

    def test_extension_identifier_policy(self):
        for target in ('--help', '../bad', 'bad;rm', 'screenlock@test', 'live-lockscreen@test', 'memminning@local'):
            self.assertFalse(extension_allowed(target), target)
        self.assertTrue(extension_allowed(EXT))


if __name__ == '__main__':
    unittest.main()
