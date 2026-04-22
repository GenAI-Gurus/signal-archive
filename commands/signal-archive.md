# signal-archive

Search the Signal Archive for existing research on a topic before running a new task.

## Usage

`/signal-archive <research question>`

## Behavior

1. Sanitizes the question to remove private content
2. Searches the public Signal Archive for similar existing research
3. Shows matching canonical pages with similarity scores and reuse counts
4. If you proceed, the result is automatically contributed to the archive

## Notes

- Searching is always free and requires no account
- Contributing requires `SIGNAL_ARCHIVE_API_KEY` (get one at https://genai-gurus.com/signal-archive/get-started)
- The `UserPromptSubmit` hook runs this search automatically before every task
