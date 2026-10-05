# Cowork Team Report member v27

## Changed

- Reports are now sent through email to the Teams channel's configured email address instead of
  being posted through the Teams API.
- `config/team_channel.json` now uses `channel_email`; the installer generator is responsible for
  populating it in each team-specific bundle.
- Removed the first-run Teams link prompt, channel-ID parsing, channel memory, and
  `PostChannelMessage` fallback.
- The mandatory privacy picker and platform approval remain the final gates before the report email
  is sent.
- Scheduled runs still email the member a review reminder and never send the report to the channel
  without an interactive privacy review.
