# Project context

This is the background that isn't in `CLAUDE.md`. Claude should read it at the start of a session on a new machine. Last updated 2026-10-21.

## Owner's goal and expectations
- The project started on 2026-10-21. The owner wants to use spare Claude tokens to run faceless content channels, and sessions are started with `/brainrot`.
- The owner's stated goal is about $20k/month. The owner has been told this is a long shot: most channels earn $0, and growth takes months of steady, varied output. Keep expectations realistic and report numbers honestly.

## Decisions made
- **3 formats**, each with its own YouTube channel (TikTok too, except kids): original funny stories over self-generated ball-physics visuals, "useless facts", and simple math for small kids (2+2=4 style).
- **English** content. **Free, local tools only**: ffmpeg, Kokoro TTS, Pillow, Google Fonts. No paid APIs or stock footage.
- The owner lives in **Denmark**. TikTok Creator Rewards doesn't appear to be available there (late 2026), so **YouTube Partner Program is the revenue engine** and TikTok is only for reach and as a funnel.
- The kids channel is YouTube only and always "Made for Kids".
- Content must stay clear of YouTube's reused/inauthentic-content rules: original scripts, no ripped footage, no copied Reddit posts, and variety between videos.

## Division of work
- **Owner:** account creation, phone and identity verification, accepting platform terms, payouts and tax, approving every batch before it's posted.
- **Claude:** writes scripts, renders videos, prepares post text, improves the pipeline, and keeps the logs and bibles up to date.
- **Claude never posts, uploads, publishes, or accepts terms/agreements** without the owner's explicit approval for that specific batch in the current session. Approval from an earlier session doesn't carry over. Changing channel settings also needs the owner's go-ahead.

## Anonymity rules
- The owner must not be publicly identifiable. Never use their real name, face, voice or personal email anywhere: channel names, handles, bios, descriptions, video/file metadata, commit history.
- All accounts use the dedicated project Gmail **pebblestudio630@gmail.com**. Use that, not "+" aliases of a personal address.
- Strip metadata from exported files (the pipeline already does this).
- Platforms and tax authorities privately get the owner's real identity for verification and payouts. That's unavoidable and fine.

## Current status (2026-10-21)
- **YouTube channels created:** Count With Pebkin (@CountWithPebkin, kidsmath) and Useless Fact Lab (@UselessFactLab, facts).
- **Story Ball Pit (@StoryBallPit, stories):** not created yet. The owner's identity (video) verification is under review (can take up to 24 h). Once it's approved, create it via youtube.com/channel_switcher.
- **Channel settings** (done 2026-10-21): Count With Pebkin set to Made for Kids; Useless Fact Lab set to not made for kids; both Country = Denmark; descriptions published. Channel art not done yet.
- **TikTok accounts:** not created yet (needed for stories and facts only).
- **Content:** one test video per channel is rendered (s001, f001, k001 in `ready-to-post/`). Nothing has been posted yet, and the posting logs are empty.

## Next steps
1. When the Story Ball Pit verification clears, create the channel.
2. Apply the same settings to Story Ball Pit once created (not made for kids, Denmark, description), then channel art for all three.
3. Channel art: profile pictures and banners (see `channels/roadmap.md`).
4. Create the TikTok accounts for stories and facts (owner does the sign-up and verification).
5. Owner reviews and approves the first batch, then post it and start filling in `channels/<key>/log.md`.
6. Keep running `/brainrot` sessions: build up a queue of distinct videos and work through the roadmap (music, sound effects, more backgrounds, kids long-form compilations).

## Working on two Macs
See `HOME-SETUP.md`. Short version: use one machine at a time, pull before a session, push after, and rebuild videos from the queue JSON instead of syncing them.
