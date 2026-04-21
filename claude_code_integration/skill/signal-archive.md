# Signal Archive

Search the Signal Archive for existing research before running a new task.

## Usage

`/signal-archive <research question>`

## Behavior

1. Sanitizes the research question to remove any private content
2. Searches the public Signal Archive for similar existing research
3. Presents matching canonical pages with similarity scores and reuse counts
4. If you proceed with the task, the result is automatically contributed to the archive

## Setup

Set `SIGNAL_ARCHIVE_API_KEY` and `SIGNAL_ARCHIVE_API_URL` environment variables.
