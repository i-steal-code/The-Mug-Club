Developer logs/cursor prompts
this text file is for the purpose of storing cursor prompts and also doubles as a dev log 

v0.1.1
based on the contents of the current repository,
code rebase & refactor to host:
1. remove shop-dashboard folder and shop-dashboard 2 folder in favour of organising everything properly in the repo file
2. re-work the tech stack and framework to be hosted on render web app and database hosted on supabase
3. update readme to be slightly simplified and also state current v0.1 development 
4. change UI colour scheme to have primary colour (background colour) as white #eeede9, secondary colour as green #415b42, and a border/constrasting colour as black-green using the green provided as a root colour
5. add a feature to allow import and export of .csv files to port over into the database
6. rework database based on .csv files and also insert new data to sync. all data are migrated from google sheets, with 1 actively linked to a google form to receive orders, another financial tracker that needs to be accessible to stakeholders (will require exporting data from web app database into the google sheet), and a margins and inventory sheet. leave the members feature untouched, and rework the orders, finance and inventory to fit the data provided. recipes with ingredient amounts will be input and created later in the recipe page. csv files are in the database import folder, leave the folder untouched for database import/export (financial tracking sheet)
7. add recipes page to create new recipes and items. every latte uses the base items, 1 coffee or matcha cloud, and 1 flavour (no flavour for original lattes).

v0.1.2
hosting troubleshooting:
here are the error logs from the first deployment:
2026-04-24T00:36:45.403752394Z ==> Setting WEB_CONCURRENCY=1 by default, based on available CPUs in the instance
2026-04-24T00:36:55.168249143Z ==> Running 'gunicorn app:app'
2026-04-24T00:37:00.457944912Z Traceback (most recent call last):
2026-04-24T00:37:00.459244656Z   File "/opt/render/project/src/.venv/bin/gunicorn", line 7, in <module>
2026-04-24T00:37:00.459258356Z     sys.exit(run())
2026-04-24T00:37:00.459260827Z              ~~~^^
2026-04-24T00:37:00.459263437Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/app/wsgiapp.py", line 67, in run
2026-04-24T00:37:00.459269307Z     WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=prog).run()
2026-04-24T00:37:00.459271487Z     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
2026-04-24T00:37:00.459273487Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/app/base.py", line 236, in run
2026-04-24T00:37:00.459275837Z     super().run()
2026-04-24T00:37:00.459277907Z     ~~~~~~~~~~~^^
2026-04-24T00:37:00.459280387Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/app/base.py", line 72, in run
2026-04-24T00:37:00.459283427Z     Arbiter(self).run()
2026-04-24T00:37:00.459286647Z     ~~~~~~~^^^^^^
2026-04-24T00:37:00.459290057Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/arbiter.py", line 58, in __init__
2026-04-24T00:37:00.459293177Z     self.setup(app)
2026-04-24T00:37:00.459296597Z     ~~~~~~~~~~^^^^^
2026-04-24T00:37:00.459299708Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/arbiter.py", line 118, in setup
2026-04-24T00:37:00.459302778Z     self.app.wsgi()
2026-04-24T00:37:00.459305958Z     ~~~~~~~~~~~~~^^
2026-04-24T00:37:00.459308918Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/app/base.py", line 67, in wsgi
2026-04-24T00:37:00.459311348Z     self.callable = self.load()
2026-04-24T00:37:00.459313318Z                     ~~~~~~~~~^^
2026-04-24T00:37:00.459315608Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
2026-04-24T00:37:00.459318458Z     return self.load_wsgiapp()
2026-04-24T00:37:00.459321868Z            ~~~~~~~~~~~~~~~~~^^
2026-04-24T00:37:00.459325408Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
2026-04-24T00:37:00.459329029Z     return util.import_app(self.app_uri)
2026-04-24T00:37:00.459332089Z            ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
2026-04-24T00:37:00.459346079Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/gunicorn/util.py", line 371, in import_app
2026-04-24T00:37:00.459348479Z     mod = importlib.import_module(module)
2026-04-24T00:37:00.459350559Z   File "/opt/render/project/python/Python-3.14.3/lib/python3.14/importlib/__init__.py", line 88, in import_module
2026-04-24T00:37:00.459353179Z     return _bootstrap._gcd_import(name[level:], package, level)
2026-04-24T00:37:00.459355109Z            ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T00:37:00.459357109Z   File "<frozen importlib._bootstrap>", line 1398, in _gcd_import
2026-04-24T00:37:00.459359099Z   File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
2026-04-24T00:37:00.459361059Z   File "<frozen importlib._bootstrap>", line 1342, in _find_and_load_unlocked
2026-04-24T00:37:00.45936887Z   File "<frozen importlib._bootstrap>", line 938, in _load_unlocked
2026-04-24T00:37:00.45937093Z   File "<frozen importlib._bootstrap_external>", line 759, in exec_module
2026-04-24T00:37:00.45937285Z   File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
2026-04-24T00:37:00.45937479Z   File "/opt/render/project/src/app.py", line 14, in <module>
2026-04-24T00:37:00.45938827Z     import psycopg2
2026-04-24T00:37:00.45939044Z   File "/opt/render/project/src/.venv/lib/python3.14/site-packages/psycopg2/__init__.py", line 51, in <module>
2026-04-24T00:37:00.45939246Z     from psycopg2._psycopg import (                     # noqa
2026-04-24T00:37:00.45939448Z     ...<10 lines>...
2026-04-24T00:37:00.45939672Z     )
2026-04-24T00:37:00.45939962Z ImportError: /opt/render/project/src/.venv/lib/python3.14/site-packages/psycopg2/_psycopg.cpython-314-x86_64-linux-gnu.so: undefined symbol: _PyInterpreterState_Get
2026-04-24T00:37:02.12616382Z ==> Exited with status 1
2026-04-24T00:37:02.139863064Z ==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys

v0.1.3
supabase issues
error logs:
2026-04-24T01:39:11.538195092Z ==> Using Python version 3.12.6 via /opt/render/project/src/.python-version
2026-04-24T01:39:11.538211862Z ==> Docs on specifying a Python version: https://render.com/docs/python-version
2026-04-24T01:39:11.538330399Z ==> Installing Python version 3.12.6...
2026-04-24T01:39:27.121462555Z ==> Using Poetry version 2.1.3 (default)
2026-04-24T01:39:27.174116384Z ==> Docs on specifying a Poetry version: https://render.com/docs/poetry-version
2026-04-24T01:39:27.303143993Z ==> Running build command 'pip install -r requirements.txt'...
2026-04-24T01:39:28.018779384Z Collecting Flask==3.0.3 (from -r requirements.txt (line 1))
2026-04-24T01:39:28.020214588Z   Using cached flask-3.0.3-py3-none-any.whl.metadata (3.2 kB)
2026-04-24T01:39:28.140207792Z Collecting gunicorn==22.0.0 (from -r requirements.txt (line 2))
2026-04-24T01:39:28.141566222Z   Using cached gunicorn-22.0.0-py3-none-any.whl.metadata (4.4 kB)
2026-04-24T01:39:28.35920338Z Collecting psycopg2-binary==2.9.9 (from -r requirements.txt (line 3))
2026-04-24T01:39:28.377023356Z   Using cached psycopg2_binary-2.9.9-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.4 kB)
2026-04-24T01:39:28.541833636Z Collecting Werkzeug>=3.0.0 (from Flask==3.0.3->-r requirements.txt (line 1))
2026-04-24T01:39:28.5430704Z   Using cached werkzeug-3.1.8-py3-none-any.whl.metadata (4.0 kB)
2026-04-24T01:39:28.670865366Z Collecting Jinja2>=3.1.2 (from Flask==3.0.3->-r requirements.txt (line 1))
2026-04-24T01:39:28.672067177Z   Using cached jinja2-3.1.6-py3-none-any.whl.metadata (2.9 kB)
2026-04-24T01:39:28.874140505Z Collecting itsdangerous>=2.1.2 (from Flask==3.0.3->-r requirements.txt (line 1))
2026-04-24T01:39:28.87541425Z   Using cached itsdangerous-2.2.0-py3-none-any.whl.metadata (1.9 kB)
2026-04-24T01:39:29.009795944Z Collecting click>=8.1.3 (from Flask==3.0.3->-r requirements.txt (line 1))
2026-04-24T01:39:29.011101161Z   Using cached click-8.3.3-py3-none-any.whl.metadata (2.6 kB)
2026-04-24T01:39:29.129260651Z Collecting blinker>=1.6.2 (from Flask==3.0.3->-r requirements.txt (line 1))
2026-04-24T01:39:29.130497364Z   Using cached blinker-1.9.0-py3-none-any.whl.metadata (1.6 kB)
2026-04-24T01:39:29.304955501Z Collecting packaging (from gunicorn==22.0.0->-r requirements.txt (line 2))
2026-04-24T01:39:29.306123071Z   Using cached packaging-26.1-py3-none-any.whl.metadata (3.5 kB)
2026-04-24T01:39:29.519997035Z Collecting MarkupSafe>=2.0 (from Jinja2>=3.1.2->Flask==3.0.3->-r requirements.txt (line 1))
2026-04-24T01:39:29.521282361Z   Using cached markupsafe-3.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.7 kB)
2026-04-24T01:39:29.527241148Z Using cached flask-3.0.3-py3-none-any.whl (101 kB)
2026-04-24T01:39:29.528385927Z Using cached gunicorn-22.0.0-py3-none-any.whl (84 kB)
2026-04-24T01:39:29.529541886Z Using cached psycopg2_binary-2.9.9-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.0 MB)
2026-04-24T01:39:29.533076228Z Using cached blinker-1.9.0-py3-none-any.whl (8.5 kB)
2026-04-24T01:39:29.534176895Z Using cached click-8.3.3-py3-none-any.whl (110 kB)
2026-04-24T01:39:29.535353415Z Using cached itsdangerous-2.2.0-py3-none-any.whl (16 kB)
2026-04-24T01:39:29.536448932Z Using cached jinja2-3.1.6-py3-none-any.whl (134 kB)
2026-04-24T01:39:29.537635513Z Using cached werkzeug-3.1.8-py3-none-any.whl (226 kB)
2026-04-24T01:39:29.538867836Z Using cached packaging-26.1-py3-none-any.whl (95 kB)
2026-04-24T01:39:29.540054067Z Using cached markupsafe-3.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (22 kB)
2026-04-24T01:39:29.564722786Z Installing collected packages: psycopg2-binary, packaging, MarkupSafe, itsdangerous, click, blinker, Werkzeug, Jinja2, gunicorn, Flask
2026-04-24T01:39:31.602844842Z Successfully installed Flask-3.0.3 Jinja2-3.1.6 MarkupSafe-3.0.3 Werkzeug-3.1.8 blinker-1.9.0 click-8.3.3 gunicorn-22.0.0 itsdangerous-2.2.0 packaging-26.1 psycopg2-binary-2.9.9
2026-04-24T01:39:31.630660913Z 
2026-04-24T01:39:31.630680534Z [notice] A new release of pip is available: 24.2 -> 26.0.1
2026-04-24T01:39:31.630705845Z [notice] To update, run: pip install --upgrade pip
2026-04-24T01:39:45.580531472Z ==> Uploading build...
2026-04-24T01:39:50.204634085Z ==> Uploaded in 1.9s. Compression took 2.7s
2026-04-24T01:39:50.300580362Z ==> Build successful 🎉
2026-04-24T01:40:19.156850901Z ==> Deploying...
2026-04-24T01:40:19.363265814Z ==> Setting WEB_CONCURRENCY=1 by default, based on available CPUs in the instance
2026-04-24T01:40:45.242548149Z ==> Running 'gunicorn app:app'
2026-04-24T01:40:54.546822659Z Traceback (most recent call last):
2026-04-24T01:40:54.546853321Z   File "/opt/render/project/src/.venv/bin/gunicorn", line 8, in <module>
2026-04-24T01:40:54.54702555Z     sys.exit(run())
2026-04-24T01:40:54.547125815Z              ^^^^^
2026-04-24T01:40:54.547137696Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 67, in run
2026-04-24T01:40:54.549132042Z     WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=prog).run()
2026-04-24T01:40:54.549235018Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 236, in run
2026-04-24T01:40:54.551749572Z     super().run()
2026-04-24T01:40:54.551795664Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 72, in run
2026-04-24T01:40:54.55190341Z     Arbiter(self).run()
2026-04-24T01:40:54.551937272Z     ^^^^^^^^^^^^^
2026-04-24T01:40:54.551942122Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 58, in __init__
2026-04-24T01:40:54.554490358Z     self.setup(app)
2026-04-24T01:40:54.554503089Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 118, in setup
2026-04-24T01:40:54.554508549Z     self.app.wsgi()
2026-04-24T01:40:54.554513119Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 67, in wsgi
2026-04-24T01:40:54.55451812Z     self.callable = self.load()
2026-04-24T01:40:54.55452237Z                     ^^^^^^^^^^^
2026-04-24T01:40:54.55452553Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
2026-04-24T01:40:54.55452866Z     return self.load_wsgiapp()
2026-04-24T01:40:54.55453171Z            ^^^^^^^^^^^^^^^^^^^
2026-04-24T01:40:54.554535101Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
2026-04-24T01:40:54.554538551Z     return util.import_app(self.app_uri)
2026-04-24T01:40:54.554541651Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:40:54.554544801Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/util.py", line 371, in import_app
2026-04-24T01:40:54.556674815Z     mod = importlib.import_module(module)
2026-04-24T01:40:54.556683565Z           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:40:54.556697036Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/importlib/__init__.py", line 90, in import_module
2026-04-24T01:40:54.560563962Z     return _bootstrap._gcd_import(name[level:], package, level)
2026-04-24T01:40:54.560589333Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:40:54.560599674Z   File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
2026-04-24T01:40:54.560605684Z   File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
2026-04-24T01:40:54.560630126Z   File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
2026-04-24T01:40:54.560636856Z   File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
2026-04-24T01:40:54.560640866Z   File "<frozen importlib._bootstrap_external>", line 995, in exec_module
2026-04-24T01:40:54.560647947Z   File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
2026-04-24T01:40:54.560654447Z   File "/opt/render/project/src/app.py", line 107, in <module>
2026-04-24T01:40:54.561305351Z     ensure_schema_and_seed()
2026-04-24T01:40:54.561314942Z   File "/opt/render/project/src/app.py", line 74, in ensure_schema_and_seed
2026-04-24T01:40:54.56183559Z     conn = get_conn()
2026-04-24T01:40:54.561849231Z            ^^^^^^^^^^
2026-04-24T01:40:54.561852651Z   File "/opt/render/project/src/app.py", line 44, in get_conn
2026-04-24T01:40:54.561855801Z     return psycopg2.connect(url, cursor_factory=extras.RealDictCursor)
2026-04-24T01:40:54.561858841Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:40:54.561862061Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/psycopg2/__init__.py", line 122, in connect
2026-04-24T01:40:54.562343617Z     conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
2026-04-24T01:40:54.562356047Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:40:54.562416821Z psycopg2.OperationalError: connection to server at "db.vqawahybaepcnfehlimn.supabase.co" (2406:da18:243:7429:9ba0:fb3:6f36:99aa), port 5432 failed: Network is unreachable
2026-04-24T01:40:54.562421491Z 	Is the server running on that host and accepting TCP/IP connections?
2026-04-24T01:40:54.562424351Z 
2026-04-24T01:41:10.499639089Z ==> Exited with status 1
2026-04-24T01:41:10.501862897Z ==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
2026-04-24T01:41:18.000361743Z ==> Running 'gunicorn app:app'
2026-04-24T01:41:25.718191994Z Traceback (most recent call last):
2026-04-24T01:41:25.718213566Z   File "/opt/render/project/src/.venv/bin/gunicorn", line 8, in <module>
2026-04-24T01:41:25.718323341Z     sys.exit(run())
2026-04-24T01:41:25.718330702Z              ^^^^^
2026-04-24T01:41:25.718335682Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 67, in run
2026-04-24T01:41:25.719216299Z     WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=prog).run()
2026-04-24T01:41:25.719328735Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 236, in run
2026-04-24T01:41:25.71998343Z     super().run()
2026-04-24T01:41:25.719991381Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 72, in run
2026-04-24T01:41:25.720136708Z     Arbiter(self).run()
2026-04-24T01:41:25.720145699Z     ^^^^^^^^^^^^^
2026-04-24T01:41:25.720149679Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 58, in __init__
2026-04-24T01:41:25.721017685Z     self.setup(app)
2026-04-24T01:41:25.721033016Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 118, in setup
2026-04-24T01:41:25.721176714Z     self.app.wsgi()
2026-04-24T01:41:25.721186504Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 67, in wsgi
2026-04-24T01:41:25.721281039Z     self.callable = self.load()
2026-04-24T01:41:25.721287999Z                     ^^^^^^^^^^^
2026-04-24T01:41:25.72129301Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
2026-04-24T01:41:25.721391495Z     return self.load_wsgiapp()
2026-04-24T01:41:25.721399616Z            ^^^^^^^^^^^^^^^^^^^
2026-04-24T01:41:25.721405476Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
2026-04-24T01:41:25.721499151Z     return util.import_app(self.app_uri)
2026-04-24T01:41:25.721511171Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:41:25.721516042Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/util.py", line 371, in import_app
2026-04-24T01:41:25.722441441Z     mod = importlib.import_module(module)
2026-04-24T01:41:25.722455602Z           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:41:25.722460972Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/importlib/__init__.py", line 90, in import_module
2026-04-24T01:41:25.722578768Z     return _bootstrap._gcd_import(name[level:], package, level)
2026-04-24T01:41:25.722592339Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:41:25.722598Z   File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
2026-04-24T01:41:25.72260636Z   File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
2026-04-24T01:41:25.72261112Z   File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
2026-04-24T01:41:25.72261545Z   File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
2026-04-24T01:41:25.722620041Z   File "<frozen importlib._bootstrap_external>", line 995, in exec_module
2026-04-24T01:41:25.722628301Z   File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
2026-04-24T01:41:25.722645482Z   File "/opt/render/project/src/app.py", line 107, in <module>
2026-04-24T01:41:25.723121637Z     ensure_schema_and_seed()
2026-04-24T01:41:25.723133998Z   File "/opt/render/project/src/app.py", line 74, in ensure_schema_and_seed
2026-04-24T01:41:25.723138558Z     conn = get_conn()
2026-04-24T01:41:25.723152949Z            ^^^^^^^^^^
2026-04-24T01:41:25.723156389Z   File "/opt/render/project/src/app.py", line 44, in get_conn
2026-04-24T01:41:25.723159019Z     return psycopg2.connect(url, cursor_factory=extras.RealDictCursor)
2026-04-24T01:41:25.723161799Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:41:25.72316445Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/psycopg2/__init__.py", line 122, in connect
2026-04-24T01:41:25.797731045Z     conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
2026-04-24T01:41:25.797805199Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:41:25.79781218Z psycopg2.OperationalError: connection to server at "db.vqawahybaepcnfehlimn.supabase.co" (2406:da18:243:7429:9ba0:fb3:6f36:99aa), port 5432 failed: Network is unreachable
2026-04-24T01:41:25.79781572Z 	Is the server running on that host and accepting TCP/IP connections?
2026-04-24T01:41:25.79781864Z 

v0.1.4
    # ipaddress.ip_address(s) succeeds for valid IPv4 or IPv6 literals; ValueError if s is
    # a hostname (e.g. db.*.supabase.co) or otherwise not a valid IP string. Refactored to _host_is_literal_ip().

v0.1.5
2026-04-24T01:59:31.748121151Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 58, in __init__
2026-04-24T01:59:31.748198777Z     self.setup(app)
2026-04-24T01:59:31.748205268Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 118, in setup
2026-04-24T01:59:31.748324427Z     self.app.wsgi()
2026-04-24T01:59:31.7483676Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 67, in wsgi
2026-04-24T01:59:31.748468108Z     self.callable = self.load()
2026-04-24T01:59:31.748477819Z                     ^^^^^^^^^^^
2026-04-24T01:59:31.748481559Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
2026-04-24T01:59:31.748564846Z     return self.load_wsgiapp()
2026-04-24T01:59:31.748569506Z            ^^^^^^^^^^^^^^^^^^^
2026-04-24T01:59:31.748586748Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
2026-04-24T01:59:31.748715808Z     return util.import_app(self.app_uri)
2026-04-24T01:59:31.748722809Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:59:31.748726929Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/util.py", line 371, in import_app
2026-04-24T01:59:31.748880931Z     mod = importlib.import_module(module)
2026-04-24T01:59:31.748891382Z           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:59:31.748894842Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/importlib/__init__.py", line 90, in import_module
2026-04-24T01:59:31.749106719Z     return _bootstrap._gcd_import(name[level:], package, level)
2026-04-24T01:59:31.74911801Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:59:31.7491221Z   File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
2026-04-24T01:59:31.74912539Z   File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
2026-04-24T01:59:31.749128441Z   File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
2026-04-24T01:59:31.749131571Z   File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
2026-04-24T01:59:31.749134461Z   File "<frozen importlib._bootstrap_external>", line 995, in exec_module
2026-04-24T01:59:31.749137301Z   File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
2026-04-24T01:59:31.749267701Z   File "/opt/render/project/src/app.py", line 183, in <module>
2026-04-24T01:59:31.749272792Z     ensure_schema_and_seed()
2026-04-24T01:59:31.749274952Z   File "/opt/render/project/src/app.py", line 150, in ensure_schema_and_seed
2026-04-24T01:59:31.749367809Z     conn = get_conn()
2026-04-24T01:59:31.749396082Z            ^^^^^^^^^^
2026-04-24T01:59:31.749400512Z   File "/opt/render/project/src/app.py", line 119, in get_conn
2026-04-24T01:59:31.74950172Z     kwargs = _connect_kwargs_from_database_url(url)
2026-04-24T01:59:31.749517171Z              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:59:31.749521672Z   File "/opt/render/project/src/app.py", line 71, in _connect_kwargs_from_database_url
2026-04-24T01:59:31.749619179Z     parsed = urlparse(url)
2026-04-24T01:59:31.74962529Z              ^^^^^^^^^^^^^
2026-04-24T01:59:31.74963151Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/urllib/parse.py", line 395, in urlparse
2026-04-24T01:59:31.749781722Z     splitresult = urlsplit(url, scheme, allow_fragments)
2026-04-24T01:59:31.749788203Z                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:59:31.749794773Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/urllib/parse.py", line 500, in urlsplit
2026-04-24T01:59:31.749980978Z     _check_bracketed_host(bracketed_host)
2026-04-24T01:59:31.749994989Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/urllib/parse.py", line 446, in _check_bracketed_host
2026-04-24T01:59:31.750164022Z     ip = ipaddress.ip_address(hostname) # Throws Value Error if not IPv6 or IPv4
2026-04-24T01:59:31.750178653Z          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T01:59:31.750182214Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/ipaddress.py", line 54, in ip_address
2026-04-24T01:59:31.750366808Z     raise ValueError(f'{address!r} does not appear to be an IPv4 or IPv6 address')
2026-04-24T01:59:31.750371799Z ValueError: 'my-boss-has-a-5head' does not appear to be an IPv4 or IPv6 address
2026-04-24T01:59:43.34373807Z ==> Exited with status 1
2026-04-24T01:59:43.346470243Z ==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
2026-04-24T01:59:51.057224409Z ==> Running 'gunicorn app:app'

# v0.1.5 fix: ValueError is NOT from our code — urllib.parse sees [my-boss-has-a-5head] as a
# bracketed host (invalid IPv6). Cause: DATABASE_URL used [ ] around a non-IPv6 host, or a
# password with unencoded special chars. Use Supabase URI as-is; don't wrap db.*.supabase.co in brackets.
# App now catches urlparse ValueError and raises a clearer RuntimeError.

v0.1.7
2026-04-24T02:15:24.228501232Z     sys.exit(run())
2026-04-24T02:15:24.228564243Z              ^^^^^
2026-04-24T02:15:24.228580604Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 67, in run
2026-04-24T02:15:24.228686857Z     WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=prog).run()
2026-04-24T02:15:24.228729568Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 236, in run
2026-04-24T02:15:24.228899803Z     super().run()
2026-04-24T02:15:24.228904752Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 72, in run
2026-04-24T02:15:24.229021656Z     Arbiter(self).run()
2026-04-24T02:15:24.229039896Z     ^^^^^^^^^^^^^
2026-04-24T02:15:24.229042856Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 58, in __init__
2026-04-24T02:15:24.22917319Z     self.setup(app)
2026-04-24T02:15:24.229215071Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 118, in setup
2026-04-24T02:15:24.229331794Z     self.app.wsgi()
2026-04-24T02:15:24.229349875Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 67, in wsgi
2026-04-24T02:15:24.229467908Z     self.callable = self.load()
2026-04-24T02:15:24.229606722Z                     ^^^^^^^^^^^
2026-04-24T02:15:24.229622342Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
2026-04-24T02:15:24.229726545Z     return self.load_wsgiapp()
2026-04-24T02:15:24.229734755Z            ^^^^^^^^^^^^^^^^^^^
2026-04-24T02:15:24.229739315Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
2026-04-24T02:15:24.229866669Z     return util.import_app(self.app_uri)
2026-04-24T02:15:24.22988349Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:15:24.22989053Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/util.py", line 371, in import_app
2026-04-24T02:15:24.230082745Z     mod = importlib.import_module(module)
2026-04-24T02:15:24.230093945Z           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:15:24.230097045Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/importlib/__init__.py", line 90, in import_module
2026-04-24T02:15:24.230228229Z     return _bootstrap._gcd_import(name[level:], package, level)
2026-04-24T02:15:24.23027733Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:15:24.2302813Z   File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
2026-04-24T02:15:24.230283341Z   File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
2026-04-24T02:15:24.230294731Z   File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
2026-04-24T02:15:24.230298371Z   File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
2026-04-24T02:15:24.230300391Z   File "<frozen importlib._bootstrap_external>", line 995, in exec_module
2026-04-24T02:15:24.230302421Z   File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
2026-04-24T02:15:24.230308871Z   File "/opt/render/project/src/app.py", line 192, in <module>
2026-04-24T02:15:24.230476776Z     ensure_schema_and_seed()
2026-04-24T02:15:24.230482146Z   File "/opt/render/project/src/app.py", line 159, in ensure_schema_and_seed
2026-04-24T02:15:24.230661291Z     conn = get_conn()
2026-04-24T02:15:24.230685721Z            ^^^^^^^^^^
2026-04-24T02:15:24.230689382Z   File "/opt/render/project/src/app.py", line 129, in get_conn
2026-04-24T02:15:24.230809475Z     return psycopg2.connect(cursor_factory=extras.RealDictCursor, **kwargs)
2026-04-24T02:15:24.230861556Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:15:24.230865817Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/psycopg2/__init__.py", line 122, in connect
2026-04-24T02:15:24.23099046Z     conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
2026-04-24T02:15:24.231038491Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:15:24.231043491Z psycopg2.OperationalError: connection to server at "db.vqawahybaepcnfehlimn.supabase.co" (2406:da18:243:7429:9ba0:fb3:6f36:99aa), port 5432 failed: Network is unreachable
2026-04-24T02:15:24.231046751Z 	Is the server running on that host and accepting TCP/IP connections?
2026-04-24T02:15:24.231049811Z 
2026-04-24T02:15:26.888096345Z ==> Exited with status 1
2026-04-24T02:15:26.89288247Z ==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys

where database url = postgresql://postgres:my-boss-has-a-5head@db.vqawahybaepcnfehlimn.supabase.co:5432/postgres
secret key is set to a random password

# v0.1.7 fix: stronger IPv4 resolution (AF_INET + gethostbyname); if still no A record, use pooler URI.
# If A exists but connect still used v6, we no longer fall back to host-only; must set hostaddr.

v0.1.8
# Document Session pooler in .env.example + README: postgres.<ref> @ aws-REGION.pooler.supabase.com:5432
# (Supabase: IPv4 proxied; use for Render). RuntimeError text updated for Session vs Transaction 6543.

v0.1.8
from supabase connection string session pooler:
1. Connection string
Copy the connection details for your database.
Details:
Shared Pooler
Only use on a IPv4 networkSession pooler connections are IPv4 proxied for free.
Use Direct Connection if connecting via an IPv6 network.
host:aws-1-ap-southeast-1.pooler.supabase.com
port:5432
database:postgres
user:postgres.vqawahybaepcnfehlimn
Code:
File: Code
```
postgresql://postgres.vqawahybaepcnfehlimn:[YOUR-PASSWORD]@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
```

v0.1.9
2026-04-24T02:29:10.030304335Z   File "/opt/render/project/src/.venv/bin/gunicorn", line 8, in <module>
2026-04-24T02:29:10.031128066Z     sys.exit(run())
2026-04-24T02:29:10.031140437Z              ^^^^^
2026-04-24T02:29:10.031145657Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 67, in run
2026-04-24T02:29:10.031151747Z     WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=prog).run()
2026-04-24T02:29:10.031155647Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 236, in run
2026-04-24T02:29:10.031159757Z     super().run()
2026-04-24T02:29:10.031163917Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 72, in run
2026-04-24T02:29:10.031168107Z     Arbiter(self).run()
2026-04-24T02:29:10.031174758Z     ^^^^^^^^^^^^^
2026-04-24T02:29:10.031178988Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 58, in __init__
2026-04-24T02:29:10.031183338Z     self.setup(app)
2026-04-24T02:29:10.031187858Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 118, in setup
2026-04-24T02:29:10.031202938Z     self.app.wsgi()
2026-04-24T02:29:10.03127005Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 67, in wsgi
2026-04-24T02:29:10.031357772Z     self.callable = self.load()
2026-04-24T02:29:10.031367533Z                     ^^^^^^^^^^^
2026-04-24T02:29:10.031372493Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
2026-04-24T02:29:10.031472746Z     return self.load_wsgiapp()
2026-04-24T02:29:10.031491946Z            ^^^^^^^^^^^^^^^^^^^
2026-04-24T02:29:10.031497066Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
2026-04-24T02:29:10.031605179Z     return util.import_app(self.app_uri)
2026-04-24T02:29:10.03164025Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:29:10.031672691Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/gunicorn/util.py", line 371, in import_app
2026-04-24T02:29:10.031884566Z     mod = importlib.import_module(module)
2026-04-24T02:29:10.031918117Z           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:29:10.031950428Z   File "/opt/render/project/python/Python-3.12.6/lib/python3.12/importlib/__init__.py", line 90, in import_module
2026-04-24T02:29:10.032120552Z     return _bootstrap._gcd_import(name[level:], package, level)
2026-04-24T02:29:10.032198005Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:29:10.032204265Z   File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
2026-04-24T02:29:10.032208345Z   File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
2026-04-24T02:29:10.032221735Z   File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
2026-04-24T02:29:10.032225705Z   File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
2026-04-24T02:29:10.032229765Z   File "<frozen importlib._bootstrap_external>", line 995, in exec_module
2026-04-24T02:29:10.032237415Z   File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
2026-04-24T02:29:10.032241576Z   File "/opt/render/project/src/app.py", line 225, in <module>
2026-04-24T02:29:10.03238933Z     ensure_schema_and_seed()
2026-04-24T02:29:10.03240162Z   File "/opt/render/project/src/app.py", line 192, in ensure_schema_and_seed
2026-04-24T02:29:10.032537463Z     conn = get_conn()
2026-04-24T02:29:10.032560624Z            ^^^^^^^^^^
2026-04-24T02:29:10.032564364Z   File "/opt/render/project/src/app.py", line 162, in get_conn
2026-04-24T02:29:10.032672237Z     return psycopg2.connect(cursor_factory=extras.RealDictCursor, **kwargs)
2026-04-24T02:29:10.032702338Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:29:10.032807701Z   File "/opt/render/project/src/.venv/lib/python3.12/site-packages/psycopg2/__init__.py", line 122, in connect
2026-04-24T02:29:10.032938284Z     conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
2026-04-24T02:29:10.032980245Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-04-24T02:29:10.032997166Z psycopg2.OperationalError: connection to server at "3.1.167.181", port 5432 failed: FATAL:  Tenant or user not found
2026-04-24T02:29:10.033000386Z 
2026-04-24T02:29:12.887311613Z ==> No open ports detected, continuing to scan...
2026-04-24T02:29:13.278129785Z ==> Docs on specifying a port: https://render.com/docs/web-services#port-binding

# v0.1.9: FATAL Tenant or user not found = pooler got user "postgres" only; need postgres.<project-ref>.
# App validates pooler host + pre-connect; maps OperationalError to RuntimeError with hint.

v0.2.0
update: supabase connection issues have been fixed and render now deploys with supabase 
data migration and restructuring:
1. remove all seeded data and the seed sql file
2. insert all data from the databse import folder into the database once， looking through the recipe sheet and analysing thoroughly to rework the recipe feature on the web app to include ingredient readiness (reading from inventory), recipe steps (ticked off 1 by 1), and portioning/ratios function to adjust ingredients needed based on desired output
3. link past orders and current new orders to the financial sheet to track cash inflow and costs side-by-side. 
4. add a data anlysis page that looks at the statistics of each product (sort by matcha, coffee, by flavour, etc.), analyse regular customers, etc.
5. end the migration phase by removing the import/export page, adding an option to export as .csv under every database page. refactor and optimise all tables in the database, inspired by the current data structure from the provided files but optimised for relational databage usage.

new features:
1. anti-cold start using the keep-alive monitor and an optimised cold-start. downtimes are on saturday to monday, where little to no users access the website. hotspots are wednesday, thursday and friday where multiple instances will be opened simultaneously across the span of time
2. (beta) add an ordering system designed for customers. keep the ordering process simple and streamlined. payment, left at the bottom, allows options such as "paynow" via QR code or via mobile number, or pay via cash/in-person during collection. auth/separate interfaces for customer/employees are not necessary yet as this page is still in development
3. reframe UI design in preparation for a rework involving substituing various titles/logos with images, adding motifs in the background and sprucing up the entire website in general (major UI rework will only come much later)

v0.2.1
patches:
1. using import_initial_data is not a very intelligent solution. optimise for simplicity by directly inserting the .csv data into the database with sql run on supabase 
2. orders on customer and employee side should be actual products, not blobs of text that ruin the entire point of using a database. latte products follow the naming convention of [coffe/matcha][flavour], and special items are standalone items. every single data point/selection should be a fixed drop-down selection, not text to be input by employees or customers. the only situation where there will be text input is for integers or for remarks/special requests on orders 
3. recipe should be an interactive table where a new ingredient can be added (a drop-down selection of ingredients from inventory) and a portion specification. 
4. where are the supplier and source cost columns in inventory?
5. move prep components table out of the inventory page into the dashboard and integrate its data with the analytics page to analyse past orders 
6. some data may be inconsistent; whipping cream sometimes written as heavy cream, honey buttercream matcha latte sometimes written as honey matcha latte, etc. gather and fix all inconsistent data across tables MANUALLY in the .csv files before insertion into database MANUALLY (no funny code that doesnt run without 5 dependencies and 3 hours of debugging)
7. make naming conventions modifiable; ingredient names can be modified, product names can be modified on the order/inventory tables, etc. 

v0.2.2
patches:
1. insert data from financial tracker csv into the database. the first few rows are formatted in a non-standard way and the data needs to be extracted and inseted differently. there are 2 main tables in the csv file, 1 for orders received (can be inferred from the table column names) and expenses list beside it. these 2 tables need to be separated before insertion into database. clean up data while inserting it. find the simplest, most optimal method of inserting the data into the database that has a high chance of succeeding
2. flavours should also be fixed into drop-down tables. how for the recipe system works, look at the mug club recipes.txt file. we are going to restructure the current recipe framework in the website (it is currently horrendous, whoever said we are close to AGI is clearly lying). every recipe has a required ingredient list table with dropdowns and function to add rows. before the food item can be made, there needs to be a checkbox table for ingredient preparation. after ingredient prep, insert another recipe steps list. recipes may have more than 1 component that needs to be made separately and then assembled at the end in final assembly steps. add remarks for every single list/table in a recipe card.
3. anti-cold start pings do not work; look into it and debug it with me step-by step (can stretch to v0.2.3)
4. products and recipes page should be merged; products come from creating recipes and are then assigned their productID, and using the ingredients used per serving of the product, calculate margins and display on product/recipe card. these margins data go into the finance and analytics data tables as well.
5. selling price of products will also be attached onto the product/recipe card. on the shop page, there should be a interactive list to add products (dropdown selection with images, insert placeholder images of a cup image for now) and a short description and price attached to the product. final price will be tabulated at the bottom and lead to the payment options section. insert a placeholder image under the paynow QR with the paynow mobile number below thr QR code, then remove the paynow mobile number text input as that is not how the paynow system works in singapore

v0.2.3
patches:
1. implement anti-cold start features and devise troubleshooting plan
2. put the cash inflow and expenditure table parallel, side-by-side instead
3. preview on order page does not update to show cash values. 
4. product cards should be displayed on the dropdown selection menu instead of adding a separate menu underneath everything 
5. there should be a special request/remark input for every individual product
6. if paynow is selected, add a footnote on the payment card to indicate that order will only be processed after payment is verified
7. do not display employee IDs in the staff list. change page name to "staff"
8. re-parse the financial data to extract a customer name column, product column and change "person" to "payment" with 2 states: "paynow" and "cash", then add another column to indicate payment status. use a new row for every singular product bought. data can be normalised to 3NF in other pages, but financial sheet should stay as 1NF raw data for low level administrative work
9. in the orders table, payment method should be paynow or cash (from the shop order form), and payment should stay the same. shift order status to the right-most of the table and let it take on 3 different states of pending, processing and completed. to simplify UX, make order status and payment buttons that morph to the next state when clicked (e.g. upon creation order shows "pending" and "unpaid" button, but after clicking order status it changes to "processing" then "completed"). orders on the order page should disappear once order status is completed and payment is paid.
10. finance sheet should be updated with the orders page; once an order is finished (order status completed, payment paid), the order should go into the finance table and ready to use on other pages
11. why is there a linked order column in the finance sheet? all orders are to be as autonomous as possible, with indexing done by the relational database and by the web app's own algorithm
12. rework the product page again - the organisation system is still messed up; introduce a new object "component" that replaces the product recipe card. each component is created with a recipe and name. first step of creation is product name, component type (dropdown selection of currently registered components, with another function to add new component type). after that should be a list (similar to the order page ordering list) to add ingredients (from inventory) with amount in grams. below that should be a similar list that instead adds component steps 1 by 1. think of component recipes as the end branch of a product recipe, where the product recipe's "ingredients" are the components that have their own recipes. some product recipes also have additional ingredients that are not components, so components can be treated more like a ingredient from the inventory (especially for flavour components). 
13. turn the products page into a recipe databank (do not rename) with a menu at the top that shows all the products, and clicking them should lead to the product's specific recipe

notes:
ensure all data is consistent and normalised properly