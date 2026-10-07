# How to work on this project

This guide explains how to set up the project on your computer and how we work on it together on GitHub.
It assumes you have never collaborated on GitHub before, so it goes step by step.
If something doesn't work, ask in the team channel. Getting stuck on Git is normal.

**Contents**

1. [How we work: the short version](#1-how-we-work-the-short-version)
2. [One-time setup](#2-one-time-setup)
3. [Your everyday workflow](#3-your-everyday-workflow)
4. [Reviewing a pull request](#4-reviewing-a-pull-request)
5. [Good habits](#5-good-habits)
6. [When things go wrong](#6-when-things-go-wrong)
7. [Cheat sheet](#7-cheat-sheet)

---

## 1. How we work: the short version

We use three kinds of **branches**. A branch is a separate copy of the project where you can make
changes without affecting anyone else.

| Branch | What it is | Who changes it |
|---|---|---|
| `main` | The stable version, the one that is published as the website | Only via a pull request from `develop`, at milestones |
| `develop` | The **working branch**. Everyone's finished work comes together here | Only via pull requests |
| `feature/...` | **Your** branch for one task, for example `feature/drought-map` | You |

The cycle for every piece of work is:

```
develop  ──►  create your feature branch  ──►  commit changes  ──►  push  ──►  pull request into develop  ──►  review  ──►  merge
```

**Golden rules**

- Never commit directly to `main` or `develop`. Always work on a feature branch.
- One branch per task. Keep tasks small, so a branch lives for days rather than weeks.
- Pull requests always go **into `develop`**, never into `main`.
- Pull the latest `develop` before you start something new.

---

## 2. One-time setup

You do this once per computer.

### 2.1 Install the tools

1. **Git**: on macOS, run `git --version` in the Terminal. If Git isn't installed, macOS offers to install it.
   On Windows, install [Git for Windows](https://git-scm.com/download/win) and use the "Git Bash" terminal for the commands below.
2. **Conda**: install [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
3. **GitHub CLI** (`gh`): this makes logging in to GitHub from the terminal easy.
   Install it from [cli.github.com](https://cli.github.com) (on macOS with Homebrew: `brew install gh`).
4. **An editor**: we recommend [VS Code](https://code.visualstudio.com) with the *Python*, *Jupyter* and *Quarto* extensions.

### 2.2 Get access to the repository

1. Create a [GitHub account](https://github.com/signup) if you don't have one.
2. Send your GitHub username to the project maintainer and ask to be added as a **collaborator**.
3. Accept the invitation you receive by email (or at <https://github.com/notifications>).

### 2.3 Tell Git who you are

Use the same email as your GitHub account. Your name appears on every commit you make.

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### 2.4 Log in to GitHub from the terminal

```bash
gh auth login
```

Answer the questions: **GitHub.com**, **HTTPS**, **Yes** (authenticate Git), **Login with a web browser**.
Then follow the instructions in the browser.

### 2.5 Download (clone) the project

Go to the folder where you keep your projects, then clone:

```bash
cd ~/Documents            # or wherever you want the project folder
git clone https://github.com/ostojanovic/capstone-cohort10.git
cd capstone-cohort10
```

You now have a folder `capstone-cohort10` with the whole project and its history.

### 2.6 Switch to the working branch

```bash
git checkout develop
```

`git branch` should now show `* develop`. The star marks the branch you are on.

### 2.7 Create the Python environment

The environment contains Python, Jupyter, Quarto and all the libraries we use, in the same versions for everyone.

```bash
conda env create -f environment.yml
conda activate capstone-cohort10
python -m ipykernel install --user --name capstone-cohort10 --display-name "Python (capstone-cohort10)"
```

The first command takes a few minutes. The last one makes the environment available as a Jupyter kernel.

> Every time you open a new terminal to work on the project, run `conda activate capstone-cohort10` first.
> Your prompt then starts with `(capstone-cohort10)`.

### 2.8 Check that everything works

```bash
quarto preview
```

Your browser should open the website with the map. Press `Ctrl + C` in the terminal to stop the preview.

🎉 Setup is done.

---

## 3. Your everyday workflow

Follow these steps for **every task**: a new map layer, a blog post, a notebook, a fix in the README.

### Step 1: Start from the latest `develop`

Other people may have merged work since you last looked. Get it first:

```bash
git checkout develop
git pull
```

### Step 2: Create your feature branch

Give it a short name that says what you are doing. Use lowercase and dashes:

```bash
git checkout -b feature/drought-monitor-layer
```

Naming examples: `feature/el-nino-blog-post`, `feature/cropland-notebook`, `fix/broken-legend`, `docs/update-readme`.

`git checkout -b` creates the branch **and** switches to it. Check with `git branch`.

### Step 3: Make your changes

Edit files, write your notebook or post, and check the result with `quarto preview`.

### Step 4: Look at what you changed

```bash
git status          # which files changed
git diff            # the exact lines that changed (press q to exit)
```

### Step 5: Commit, which saves a snapshot of your work

First choose which files go into the snapshot (this is called "staging"), then commit them with a message:

```bash
git add index.qmd src/capstone/topics.py      # add specific files
git commit -m "Add US Drought Monitor layer to drought map"
```

- Commit often: whenever a small piece works, commit it. Small commits are easier to review and to undo.
- Write messages that say **what** the commit does, starting with a verb: "Add …", "Fix …", "Update …".
  Avoid messages like "changes" or "stuff".
- Prefer adding files by name over `git add .`, so you don't commit things by accident.
  Always check `git status` before committing.

### Step 6: Push your branch to GitHub

Until now, your commits only exist on your computer. Pushing uploads them:

```bash
git push -u origin feature/drought-monitor-layer
```

You only need `-u origin <branch-name>` the first time you push a branch. After that, `git push` is enough.

### Step 7: Open a pull request (PR)

A pull request asks the team to review your branch and merge it into `develop`.

1. Go to <https://github.com/ostojanovic/capstone-cohort10>. GitHub shows a yellow banner with
   **"Compare & pull request"** for your recently pushed branch. Click it.
   (Or go to the **Pull requests** tab, click **New pull request**, then choose your branch.)
2. ⚠️ **Check the base branch.** At the top it must say **`base: develop`** ← `compare: feature/your-branch`.
   GitHub often preselects `main`. Change it to `develop`.
3. Write a title and a short description:
   - What did you change, and why?
   - How can a reviewer check it (for example, "run `quarto preview` and open the Droughts tab")?
   - Screenshots help a lot for maps and figures.
4. On the right, under **Reviewers**, pick at least one teammate.
5. Click **Create pull request**.

Or from the terminal: `gh pr create --base develop`.

### Step 8: Respond to review

Your reviewer may leave comments or ask for changes. To update the PR, keep working **on the same branch**,
then commit and push again:

```bash
git add <files>
git commit -m "Address review: clarify legend labels"
git push
```

The pull request updates automatically. You don't need to open a new one.

### Step 9: Merge

Once the PR is approved, click **Merge pull request** on GitHub, then **Delete branch**.

### Step 10: Clean up locally and start the next task

```bash
git checkout develop
git pull
git branch -d feature/drought-monitor-layer     # delete your local copy of the merged branch
```

Back to Step 1 for the next task.

---

## 4. Reviewing a pull request

Reviewing is as important as writing code. It is how we catch mistakes and learn from each other.

1. Open the PR on GitHub and read the description.
2. Look at the **Files changed** tab. Click a line to leave a comment there.
3. To try it on your own computer:
   ```bash
   gh pr checkout <PR number>
   quarto preview
   ```
   When you're done, switch back to your own branch with `git checkout <your-branch>`.
4. Finish with **Review changes** → *Comment*, *Approve* or *Request changes*.

Be kind and specific: "This legend is hard to read in dark mode, maybe use a darker blue?" works better than "colors are bad".

---

## 5. Good habits

- **Keep your branch up to date** when it lives longer than a few days, so you don't drift away from `develop`:
  ```bash
  git checkout develop && git pull
  git checkout feature/your-branch
  git merge develop
  ```
- **Don't commit data files.** Put downloaded data in `data/raw/` and processed data in `data/processed/`.
  Git ignores both folders. Write down in your notebook or post where the data comes from and how to download it.
- **Don't commit secrets**, such as API keys, passwords or tokens. If a data source needs a key, ask the team how to handle it.
- **Commit `_freeze/` changes.** Quarto stores the results of executed pages there, so the website can be built
  without re-running everything.
- **Adding a Python package?** Add it to `environment.yml` in your PR and mention it in the PR description.
  Everyone else then runs:
  ```bash
  conda env update -f environment.yml --prune
  ```
- **Notebooks are hard to merge.** Agree on who works on which notebook, so two people don't edit the same one at the same time.
- **Pages with Python code** need `jupyter: capstone-cohort10` in their header. Copy it from `index.qmd`.

---

## 6. When things go wrong

**"I committed on `develop` by accident"** (and haven't pushed yet): move the commit to a new branch.
```bash
git checkout -b feature/my-work          # new branch keeps your commit
git checkout develop
git reset --hard origin/develop          # put develop back to the GitHub version
git checkout feature/my-work
```

**"`git pull` or `git merge` says CONFLICT"**: you and someone else changed the same lines.
1. `git status` lists the conflicted files.
2. Open each file. You'll see blocks like:
   ```
   <<<<<<< HEAD
   your version
   =======
   their version
   >>>>>>> develop
   ```
   Edit the block so that it contains the correct final text, and delete the `<<<<<<<`, `=======` and `>>>>>>>` lines.
   VS Code has buttons for this ("Accept current", "Accept incoming", "Accept both").
3. `git add <file>` for each fixed file, then `git commit`.

If you're unsure, stop and ask. Nothing is lost until you force something.

**"I want to throw away my uncommitted changes to a file"**
```bash
git restore <file>
```

**"`git push` is rejected"**: someone pushed to your branch, or you're on the wrong branch.
Check with `git branch`, then run `git pull` and push again.

**"Quarto says `No module named 'capstone'`"**: the page is missing `jupyter: capstone-cohort10` in its header,
or you haven't run the kernel install command from step 2.7.

**Never use `git push --force`** on `develop` or `main`.

---

## 7. Cheat sheet

| I want to… | Command |
|---|---|
| See where I am and what changed | `git status` |
| See which branch I'm on | `git branch` |
| Get the latest `develop` | `git checkout develop` then `git pull` |
| Start a new task | `git checkout -b feature/short-name` |
| Save a snapshot | `git add <files>` then `git commit -m "Message"` |
| Upload my branch (first time) | `git push -u origin feature/short-name` |
| Upload more commits | `git push` |
| Open a pull request | GitHub website, or `gh pr create --base develop` |
| Try someone's pull request | `gh pr checkout <number>` |
| See the history | `git log --oneline` |
| Activate the environment | `conda activate capstone-cohort10` |
| Preview the website | `quarto preview` |
