import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def command(*args,cwd=ROOT):
    return subprocess.run([sys.executable,'-m','reelsyntax',*map(str,args)],cwd=cwd,text=True,capture_output=True,timeout=30)


class CliTests(unittest.TestCase):
    def test_utf8_json_with_non_utf8_child_stream_defaults(self):
        import os
        env = dict(os.environ, PYTHONIOENCODING='ascii')
        for command in ([sys.executable, '-m', 'reelsyntax', 'skills', 'explain', 'kamera sabit yazı olmasın', '--json'], [sys.executable, str(ROOT / 'ReelSyntax_Skills/tools/route.py'), 'kamera sabit yazı olmasın', '--json']):
            result = subprocess.run(command, capture_output=True, encoding='utf-8', env=env, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)

    def test_json_and_help(self):
        self.assertEqual(command('--help').returncode,0)
        response=command('skills','search','siyah kare','--json')
        self.assertEqual(response.returncode,0,response.stderr)
        result=json.loads(response.stdout)
        self.assertTrue(result['ok'])
        self.assertEqual(result['result']['skill_bodies_read'],0)

    def test_error_exit_and_empty_stdout(self):
        response=command('skills','load','missing-skill')
        self.assertEqual(response.returncode,2)
        self.assertEqual(response.stdout,'')
        self.assertFalse(json.loads(response.stderr)['ok'])

    def test_installed_launcher_from_other_directory(self):
        from reelsyntax.hosts import install
        with tempfile.TemporaryDirectory() as tmp:
            install(tmp,'codex')
            launcher=Path(tmp,'.agents/skills/reelsyntax-router/route.py')
            response=subprocess.run([sys.executable,str(launcher),'siyah kare','--json'],cwd=tmp,capture_output=True,text=True,timeout=30)
            self.assertEqual(response.returncode,0,response.stderr)
            self.assertEqual(json.loads(response.stdout)['skill_bodies_read'],0)

    def test_init_validate_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp,'Film Türkçe space')
            for args in [('init',project),('validate',project),('plan',project)]:
                response=command(*args)
                self.assertEqual(response.returncode,0,response.stderr)
                self.assertTrue(json.loads(response.stdout)['ok'])
            exp=command('export',project,'--format','otio')
            self.assertEqual(exp.returncode,0,exp.stderr)
            self.assertTrue(json.loads(exp.stdout)['ok'])

    def test_doctor_integrations_install_dry_run_and_explain(self):
        for args in [
            ('doctor','--json'),
            ('integrations','--json'),
            ('install','--all','--dry-run','--json'),
            ('skills','explain','kamera sabit yazı olmasın','--json'),
        ]:
            with self.subTest(args=args):
                response=command(*args)
                self.assertEqual(response.returncode,0,response.stderr)
                payload=json.loads(response.stdout)
                self.assertTrue(payload['ok'])
                if args[0]=='skills':
                    self.assertIn('explanation',payload['result'])


if __name__ == '__main__':
    unittest.main()
