"""Exercise real package resolution and the configured Streamlit watcher."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def run_python(self, code, cwd):
        # No inherited path or secret overrides: this must exercise repository config.
        environment = os.environ.copy()
        for name in ('PYTHONPATH', 'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'STREAMLIT_SERVER_FILE_WATCHER_TYPE'):
            environment.pop(name, None)
        result = subprocess.run(
            [sys.executable, '-c', code], cwd=cwd, env=environment,
            capture_output=True, text=True, timeout=45,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_production_config_selects_noop_watcher(self):
        self.run_python('''
from streamlit import config
from streamlit.watcher.path_watcher import NoOpPathWatcher, get_default_path_watcher_class
assert config.get_option('server.fileWatcherType') == 'none'
assert get_default_path_watcher_class() is NoOpPathWatcher
''', REPO)

    def test_absolute_entrypoint_imports_and_reruns_outside_repo(self):
        with tempfile.TemporaryDirectory() as cwd:
            self.run_python(f'''
from pathlib import Path
from streamlit.testing.v1 import AppTest
repo = Path({str(REPO)!r})
app = AppTest.from_file(str(repo / 'app.py')).run(timeout=30)
assert not app.exception, app.exception
app.text_input('input_sender_name').set_value('Import regression test').run(timeout=30)
assert not app.exception, app.exception
app.run(timeout=30)
assert not app.exception, app.exception
import core
import core.models
import services
import services.gemini_service
assert Path(core.__file__).resolve() == repo / 'core' / '__init__.py'
assert Path(core.models.__file__).resolve() == repo / 'core' / 'models.py'
assert Path(services.__file__).resolve() == repo / 'services' / '__init__.py'
assert Path(services.gemini_service.__file__).resolve() == repo / 'services' / 'gemini_service.py'
''', cwd)
