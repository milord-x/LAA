^CINFO:     Shutting down
[WS] client disconnected after 0 chunks
INFO:     connection closed
INFO:     connection closed
INFO:     Waiting for background tasks to complete. (CTRL+C to force quit)
^CINFO:     Finished server process [941223]
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/usr/lib/python3.14/asyncio/runners.py", line 204, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/lib/python3.14/asyncio/runners.py", line 127, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "uvloop/loop.pyx", line 1512, in uvloop.loop.Loop.run_until_complete
  File "uvloop/loop.pyx", line 1505, in uvloop.loop.Loop.run_until_complete
    self.run_forever()
  File "uvloop/loop.pyx", line 1379, in uvloop.loop.Loop.run_forever
    self._run(mode)
  File "uvloop/loop.pyx", line 557, in uvloop.loop.Loop._run
    raise self._last_error
  File "uvloop/loop.pyx", line 476, in uvloop.loop.Loop._on_idle
    handler._run()
  File "uvloop/cbhandles.pyx", line 83, in uvloop.loop.Handle._run
  File "uvloop/cbhandles.pyx", line 63, in uvloop.loop.Handle._run
    callback(*args)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/uvicorn/server.py", line 78, in serve
    with self.capture_signals():
         ~~~~~~~~~~~~~~~~~~~~^^
  File "/usr/lib/python3.14/contextlib.py", line 148, in __exit__
    next(self.gen)
    ~~~~^^^^^^^^^^
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/uvicorn/server.py", line 339, in capture_signals
    signal.raise_signal(captured_signal)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.14/asyncio/runners.py", line 166, in _on_sigint
    raise KeyboardInterrupt()
KeyboardInterrupt

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/uvicorn/protocols/websockets/websockets_impl.py", line 239, in run_asgi
    result = await self.app(self.scope, self.asgi_receive, self.asgi_send)  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/fastapi/applications.py", line 1163, in __call__
    await super().__call__(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/applications.py", line 90, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/middleware/errors.py", line 151, in __call__
    await self.app(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/routing.py", line 660, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/routing.py", line 680, in app
    await route.handle(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/routing.py", line 350, in handle
    await self.app(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 160, in app
    await wrap_app_handling_exceptions(app, session)(scope, receive, send)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 157, in app
    await func(session)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/fastapi/routing.py", line 764, in app
    await dependant.call(**solved_result.values)
  File "/home/proxy/Projects/LAA/api/server.py", line 40, in websocket_subtitles
    await ws_endpoint(websocket, pipeline.process_bytes)
  File "/home/proxy/Projects/LAA/api/ws/subtitles.py", line 15, in ws_endpoint
    result = await process_audio_cb(raw)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/proxy/Projects/LAA/core/pipeline.py", line 196, in process_bytes
    chunk = await loop.run_in_executor(None, self._asr.transcribe_raw, audio_np)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
asyncio.exceptions.CancelledError
ERROR:    Traceback (most recent call last):
  File "/usr/lib/python3.14/asyncio/runners.py", line 204, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/usr/lib/python3.14/asyncio/runners.py", line 127, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "uvloop/loop.pyx", line 1512, in uvloop.loop.Loop.run_until_complete
    raise
  File "uvloop/loop.pyx", line 1505, in uvloop.loop.Loop.run_until_complete
    self.run_forever()
  File "uvloop/loop.pyx", line 1379, in uvloop.loop.Loop.run_forever
    self._run(mode)
  File "uvloop/loop.pyx", line 557, in uvloop.loop.Loop._run
    raise self._last_error
  File "uvloop/loop.pyx", line 476, in uvloop.loop.Loop._on_idle
    handler._run()
  File "uvloop/cbhandles.pyx", line 83, in uvloop.loop.Handle._run
    raise
  File "uvloop/cbhandles.pyx", line 63, in uvloop.loop.Handle._run
    callback(*args)
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/uvicorn/server.py", line 78, in serve
    with self.capture_signals():
         ~~~~~~~~~~~~~~~~~~~~^^
  File "/usr/lib/python3.14/contextlib.py", line 148, in __exit__
    next(self.gen)
    ~~~~^^^^^^^^^^
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/uvicorn/server.py", line 339, in capture_signals
    signal.raise_signal(captured_signal)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.14/asyncio/runners.py", line 166, in _on_sigint
    raise KeyboardInterrupt()
KeyboardInterrupt

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/starlette/routing.py", line 645, in lifespan
    await receive()
  File "/home/proxy/Projects/LAA/.venv/lib/python3.14/site-packages/uvicorn/lifespan/on.py", line 137, in receive
    return await self.receive_queue.get()
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.14/asyncio/queues.py", line 186, in get
    await getter
asyncio.exceptions.CancelledError

 ^C^CException ignored on threading shutdown:
Traceback (most recent call last):
  File "/usr/lib/python3.14/threading.py", line 1577, in _shutdown
    atexit_call()
  File "/usr/lib/python3.14/threading.py", line 1548, in <lambda>
    _threading_atexits.append(lambda: func(*arg, **kwargs))
  File "/usr/lib/python3.14/concurrent/futures/thread.py", line 31, in _python_exit
    t.join()
  File "/usr/lib/python3.14/threading.py", line 1133, in join
    self._os_thread_handle.join(timeout)
KeyboardInterrupt: 
^C⏎                                                                                                                                                                                          ✘ ❮ 05:12:02 PM
 ❯LAA ❯ 