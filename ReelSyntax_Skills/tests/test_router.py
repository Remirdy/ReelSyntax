import importlib.util,json,pathlib,re,unittest,contextlib,io
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('route', ROOT/'tools/route.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ROWS=json.loads((ROOT/'registry/index.json').read_text(encoding='utf-8'))['skills']
CASES=[('PS D',None),('psd animasyon','psd-to-video'),('seslendirme senkronu','voiceover-alignment'),('beat sync','beat-synced-editing'),('kamera sabit orbit','locked-camera'),('yazı olmasın kinetic typography','textless-visual-design'),('GitHub tanıtım','repository-to-video'),('word anchored','word-anchored-timeline'),('siyah kare','black-frame-detection'),('türkçe karakter','turkish-glyph-audit'),('blender geometry nodes','blender-geometry-nodes'),('web sitesinden video','website-to-video'),('render devam','resume-render'),('sadece değişen sahne','partial-render'),('alt bar sabit','locked-region-editing'),('loudness normalization','loudness-normalization'),('skill seçimi','skill-routing'),('lineer cebir','linear-algebra-visualization'),('no camera movement, dolly zoom','locked-camera'),('öğretmenler günü','teacher-tribute'),('fcpxml','fcpxml-export'),('foley','foley-design'),('glitch geçişi','glitch-transition'),('psd mp3 eşleştir','asset-matching'),('reeldiff','revision-diff'),('random unrecognized xqz','NONE')]
class TestRouter(unittest.TestCase):
 def test_catalog(self):
  self.assertGreaterEqual(len(ROWS),500);self.assertEqual(len(set(r['id'] for r in ROWS)),len(ROWS))
  self.assertEqual(len(list((ROOT/'library').glob('*/*/SKILL.md'))),len(ROWS))
  for r in ROWS:
   self.assertRegex(r['id'],r'^[a-z0-9]+(?:-[a-z0-9]+)*$');self.assertLessEqual(len(r['id']),64);self.assertLessEqual(len(r['description']),1024)
   self.assertTrue(m.safe_path(r).read_text(encoding='utf-8').startswith('---\nname: '+r['id']+'\n'))
 def test_queries(self):
  for query,expected in CASES:
   if expected is None:continue
   with self.subTest(query=query):
    res=m.route(query,ROWS);self.assertEqual(res['skill_bodies_read'],0);self.assertLessEqual(len(res['selected']),6)
    ids=[x['id'] for x in res['selected']]
    if expected=='NONE':self.assertEqual(ids,[])
    else:self.assertIn(expected,ids)
 def test_locked(self):
  self.assertNotIn('orbit-camera',[x['id'] for x in m.route('kamera sabit orbit',ROWS)['selected']])
  self.assertNotIn('kinetic-typography',[x['id'] for x in m.route('no text kinetic typography',ROWS)['selected']])
 def test_capabilities(self):
  res=m.route('blender cycles',ROWS,available=[]);self.assertNotIn('blender-cycles',[x['id'] for x in res['selected']]);self.assertIn('blender-cycles',[x['id'] for x in res['unavailable']])
 def test_budget_stage_override(self):
  res=m.route('render devam preview render',ROWS,stage='render',word_budget=320);self.assertLessEqual(res['estimated_loaded_words_if_all_selected'],320)
  self.assertTrue(all(x['stage']=='render' for x in res['selected']))
  self.assertEqual(m.route('nonsense',ROWS,include=['asset-matching'])['selected'][0]['id'],'asset-matching')
  self.assertTrue(m.route('nonsense',ROWS,include=['asset-matching'],word_budget=1)['unfulfilled_explicit_ids'])
 def test_conflicts(self):
  with self.assertRaises(ValueError):m.route('camera locked',ROWS,include=['orbit-camera'])
 def test_determinism(self):self.assertEqual(m.route('psd video',ROWS),m.route('psd video',ROWS))
if __name__=='__main__':unittest.main(verbosity=2)
