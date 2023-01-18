# Todoist auto labeling

> This is my original REST implementation. Does everything is says on the tin. No issues except that I needed some of the sync functionality to use the core in another project.

This is a partial replacement for the wonderful [Autodoist](https://github.com/Hoffelhas/autodoist) app by [Hoffelhas](https://github.com/Hoffelhas). Changes to the Todoist API temporarily broke [Autodoist](https://github.com/Hoffelhas/autodoist). I wrote this to keep "next_action" alive while [Autodoist](https://github.com/Hoffelhas/autodoist) was down and as an example for [an article on building and hosting a "bot"](https://www.foundationsafety.com/deploy-your-first-baby-bot-on-heroku).

> [Hoffelhas](https://github.com/Hoffelhas) has since restored [Autodoist](https://github.com/Hoffelhas/autodoist) to its former glory. This project works, and I will continue to use and maintain it, but in your shoes I'd probably defer to the [Lindy Rule](https://en.wikipedia.org/wiki/Lindy_effect) and go with [Autodoist](https://github.com/Hoffelhas/autodoist), the more established project.

This project reproduces (and tweaks) the functionality of [Autodoist](https://github.com/Hoffelhas/automdoist) that I rely on. It finds (sub)projects, sections, or (sub)tasks with special markers (that you select) and applies or removes tags with one of three schemes: serial, parallel (more below), or all.

Don't miss the ("or removes") part of that. This is a dynamic system. If you remove a marker, the labels will be removed a few seconds later. So, feel empowered to @park or @activate or @whatever-you-like any project, section, or task for half an hour if that's useful to you. But know that any labels you use with this program belong to the program. The program will freely add and remove these labels per the logic you select when running the script. If you're not sure, see the `--dry-run` argument.


    -h, --help            show this help message and exit
    -a API_KEY, --api_key API_KEY
                          REQUIRED: your Todoist API Key.
    -s [SERIAL ...], --serial [SERIAL ...]
                          format "label suffix". Add [label] to the next (sub)task beneath or at any item with a name ending in [suffix]. Example:
                          "next_action -n" will add the label `@next_action` to the next task beneath or at any project, section, or task with a name
                          ending in -n.
    -p [PARALLEL ...], --parallel [PARALLEL ...]
                          format "label suffix". Add [label] to all childless (sub)tasks beneath or at any item with a name ending in [suffix]. Example:
                          "actionable -a" will add the label `@actionable` to all childless (sub)tasks beneath or at any project, section, or task with a
                          name ending in -a.
    -l [ALL ...], --all [ALL ...]
                          format "label suffix". Add [label] to all (sub)tasks beneath or at any item with a name ending in [suffix]. Example: "parked -p"
                          will add the label `@parked` to all (sub)tasks beneath or at any project, section, or task with a name ending in -p.
    -d DELAY, --delay DELAY
                          Specify the delay in seconds between syncs (default 5).
    -n, --dry-run         Do not update Todoist. Describe changes and exit.
    -o, --once            Update Todoist once then stop watching for changes.

### Serial

Apply a label to the next (sub)task (leftmost leaf).

<figure>
 <img src="https://www.foundationsafety.com/assets/img/remote_hosting/hoffelhas_serial.gif" style="margin:auto;" alt="serial processing">
 <figcaption align="center">Image generously provided by <a href="https://github.com/Hoffelhas">Hoffelhas</a> under the MIT license.</figcaption>
</figure>

### Parallel

Apply a label to all (sub)tasks with no descendent tasks (all leaves).

<figure>
 <img src="https://www.foundationsafety.com/assets/img/remote_hosting/hoffelhas_parallel.gif" style="margin:auto;" alt="parallel processing">
 <figcaption align="center">Image generously provided by <a href="https://github.com/Hoffelhas">Hoffelhas</a> under the MIT license.</figcaption>
</figure>

### All

You can use naming conventions for sections and then filter to find, for example, all sections named Parked. The --all parameter allows using a suffix instead so you can use descriptive section names. For example, you can `@parked` sections "waiting on supplies", "waiting on approval", "if the client ever calls back", and "probably never" across multiple projects then see all `@parked` tasks in the same filter.

### important note

The meaning of "next task" is not objective. Todoist doesn't represent tasks in a strict hierarchy of

    Project -> Section -> Task

Two tasks under the same project might be

    Project -> Subproject -> Section -> Task1
    # and
    Project -> Task2

So, even though Todoist objects have an order attribute, there is no canonical ordering of child nodes of different types. When comparing different node types, I give higher priority to shorter branches. So, in this case, Task2 would be selected as "next task" over Task1. For a typical use case (one project with multiple sections, all tasks in a section), the "next task" will be the task in the upper-left corner of the board view.

The full hierarchy is:

    Highest priority first:

        * Project -> Task
        * Project -> Section -> Task
        * Project -> Subproject -> Task
        * Project -> Subproject -> Section -> Task
        * Project -> Subproject ... Subproject -> Task
        * Project -> Subproject ... Subproject -> Section -> Task

Further, Todoist will nest any number of subprojects and subtasks, so there is no one true answer to leftmost leaf.

## Use

This can be run as a script with Python with the two dependencies in requirements.txt. If that's new to you or you've never created a virtual environment, this will get you there:

    python -m venv venv
    ./venv/Scripts/activate
    pip install todoist_api_python paragraphs
    python main.py

That will print the instructions for putting together an actual command. The command I use is

    python main.py -a <my api key> --serial "next_action -n" "blocking -b" --parallel "actionable -a" -all "parked -p"

I suggest following the "dash letter" suffix style. You can also use "-word" or just "word". Double symbols (e.g., the "-\-" you may be accustomed to from [Autodoist](https://github.com/Hoffelhas/autodoist)) have a potential to cause problems. [Autodoist](https://github.com/Hoffelhas/autodoist) makes provisions for some of these problems. Todoist-bot does not.

If you're not sure where to find your API key or you'd like to go further and run this program as a bot on a remote server (that's what it was built for), see this article: [Deploy Your First Baby Bot on Heroku](https://www.foundationsafety.com/deploy-your-first-baby-bot-on-heroku) on my personal website.
