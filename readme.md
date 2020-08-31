# Worklog

Worklog project accounts work time spent on tasks employee dealt with,
and simplifies this report submitting (at this point, only into 
[Atlassian / Jira](https://en.wikipedia.org/wiki/Jira_(software))). 

This project designed to reduce employee time on between tasks context switch / 
task total work time calculation / time spending on worklog submitting.

*Notice: this project appearance history is available at 
blog [article](https://блог.md.land/михаил-драгункин/проекты/учёт-рабочего-времени) (in russian)* 

## Install

*At this point project does not provides automatically installation, 
so do it on your own, there is basic example:*

```bash
# 1. create install destination directory
mkdir -p ~/tools 

# 2. clone project
git clone https://github.com/unsektor/worklog ~/tools/worklog  

# 3. ensure script executable (optional)
chmod +x ~/tools/worklog/bin/wid.py
  
# 4. Link into executables directory (may requires access privelege)
ln -s "~/tools/worklog/bin/wid.py /usr/local/bin/wid
```

*Alternatively, 4th step can be passed just by adding custom install destination 
directory to `PATH` environment variable:* `export PATH=$PATH:~/tools/worklog/bin`

*Notice: `wid` acronym is stands for "What i did ?"*

## Usage
### 1\. Configure project (optional)

Project configuration may simplifies keeping worklog for some cases, 
but it is optional and next setup can be omitted. Configuration file stored at `../etc/wid.json` 
relative to main script.

#### Default report directory

Report directory contains workday report files you create (it 
looks like `../var/report/20191201.txt`, `../var/report/20191202.txt`, and etc... 
one file per day).

```json
{
  "dir": "../var/report"
}
```

#### Default task description

When some task is often taken in work and has always same description, 
its' number could be passed into configuration to automatically fill its' description 
on report building.

For example, it could be some administrative kind tasks:

```json
{
  "task": {
    "description": {
      "ADM-3": "TeamWox / Jira / Stash / Fisheye",
      "ADM-7": "Annual leave"
    }
  }
}
```

#### Task number aliasing

When some task is taken in work repeatedly, (eg. discussion meeting every week)  
and has some difficult to remember issue tracker number (eg. `PP-2659`), it could be aliased: 

```json
{
  "task": {
    "alias": {
      "MEET1W": "PP-2658",
      "MEET1D": "XN-2671"
    }
  }
}
```

*Notice: example above assumes that one task is stands for meeting each week (for first project), 
and another task for meeting each day (for another project).*

### 2\. Create worklog file

Manually create file in report directory (configured at first step)
with file name, following date format: `YYYYMMDD.txt`,
for example: `../var/report/20191201.txt` (stands for first december of 2019) 
and fill it with data, like:

```
# 10.00

10.00-12.00 - PP-1000 - development

# 12.00-13.00 launch time

13.00-14.00 - PP-1001 - discussion, time estimating
14.00-16.00 - PP-1007 - (blocker issue) research, fix
16.00-17.00 - PP-1008 - (higher priority issue) deployement
17.00-18.30 - PP-1007 - testing, deployment, maintenance
18.30-19.00 - PP-1001
```

Rows started with `#` character or rows that not followed time accounting row format 
will be treated as a comment and skipped by parser.

Row syntax is `[[start-time]-[end-time] - [project-key]] (- [description])`, 
where `start-time` & `end-time` represents time in format `HH:MM` 
(or `HH.MM` or `H:MM` or `H.MM`), `project-key` represents issue tracker task number (eg. 
`PK-441`), and `description` is the text to be submitted as task description. 

*Notice: some issue tracker may requires task worklog description, and at least one task 
row should contains some description.*

## 3\. Print report (user friendly)

```
$ wid  # means "what i did ?"

PP-1000  2h 0m   issue discussion
PP-1001  2h 30m  discussion, time estimating
PP-1007  4h 30m  (blocker issue) research, deployment, fix, maintenance, testing
PP-1008  1h 0m   (higher priority issue) deployement
```

## 3\.1\. Print report (for script submitting report to Jira) 

```
$ wid --json

[
  {
    "_": {
      "sum": 480
    },
    "date": "2020-08-31T00:00:00.000",
    "entries": [
      {
        "key": "PP-1000",
        "comment": "issue discussion",
        "timespent": 7200
      },
      {
        "key": "PP-1001",
        "comment": "discussion, time estimating",
        "timespent": 5400
      },
      {
        "key": "PP-1007",
        "comment": "(blocker issue) research, deployment, fix, maintenance, testing",
        "timespent": 12600
      },
      {
        "key": "PP-1008",
        "comment": "(higher priority issue) deployement",
        "timespent": 3600
      }
    ]
  }
]
```

*Notice: in example above `sum` value displayed in minutes, 
when each task `timespent` in seconds*

### 3\.2\. (\*) Report printing features

`wid` utility supports relative or concrete date report printing.

1. `wid -1` will print report for yesterday
2. `wid -2` will print report for day before yesterday
3. `wid 20170505` will print report for concrete day
4. `wid 20180202 20180203 20180204 20180205` will print report for concrete days 
   (it could be useful using with bash substitution, eg:
   `wid 202002{01..20} --json`, `wid 202002{17,22} --json`)

#### Debug

To increase command verbosity `-vvv` option should be passed. 
It useful when report is not converge (eg. in case of log syntax violation)
For worklog example above command output may be looks like: 

```
$ wid -1 -vvv

vvv: date list to process [datetime.date(2020, 8, 31)]
vvv: open file ../var/report/20200831.txt
vvv: Entry(start='10:00', end='12:00', task='PP-1000', description='development')
vvv: Entry(start='13:00', end='14:00', task='PP-1001', description='discussion, time estimating')
vvv: Entry(start='14:00', end='16:00', task='PP-1007', description='(blocker issue) research, fix')
vvv: Entry(start='16:00', end='17:00', task='PP-1008', description='(higher priority issue) deployement')
vvv: Entry(start='17:00', end='18:30', task='PP-1007', description='testing, deployment, maintenance')
vvv: Entry(start='18:30', end='19:00', task='PP-1001', description='')
vvv: task map is {'PP-1000': TaskEntry(task='PP-1000', duration=7200, description={'issue discussion'}), 'PP-1001': TaskEntry(task='PP-1001', duration=5400, description={'discussion', 'time estimating'}), 'PP-1007': TaskEntry(task='PP-1007', duration=12600, description={'(blocker issue) research', 'fix', 'testing', 'deployment', 'maintenance'}), 'PP-1008': TaskEntry(task='PP-1008', duration=3600, description={'(higher priority issue) deployement'})}

PP-1000  2h 0m   issue discussion
PP-1001  2h 30m  discussion, time estimating
PP-1007  4h 30m  (blocker issue) research, deployment, fix, maintenance, testing
PP-1008  1h 0m   (higher priority issue) deployement
```

### 4\. Submit report to Jira

1\. modify `var/jira.js` settings (issue tracker url and username))  
2\. open your Jira issue tracker web site  
3\. open developer tools `Ctrl + Shift + i` and paste (and execute) modified script 
    into console (it just exposes payload functions to submit worklog report just in one call
    in followed step)   
4\. create report and copy it to clipboard:

```bash
wid --json | pbcopy  # make report for "plugin" and copy to clipboard

# or just run `wid --json` and copy result manually
```

5\. execute into browser console function `submitDays([...])` where `[...]` is
    data that copied at 4th step.

*Notice: at this point it could be seems like it's too complicated and requires many actions, 
but practice reveals that this (**really low-cost**) solution saved **REALLY MANY** time*

# So, what the advantage ?

This project follows [Unix philosophy](https://en.wikipedia.org/wiki/Unix_philosophy) and
[Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) making application interaction 
experience pleasant, is not it ? 

Keeping worklog such way (probably the most simplest, is not it ?) removes 
employee from necessity to interact with (honestly, lagging) issue tracker interface 
performing a heavy routine (eg. sequent entering each task manually into form spending 
time to interact with it, when this project solution could be called once per week,
when submitting action takes no more than 2 minutes).

It always keeps locally worklog history (that may be transformed on any own, eg. 
`grep`'ed some way them and create work entrance (or launch) report or something else).

# Roadmap

- [ ] Create browser extension to simplify worklog submit, or use issue tracker API 
  to send worklog report instantly at all
- [ ] ... ?

# [License (MIT)](license.md)
