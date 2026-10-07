# How to work on this project

This guide is for everyone, including people who have never collaborated on GitHub.
Do the [one-time setup](#2-one-time-setup) once, then follow the [everyday workflow](#3-everyday-workflow) for every task.
Stuck? Ask in the team channel. Getting stuck on Git is normal.

1. [How we work](#1-how-we-work)
2. [One-time setup](#2-one-time-setup)
3. [Everyday workflow](#3-everyday-workflow)
4. [Adding a data source](#4-adding-a-data-source)
5. [Reviewing a pull request](#5-reviewing-a-pull-request)
6. [Good habits](#6-good-habits)
7. [When things go wrong](#7-when-things-go-wrong)
8. [Cheat sheet](#8-cheat-sheet)

## 1. How we work

A **branch** is a separate copy of the project where you can make changes without affecting anyone else.

| Branch | What it is |
|---|---|
| `main` | The stable version, published as the website. Updated from `develop` at milestones |
| `develop` | The **working branch**, where everyone's finished work comes together |
| `feature/...` | **Your** branch for one task, for example `feature/drought-map` |

For every task: create a feature branch from `develop` → commit your changes → push → open a
**pull request** into `develop` → a teammate reviews → merge.

**Golden rules**

- Never commit directly to `main` or `develop`. Always use a feature branch.
- One branch per task, and keep tasks small.
- Pull requests always go **into `develop`**.

## 2. One-time setup

### 2.1 Install the tools

- **Git**: on macOS, run `git --version` in the Terminal and accept the install if asked.
  On Windows, install [Git for Windows](https://git-scm.com/download/win) and use "Git Bash" for the commands below.
- **Conda**: install [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
- **GitHub CLI** (`gh`), for logging in to GitHub: [cli.github.com](https://cli.github.com) (macOS: `brew install gh`).
- **An editor**: we recommend [VS Code](https://code.visualstudio.com) with the *Python*, *Jupyter* and *Quarto* extensions.

### 2.2 Connect Git to GitHub

Use the email of your GitHub account:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
gh auth login
```

For `gh auth login`, choose **GitHub.com**, **HTTPS**, **Yes**, **Login with a web browser**, then follow the browser.

### 2.3 Download (clone) the project and create the environment

```bash
cd ~/Documents            # or wherever you keep your projects
git clone https://github.com/ostojanovic/capstone-cohort10.git
cd capstone-cohort10
conda env create -f environment.yml
conda activate capstone-cohort10
python -m ipykernel install --user --name capstone-cohort10 --display-name "Python (capstone-cohort10)"
```

The environment contains Python, Quarto and all our libraries. Creating it takes a few minutes.
The last line lets Quarto and Jupyter use it.

> Every time you open a new terminal, run `conda activate capstone-cohort10` first.

### 2.4 Add your logins (only for NASA data)

Logins live in a file called `.env`, which Git ignores, so passwords never end up on GitHub.

1. Create a free NASA Earthdata account at <https://urs.earthdata.nasa.gov/users/new>.
2. Run `cp .env.example .env`, open `.env` and fill in `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`.
3. Check it with `python -m capstone.earthdata`. It should print `Earthdata login works.`

> ⚠️ Never commit `.env` and never put passwords in code or notebooks. When a new data source needs a key,
> add its variable name (without the value) to `.env.example`.

### 2.5 Check that everything works

Run `quarto preview`. Your browser should open the website. Press `Ctrl + C` in the terminal to stop it.

## 3. Everyday workflow

**1. Start from the latest `develop`**

```bash
git checkout develop
git pull
```

**2. Create your feature branch.** Use a short name in lowercase with dashes:

```bash
git checkout -b feature/drought-monitor-layer
```

**3. Make your changes**, and check the result with `quarto preview`.

**4. Commit** (save a snapshot). Check what changed, choose the files, and describe the change:

```bash
git status
git add index.qmd src/capstone/topics.py
git commit -m "Add US Drought Monitor layer to drought map"
```

Commit whenever a small piece works. Start messages with a verb ("Add …", "Fix …", "Update …").
Add files by name rather than `git add .`, so nothing slips in by accident.

**5. Push** (upload your branch to GitHub):

```bash
git push -u origin feature/drought-monitor-layer    # first time; afterwards just: git push
```

**6. Open a pull request.** On the [repository page](https://github.com/ostojanovic/capstone-cohort10), click
**Compare & pull request**. Check that it says **`base: develop`**. Describe what you changed and how to check it
(screenshots help for maps), pick a teammate under **Reviewers**, and click **Create pull request**.

**7. Respond to review.** Keep working on the same branch, then commit and `git push` again.
The pull request updates automatically.

**8. Merge and clean up.** Once approved, click **Merge pull request** and **Delete branch** on GitHub. Then:

```bash
git checkout develop
git pull
git branch -d feature/drought-monitor-layer
```

## 4. Adding a data source

Each dataset on the website is one Python file in `src/capstone/sources/`. No notebook needed.
The step-by-step guide, with a complete example, is in
**[src/capstone/sources/README.md](src/capstone/sources/README.md)**.

## 5. Reviewing a pull request

1. Open the pull request and read the description.
2. In **Files changed**, click a line to comment on it.
3. To try it yourself: `gh pr checkout <number>`, then `quarto preview`.
4. Finish with **Review changes** → *Comment*, *Approve* or *Request changes*.

Be kind and specific: "The legend is hard to read, maybe a darker blue?" helps more than "colors are bad".

## 6. Good habits

- **Don't commit data.** Downloads go into `data/raw/` and `data/processed/`, which Git ignores.
- **Don't commit secrets.** Logins belong in `.env`.
- **Commit `_freeze/` changes.** Quarto stores the results of executed pages there.
- **New Python package?** Add it to `environment.yml` and mention it in the pull request.
  Everyone else then runs `conda env update -f environment.yml --prune`.
- **Branch older than a few days?** Bring in the latest work: `git checkout develop && git pull`, then
  `git checkout <your-branch>` and `git merge develop`.
- **Notebooks are hard to merge.** Agree on who edits which notebook.

## 7. When things go wrong

If you're unsure, stop and ask. Nothing is lost unless you force something. **Never use `git push --force`.**

**Merge CONFLICT**: you and someone else changed the same lines. Open each file listed by `git status`,
choose the correct text between the `<<<<<<<`, `=======` and `>>>>>>>` markers and delete the markers
(VS Code has "Accept current / incoming / both" buttons). Then `git add <file>` and `git commit`.

**Committed on `develop` by accident** (not pushed yet): move the commit to a new branch.

```bash
git checkout -b feature/my-work
git checkout develop
git reset --hard origin/develop
git checkout feature/my-work
```

**Throw away uncommitted changes to a file**: `git restore <file>`.

**`git push` is rejected**: check you're on the right branch with `git branch`, then `git pull` and push again.

**Quarto says `No module named 'capstone'`**: the page needs `jupyter: capstone-cohort10` in its header
(copy it from `index.qmd`), or you skipped the last command in [2.3](#23-download-clone-the-project-and-create-the-environment).

## 8. Cheat sheet

| I want to… | Command |
|---|---|
| See where I am and what changed | `git status` |
| Get the latest `develop` | `git checkout develop` then `git pull` |
| Start a new task | `git checkout -b feature/short-name` |
| Save a snapshot | `git add <files>` then `git commit -m "Message"` |
| Upload my branch | `git push -u origin feature/short-name` (first time), then `git push` |
| Open a pull request | GitHub website, or `gh pr create --base develop` |
| Try someone's pull request | `gh pr checkout <number>` |
| Activate the environment | `conda activate capstone-cohort10` |
| Preview the website | `quarto preview` |
