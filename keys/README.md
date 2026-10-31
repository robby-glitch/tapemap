Drop your key here as one line: `anthropic.txt` (Claude, used first) or `gemini.txt` (Gemini; optional `gemini_model.txt`, default `gemini-flash-latest`). Notepad (UTF-8) or PowerShell's `echo <key> > keys\anthropic.txt` (UTF-16) both read; with neither file, Jarvis speaks the engine's own lines and says `no key`.
The daily cap is `cap.json`: `{"calls_per_day": 80}` (80 when the file is absent); past it the engine's lines show, why `cap reached`.
Everything in this folder except this README is git-ignored, and the key is read per call, never logged or printed.
