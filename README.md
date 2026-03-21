# git-recap

Run `git-recap` in any repo and get a plain-English summary of what you've been working on. Useful for standups, weekly reviews, or just figuring out where the last three hours went.

Everything runs locally through Ollama. No API keys, no data leaving your machine.

---

## Install

```bash
pip install git-recap
```

Requires [Ollama](https://ollama.ai) running locally with at least one model pulled:

```bash
ollama pull qwen2.5:3b
```

---

## Usage

```bash
# summarize the last week in the current repo
git-recap

# just today
git-recap --since "1 day ago"

# different repo
git-recap --repo ~/projects/myapp

# skip the LLM, just list the commits
git-recap --raw

# use a different model
git-recap --model llama3.2:3b

# save the summary to a file
git-recap --output recap.txt

# filter by author
git-recap --author "kamil"
```

Example output:

```
Found 6 commit(s) since '1 week ago'. Summarizing...

╭─ Recap — 6 commit(s) since '1 week ago' ────────────────────────────────────╮
│                                                                              │
│  This week focused on the authentication flow. Added JWT token handling,     │
│  fixed a redirect bug that appeared after login, and cleaned up the user     │
│  model. Also spent some time on the test setup — integration tests now       │
│  run against a real database instead of mocks.                               │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## Options

| flag | default | description |
|------|---------|-------------|
| `--repo`, `-r` | `.` | path to the git repository |
| `--since`, `-s` | `1 week ago` | time range (any git date string) |
| `--author`, `-a` | — | filter by author name or email |
| `--model`, `-m` | `qwen2.5:3b` | Ollama model to use |
| `--raw` | — | skip the LLM, just print commits |
| `--output`, `-o` | — | save summary to a file |

---

## How it works

1. Runs `git log` with your filters
2. Collects commit messages and changed files
3. Sends them to Ollama with a short prompt
4. Prints the result

The prompt asks the model to group related changes and write in plain language — no bullet points, no headers, just a few readable sentences.

---

## Development

```bash
git clone https://github.com/kpalubicki/git-recap.git
cd git-recap
pip install -e ".[dev]"
pytest
```

---

## License

MIT
