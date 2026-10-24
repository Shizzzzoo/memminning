import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import install
from memminning import __version__
from memminning.core import Store


class InstallerTests(unittest.TestCase):
    def test_offline_user_install_handles_spaces_and_launcher(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            home = root / 'user home'
            home.mkdir()
            data, config = root / 'data files', root / 'config files'
            state = Store(root / 'state')
            env = {'XDG_DATA_HOME': str(data), 'XDG_CONFIG_HOME': str(config)}
            with patch.object(install, 'check_dependencies'), patch.object(install.os, 'geteuid', return_value=1000), \
                 patch.object(install, 'Store', return_value=state), patch.object(Path, 'home', return_value=home), \
                 patch.dict(install.os.environ, env), patch('sys.argv', ['install.py']), contextlib.redirect_stdout(io.StringIO()):
                install.main()
            launcher = home / '.local/bin/memminning'
            result = subprocess.run([str(launcher), '--version'], text=True, capture_output=True, check=True)
            self.assertEqual(result.stdout.strip(), __version__)
            self.assertTrue((data / 'memminning/app/LICENSE').is_file())
            self.assertTrue((data / 'applications/io.github.memminning.Memminning.desktop').is_file())
            self.assertTrue((config / 'autostart/io.github.memminning.Recovery.desktop').is_file())
            self.assertFalse((data / 'memminning/app/assets/companions.png').exists())

    def test_active_session_prevents_installation(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            state = Store(root / 'state')
            state.write({'schema': 1, 'actions': [], 'status': 'active'})
            data = root / 'data'
            with patch.object(install, 'check_dependencies'), patch.object(install.os, 'geteuid', return_value=1000), \
                 patch.object(install, 'Store', return_value=state), patch.dict(install.os.environ, {'XDG_DATA_HOME': str(data)}), \
                 patch('sys.argv', ['install.py']), self.assertRaises(SystemExit):
                install.main()
            self.assertFalse(data.exists())
