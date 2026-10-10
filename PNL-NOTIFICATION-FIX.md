# PNL Notification Fix

- Fixed Telegram PNL message line breaks so the message renders as a readable multi-line notification.
- Added +300%, +400% (5X), and +900% (10X) default milestones.
- Synced in-memory peak/current metrics before sending alerts, so Best MC reports the current reached peak instead of stale entry values.
- Added regression tests for a $27K to $147K move (5.44X, +444.4%).

Validation: the PNL tracker regression tests passed. The full pytest suite could not be collected in this environment because `python-telegram-bot` is not installed here; install the project's requirements before running the full suite.
