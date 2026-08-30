# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## General rules

### Language
This repository is using ENGLISH as a base language. This is NOT the maintainer's mother tongue, but this is the most universal language the maintainer is able to use, so it is the official language of this component. As a consequence any issue / PR opened MUST be fully written in this language. Any contribution not expressed in this language will be automatically rejected. 

If you do not want to comply to this rule and think the maintainer could use "google translate" then do not contribute.

### Readability
Github is using [Markdown](https://docs.github.com/github/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax) language in order to help you struture your texts with titles, paragraphs, indents, software or log quoting, ... You MUST know the basis of this language in order to produce a readable contribution. Do not hesitate to use the "preview" tab in order to see what will be the result of your inputs, and correct until it is clean before submitting.


### Common vocabulary
We need to communicate, so let's use a common vocabulary so that there is no misunderstanding:
* DEVICE: the physical device that you fixed at your ceiling, usually composed of one or two Lights, and possibly a Fan
* REMOTE: a physical remote, the same kind you use to control your TV. Do NEVER use this term talking about a Phone App.
* (ANDROID) PHONE APP: an _Android_ Phone App recommended by the device manufacturer to control your device. Do NEVER use this term to talk about an IOS Phone App.
* IOS PHONE APP: an IOS Phone App recommended by the device manufacturer to control your device
* CONTROLLER: a Remote or (android / ios) Phone App
* BLUETOOTH ADAPTER: the Bluetooth Adapter you are using to send commands to your device using this component. Could be
    * 'HCI'- the bluetooth adapter of your Home Assistant Server
    * 'BLE ADV Proxy' - A `ble_adv_proxy` component deployed on an ESP32 linked to your Home Assistant
* Home Assistant vocabulary: Entity / State / ...
* (G)UI: (Graphical) User Interface - the one provided by Home Assistant usually
* PAIR: the action to send a Pairing request to the Device and complete it, following the Pairing protocol recommended by the device manufacturer. It can be done:
    * from a Remote
    * from a Phone App
    * from this component using the "Pairing" Config Flow. Do NEVER use this term when using the "Duplicate" config flow.
* DUPLICATE: the action to listen to the command emitted by an already paired controller, extract the 'codes' it contains and duplicate them to be able to send similar request based on the same 'codes' to the Device in order to control it.


We also need to be clear and precise, but let's take an example:

```
I tried to pair my light but it does not change state
```

OK so now here are the possible interpretations:
* `I tried to pair`, well it can be:
    * I used the Pairing Config Flow using the phone type "???" from the input list
    * I used the Duplicate Config Flow using my phone app paired to my device as source
    * I used the Duplicate Config Flow using my remote paired to my device as source
    *...

* `my light`:
   * the Device light
   * the HA entity main light
   * the HA entity second light
   * the Phone app representation of the Light

* `does not change state`:
   * should have changed from OFF to ON when I pressed the remote button but instead it stayed OFF
   * should have changed from OFF to ON when I pressed the HA entity main light switch but instead it stayed OFF
   * ...

As a result the maintainer will come back to you asking to clarify, so take 1 more minute and be clear directly!


### Optimizing maintainer's time
The maintainer is providing this component for FREE and can only spend a limited amount of time in helping users and improving this component. The more time he spend in reading and investigating issues the less time he can spend on improving this component and fix real issues.

As a consequence the phylosophy of the maintainer of this component is to help users ONLY after they have tried everything they could on their own using the documentation. Asking for questions that are already answered in the docs, or even worse asking where to find an info in the docs is not a good idea. If you do not agree with this way to go no problem: do not use this component or do not open issues.


### Lies, insults, ...
The best way to have everyone lose his time is to lie in Issues (saying you have read the docs whereas it is not the case) or PR templates (saying you ran the tests whereas it was not the case), or to avoid saying the truth. The maintainer just hates this, so if the maintainer sees you lied, he will block you and you will no more be able to contribute to any of his existing or future repository. Same if you insult the maintainer or show disrespect.


## Issues
Opening an issue MUST be your last solution after having tried every single advise that can be found in the documentation. As this is unfortunately not the case for most issues, the issue templates are very strict and request you to confirm every step you already checked from the doc in order to be 100% sure your issue does not already have an answer in the docs. You can think what is requested in the issue templates is not of any use for your case, this is your right, but if the maintainer requests it just provide it or your issue will be rejected.

In order to  avoid asking for useless info in issue templates, there are several different templates for different purposes: please choose the relevant one!

As the maintainer wants to enforce the read of the documentation BEFORE you open an issue, he will not provide you with any details on where you can find answer in the documentation while rejecting your issue.

If you are 100% sure you are facing a bug or that you are facing a problem which answer is NOT in the doc then you can open issues from [here](../../issues/new/choose).

The detailed reasons for rejections can be found [here](https://github.com/NicoIIT/ha-ble-adv/wiki/Why-was-my-issue-rejected%3F)


## Pull Requests
Pull requests are more than welcome but they can be very time consumming to understand and to review, so following basic steps are needed in order to optimize their handling.

### Feature Request 
Before trying to code something you should first open an issue requesting for it (Bug Report or Feature Request). As such the maintainer can discuss with you:
* if the change is a good idea or not, or if the issue is really an issue that needs a fix in this component.
* if it complies with the global architecture of the component
* if it complies with Home Assistant architecture
After you and the maintainer agree on a solution, then you can propose a Pull Request. Any Pull Request submitted without preliminary issue opened and discussed will be rejected.

### Implementation
You are free to implement a change with any tool you want (such as an AI), but you MUST:
* understand how HA works, how this component works and its design
* understand the software change you propose
* fully test your changes in Unit Tests and with a real HA server

In particular if using an AI you must be able to challenge it on your own if the implementation it proposes is breaking the architecture of this component, or is going against HA design. If you are not an experienced developer and are then not able to do so, the maintainer will need to iterativelly challenge your software for those reasons during reviews and lose a huge amount of time. He would lose less time directly interacting with the AI, so while you think you would help the maintainer by contributing, this is the countrary that happens.

To sum-up: if you are not an experienced developer, do not open PRs that modifies the core components of this software.

### Visual Studio Code devcontainer as a basis

Visual Studio Code devcontainer is used to create an immediatly up and running workspace with everything you need to work.

Should you want to propose changes please follow:

1. Fork the repo or update your fork from original repo
2. create your working branch from `main`. We will use `dev` as working branch name in what follows. As a general rule, do NEVER work on the `main` branch of a Fork, it is the one to be kept in sync with the `main` branch of the original repo and should not contain local developments.
3. Use Visual Studio Code [devcontainer feature from githup repo](https://code.visualstudio.com/docs/devcontainers/containers#_quick-start-open-a-git-repository-or-github-pr-in-an-isolated-container-volume) to create your Visual Studio Code workspace, including =`run tasks` ready to use:
    * lint: check formatting
    * test: run python tests
    * run: starts an instance of Home Assistant with forwarded ports, available at `http://localhost:8123`
    * clean: removes the Home Assistant instance
4. Perform your changes, add relevant tests and documentation.
5. Ensure `lint` and `test` tasks run OK, and that the integration is behaving OK in `run`.
6. Commit your changes and push them to your `dev` branch.
7. Open a Pull Request from your `dev` branch to the `main` branch of the original repo.
8. Check that the Actions on github run OK on your PR, correct if needed.
9. Wait for review, approval and merge.
10. Delete your working branch when the PR is merged


### Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

