import importlib.util
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading

from .drawing import scene_geometry

DRAW = '''({shapes, width, height, params, frame, frames}) => {
  const canvas = document.querySelector('canvas');
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext('2d');
  const foreground = params.foreground || '#252925';
  const background = params.background || '#eee9df';
  const accent = params.accent || '#bb5537';
  ctx.fillStyle = background; ctx.fillRect(0, 0, width, height);
  for (const [kind, points, colored, thickness] of shapes) {
    ctx.beginPath(); ctx.moveTo(...points[0]);
    for (const point of points.slice(1)) ctx.lineTo(...point);
    ctx.strokeStyle = colored ? accent : foreground; ctx.lineWidth = thickness;
    if (kind === 'polygon') { ctx.closePath(); ctx.fillStyle = background; ctx.fill(); }
    ctx.stroke();
  }
  ctx.strokeStyle = foreground; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(width*.07, height*.85); ctx.lineTo(width*.93, height*.85); ctx.stroke();
  ctx.strokeStyle = accent; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(width*.07, height*.85); ctx.lineTo(width*(.07+.86*frame/Math.max(1,frames-1)), height*.85); ctx.stroke();
  const bounds = [];
  const unit = Math.min(width/960, height/540);
  for (const [key,size,y] of [['heading',56,.39],['subheading',19,.55]]) {
    const text = params[key] || ''; if (!text) continue;
    ctx.font = `${Math.max(8,size*unit)}px sans-serif`;
    ctx.textBaseline = 'top'; ctx.fillStyle = foreground;
    const measure = ctx.measureText(text);
    if (width*.07 + measure.width > width*.43) throw new Error(`Text exceeds safe layout region: ${key}`);
    ctx.fillText(text,width*.07,height*y);
    bounds.push({field:key,bounds:[width*.07,height*y,width*.07+measure.width,height*y+size*unit]});
  }
  return bounds;
}'''


class _PageProxy:
    def __init__(self, renderer):
        self._renderer = renderer

    def evaluate(self, expression, arg=None):
        return self._renderer.evaluate(expression, arg)


class BrowserRenderer:
    def __init__(self, timeout=12.0, worker_cmd=None):
        self.timeout = float(timeout)
        self._worker_cmd = worker_cmd
        self.process = None
        self._responses = queue.Queue()
        self.version = None
        self.page = _PageProxy(self)

    def _reader(self, stream):
        try:
            for line in stream:
                self._responses.put(line)
        finally:
            self._responses.put(None)

    def _terminate(self):
        proc = self.process
        self.process = None
        if proc is None:
            return
        if proc.poll() is None:
            if os.name == 'nt':
                proc.kill()
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        try:
            proc.communicate(timeout=2)
        except Exception:
            pass

    def _request(self, payload, stage='operation'):
        if self.process is None or self.process.poll() is not None:
            raise ValueError(f'Headless browser unavailable: worker exited before {stage}')
        if payload is not None:
            try:
                self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + '\n')
                self.process.stdin.flush()
            except OSError as error:
                self._terminate()
                raise ValueError(f'Headless browser unavailable: {error}') from error
        try:
            line = self._responses.get(timeout=self.timeout)
        except queue.Empty as error:
            self._terminate()
            raise ValueError(f'Headless browser unavailable: {stage} timed out after {self.timeout:.1f}s (check sandbox or headless display permissions)') from error
        if line is None:
            stderr_tail = ''
            if self.process and self.process.stderr:
                stderr_tail = self.process.stderr.read()[-800:].strip()
            self._terminate()
            raise ValueError(f'Headless browser unavailable: {stderr_tail or "worker closed unexpectedly"}')
        message = json.loads(line)
        if not message.get('ok'):
            error_text = message.get('error', 'unknown browser failure')
            if stage == 'readiness':
                self._terminate()
            raise ValueError(error_text)
        return message

    def __enter__(self):
        if self._worker_cmd is None and importlib.util.find_spec('playwright') is None:
            raise ValueError('Browser renderer requires the optional Playwright package and Chromium; no automatic installation occurs')
        cmd = self._worker_cmd or [sys.executable, '-m', 'reelsyntax.browser', '--worker']
        allowed_env = {'PATH', 'HOME', 'TMPDIR', 'TEMP', 'TMP', 'SystemRoot', 'WINDIR', 'LANG', 'LC_ALL', 'PLAYWRIGHT_BROWSERS_PATH', 'PYTHONPATH'}
        env = {k: v for k, v in os.environ.items() if k in allowed_env}
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            env=env,
            start_new_session=(os.name != 'nt'),
        )
        threading.Thread(target=self._reader, args=(self.process.stdout,), daemon=True).start()
        try:
            ready = self._request(None, stage='readiness')
            self.version = ready['version']
        except BaseException:
            self._terminate()
            raise
        return self

    def draw(self, scene, frame, output, seed, destination):
        width, height = output['width'], output['height']
        payload = {
            'cmd': 'draw',
            'destination': str(Path(destination)),
            'viewport': {'width': width, 'height': height},
            'draw_arg': {
                'shapes': scene_geometry(scene, frame, width, height, seed),
                'width': width,
                'height': height,
                'params': scene['params'],
                'frame': frame,
                'frames': scene['duration_frames'],
                'recipe': scene['recipe'],
                'seed': seed,
            },
        }
        return self._request(payload, stage=f'draw frame {frame}')['bounds']

    def install_module(self, source):
        self._request({'cmd': 'module', 'source': source}, stage='Three.js bundle setup')

    def require_webgl(self):
        return self._request({'cmd': 'probe_webgl'}, stage='WebGL capability probe')['info']

    def evaluate(self, expression, arg=None):
        payload = {'cmd': 'eval', 'expression': expression, 'has_arg': arg is not None, 'arg': arg}
        return self._request(payload, stage='evaluate')['value']

    def __exit__(self, *args):
        if self.process is not None and self.process.poll() is None:
            try:
                self._request({'cmd': 'close'}, stage='close')
            except ValueError:
                pass
        self._terminate()


def _worker_main():
    def emit(obj):
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + '\n')
        sys.stdout.flush()

    manager = None
    browser = None
    try:
        from playwright.sync_api import sync_playwright
        manager = sync_playwright().start()
        launch_env = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'TMPDIR', 'TEMP', 'TMP', 'SystemRoot', 'WINDIR', 'LANG'}}
        browser = manager.chromium.launch(headless=True, chromium_sandbox=True, env=launch_env, timeout=10000)
        context = browser.new_context(offline=True, service_workers='block', accept_downloads=False)
        context.route('**/*', lambda route: route.abort())
        page = context.new_page()
        page.set_default_timeout(10000)
        page.set_content('<html><body style="margin:0"><canvas></canvas></body></html>')
        page.evaluate('() => document.fonts.ready')
        ink = page.evaluate('''() => {
            const test = document.createElement('canvas'); test.width = 120; test.height = 40;
            const ctx = test.getContext('2d'); ctx.font = '24px sans-serif';
            ctx.fillText('Hx0', 5, 30);
            return ctx.getImageData(0,0,120,40).data.some((value,index) => index % 4 === 3 && value > 0);
        }''')
        if not ink:
            raise ValueError('Browser font canary rendered no ink; install an authorized local font before rendering typography')
        emit({'ok': True, 'version': browser.version})
        for raw in sys.stdin:
            req = json.loads(raw)
            cmd = req.get('cmd')
            if cmd == 'close':
                emit({'ok': True})
                break
            try:
                if cmd == 'draw':
                    page.set_viewport_size(req['viewport'])
                    page.evaluate("shader => {const gl=document.querySelector('#rs-webgl');if(gl)gl.style.display=shader?'block':'none';document.querySelector('canvas:not(#rs-webgl)').style.display=shader?'none':'block';}", req['draw_arg']['recipe'] in ('shader-sculpture', 'custom-shader', 'three-scene'))
                    if req['draw_arg']['recipe'] == 'three-scene':
                        page.evaluate("async (args) => {const canvas=document.querySelector('#rs-webgl');canvas.width=args.width;canvas.height=args.height;await window.renderReelFrame(canvas,args);}", req['draw_arg'])
                        bounds, selector = [], '#rs-webgl'
                    elif req['draw_arg']['recipe'] in ('shader-sculpture', 'custom-shader'):
                        from .webgl import DRAW as DRAW_WEBGL
                        bounds = page.evaluate(DRAW_WEBGL, req['draw_arg'])
                        selector = '#rs-webgl'
                    else:
                        bounds = page.evaluate(DRAW, req['draw_arg'])
                        selector = 'canvas:not(#rs-webgl)'
                    page.locator(selector).screenshot(path=req['destination'], animations='disabled')
                    emit({'ok': True, 'bounds': bounds})
                elif cmd == 'module':
                    page.evaluate('() => { delete window.renderReelFrame; }')
                    page.add_script_tag(content=req['source'])
                    if not page.evaluate("typeof window.renderReelFrame === 'function'"):
                        raise ValueError('Bundle must define window.renderReelFrame(canvas, args)')
                    emit({'ok': True})
                elif cmd == 'probe_webgl':
                    from .webgl import PROBE
                    info = page.evaluate(PROBE)
                    page.evaluate("() => {document.querySelector('#rs-webgl').style.position='absolute';document.querySelector('#rs-webgl').style.top='0';}")
                    emit({'ok': True, 'info': info})
                elif cmd == 'eval':
                    value = page.evaluate(req['expression'], req['arg']) if req.get('has_arg') else page.evaluate(req['expression'])
                    emit({'ok': True, 'value': value})
                else:
                    emit({'ok': False, 'error': f'Unsupported browser worker command: {cmd}'})
            except Exception as error:
                emit({'ok': False, 'error': str(error)})
    except Exception as error:
        emit({'ok': False, 'error': f'Headless browser unavailable: {error}'})
        return 1
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if manager is not None:
            try:
                manager.stop()
            except Exception:
                pass
    return 0


if __name__ == '__main__' and '--worker' in sys.argv[1:]:
    raise SystemExit(_worker_main())
