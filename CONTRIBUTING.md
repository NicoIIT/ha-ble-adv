# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github and Visual Studio Code devcontainer as a basis

Github is used to host code, to track issues and feature requests, as well as accept pull requests.
Visual Studio Code devcontainer is used to create an immediatly up and running workspace with everything you need to work.

Should you want to propose changes please follow:

1. Fork the repo or update your fork from original repo
2. create your working branch from `main`. We will use `dev` as working branch name in what follows. As a general rule, do NEVER work on the `main` branch of a Fork, it is the one to be kept in sync with the `main` branch of the original repo and should not contain local developments.
3. Use Visual Studio Code [devcontainer feature from githup repo](https://code.visualstudio.com/docs/devcontainers/containers#_quick-start-open-a-git-repository-or-github-pr-in-an-isolated-container-volume) to create your Visual Studio Code workspace, including =`run tasks` ready to use:
    * lint: check formatting
    * test: run python tests
    * run: starts an instance of Home Assistant with forwarded ports, available at `http://localhost:8123`
4. Perform your changes, add relevant tests and documentation.
5. Ensure `lint` and `test` tasks run OK, and that the integration is behaving OK in `run`.
6. Commit your changes and push them to your `dev` branch.
7. Open a Pull Request from your `dev` branch to the `main` branch of the original repo.
8. Check that the Actions on github run OK on your PR, correct if needed.
9. Wait for review, approval and merge.
10. Delete your working branch when the PR is merged


## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.
People *hate* one line bug reports. If they have to ask you for details, it is more likely that your bug report will never be considered.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
