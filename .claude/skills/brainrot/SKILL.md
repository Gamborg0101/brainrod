---
name: brainrot
description: Run a spare-token production session for the faceless content channels — review performance, write new scripts, render videos, prepare posts. Use when the user types /brainrot or says they have spare tokens for the channels.
---

# /brainrot session

Read `CLAUDE.md` first. Optional args: a channel key (only work on that one) or a number (videos per channel, default 3).

1. **Status (short).** For each channel, count unposted folders in `ready-to-post/<key>/` and read the latest entries in `channels/<key>/log.md`. If the owner has shared new stats (or Chrome is available and they approve), update the log and note which hooks/topics win.
2. **Plan.** Skip any channel that already has 7+ unposted videos. Pick ideas from the bible's backlog, biased toward what performs. Add fresh ideas to the backlog so it never runs dry.
3. **Write.** For each video, write `queue/<key>/<id>.json` (next free id: s###, f###, k###), following the bible. Make each one distinct — new hook style, structure, topic.
4. **Render** each script and check 3–4 frames per video. Fix anything ugly or out of sync before moving on.
5. **Improve (if tokens remain).** Pick ONE pipeline upgrade from `channels/roadmap.md`, implement it, re-render a test, and tick it off.
6. **Report.** End with a short table: channel, new videos (title + length), queue size, and anything the owner must do (e.g. "approve batch to post", "channel X is close to 1k subs").

Never post or upload without explicit approval in this session. Keep the owner anonymous.
