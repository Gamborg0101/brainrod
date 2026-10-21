# Home Mac setup

How to continue this project on another Mac with Claude Code. Takes about 20 minutes, most of it downloads.

Background on the project (goals, decisions, current status): `docs/PROJECT-CONTEXT.md`.

## 1. Move the project

What travels: `CLAUDE.md`, `.claude/skills/` (the `/brainrot` command), `pipeline/`, `queue/`, `channels/`, `assets/fonts/`, `docs/`, `setup.sh`, `requirements.txt`.

What does **not** travel (each Mac makes its own):
- `.venv/` — the Python environment. It only works on the machine that created it.
- `assets/models/` — the voice model (~350 MB). `setup.sh` downloads it.
- Videos in `ready-to-post/` — they can be rebuilt any time from the `queue/` JSON files.

### Option A (recommended): private Git repository

Work Mac, once:
1. Install Git if needed: `xcode-select --install`.
2. On github.com create a **Private** repository (e.g. `brainrod`). For anonymity, use a GitHub account that is not tied to your real name, or at least keep the repo private. Don't add a README.
3. In Terminal:
   ```bash
   cd ~/Desktop/brainrod
   git init
   git config user.name "Pebble Studio"
   git config user.email "pebblestudio630@gmail.com"
   git add .
   git commit -m "Initial import"
   git branch -M main
   git remote add origin https://github.com/<account>/brainrod.git
   git push -u origin main
   ```
   The included `.gitignore` already leaves out `.venv/`, `assets/models/`, rendered videos/audio and `.DS_Store`.
   The two `git config` lines keep your personal name/email out of the commit history.

Home Mac:
```bash
xcode-select --install          # if git is missing
cd ~/Desktop
git clone https://github.com/<account>/brainrod.git
cd brainrod
git config user.name "Pebble Studio"
git config user.email "pebblestudio630@gmail.com"
```
GitHub will ask you to sign in the first time (browser login or a personal access token).

### Option B: copy through a cloud drive or USB stick

Good for a one-time move. On the work Mac:
```bash
cd ~/Desktop
zip -r brainrod.zip brainrod -x 'brainrod/.venv/*' 'brainrod/assets/models/*' 'brainrod/ready-to-post/*/*/*.mp4'
```
Put `brainrod.zip` in iCloud Drive / Dropbox / Google Drive (or on a USB stick), then unzip it on the home Mac into `~/Desktop`.

Don't keep the live project folder itself inside a synced cloud folder. The sync would also copy `.venv` and the large model files, and two machines writing to the same folder causes conflicts.

## 2. Install the prerequisites

1. **Homebrew** (if `brew --version` fails): go to https://brew.sh, paste the command into Terminal, then run the two "Next steps" lines it prints.
2. **Claude Code**: see https://docs.claude.com/en/docs/claude-code (native installer: `curl -fsSL https://claude.ai/install.sh | bash`). Log in with the same Claude account you use at work.
3. **Google Chrome**, if you don't already have it.

## 3. Run the setup script

```bash
cd ~/Desktop/brainrod
./setup.sh
```
It installs `ffmpeg` and Python 3.12 with Homebrew (if missing), creates `.venv`, installs the Python packages from `requirements.txt`, downloads the voice model and fonts (only if missing), and checks that everything imports. It's safe to run again.

## 4. Test render

```bash
.venv/bin/python pipeline/render.py queue/facts/f001.json
```
The first run takes a little longer while the voice model loads. When it finishes, open `ready-to-post/facts/f001/video.mp4`. You should see a ~37-second vertical "5 useless facts" video with a voice-over.

## 5. Claude in Chrome (for managing the channels)

1. Use a **separate Chrome profile** signed into the project Google account **pebblestudio630@gmail.com**, never your personal one (Chrome menu → profile icon → Add).
2. In that profile, install the **Claude** extension by Anthropic from the Chrome Web Store, pin it, and sign in with your Claude account.
3. In Claude Code, run `/chrome` to check that the extension is connected. If it isn't, follow the prompt.
4. Sign that profile into YouTube Studio (and TikTok once the accounts exist), so Claude can see the channels when you ask it to.

Claude never uploads, posts or accepts terms unless you approve that batch in the current session.

## 6. Start working

```bash
cd ~/Desktop/brainrod
claude
```
Starting Claude Code inside the folder loads `CLAUDE.md` (the project rules) and the `/brainrot` skill automatically. Type `/brainrot` to run a production session (or `/brainrot facts 2` for one channel, two videos).

## Keeping both machines in sync (Git option)

- **Use one machine at a time.** Don't run sessions on both Macs at the same time.
- **Before a session:** `git pull`
- **After a session:**
  ```bash
  git add -A
  git commit -m "brainrot session"
  git push
  ```
- Rendered videos are not synced. To get a video that was made on the other Mac, rebuild it: `.venv/bin/python pipeline/render.py queue/<channel>/<id>.json`.
- After you post a video, record it in `channels/<channel>/log.md`, then commit, so both machines know what's already been posted.
- If `requirements.txt` changes (a session added a package), run `./setup.sh` again on the other Mac.

## Troubleshooting

| Problem | Fix |
|---|---|
| `brew: command not found` right after installing Homebrew | Run the two "Next steps" lines Homebrew printed, or open a new Terminal window. |
| `./setup.sh: Permission denied` | `chmod +x setup.sh`, or run `bash setup.sh`. |
| Download fails or a model file looks tiny | Delete the file in `assets/models/` (or `assets/fonts/`) and run `./setup.sh` again. Check your internet connection / VPN. |
| `ModuleNotFoundError` when rendering | Run Python from the venv: `.venv/bin/python ...`, not plain `python3`. If it keeps happening: `rm -rf .venv && ./setup.sh`. |
| `.venv` copied over from the other Mac and is broken | `rm -rf .venv && ./setup.sh`. |
| `ffmpeg: command not found` | `brew install ffmpeg`, then open a new Terminal. |
| Video has no sound / voice error | Check that `assets/models/kokoro-v1.0.onnx` (~310 MB) and `voices-v1.0.bin` (~27 MB) both exist. |
| `/brainrot` doesn't show up | Start `claude` from inside the `brainrod` folder, and check that `.claude/skills/brainrot/SKILL.md` was copied (hidden folders are easy to miss when copying by hand). |
| Claude can't reach Chrome | Chrome must be open in the project profile with the extension signed in. Run `/chrome` in Claude Code. |
| `git push` rejected | Run `git pull`, then push again. If a file conflicts, ask Claude to help resolve it. |
