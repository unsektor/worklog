#!/usr/bin/env python3

__version__ = '0.1.0'
__author__ = 'https://md.land/md'


import datetime
import math
import os
import re
import sys
import typing
import json


# Entity
class Day:
    def __init__(self, date: datetime.date, entry_list: typing.List['Entry']):
        self.date: datetime.date = date
        self.entry_list: typing.List['Entry'] = entry_list


class Entry:
    """ Represent task report row entry (model of parsed text line) """
    def __init__(self, start: datetime.datetime, end: datetime.datetime, task: str, description: str = ''):
        self.start: datetime.datetime = start
        self.end: datetime.datetime = end
        self.task: str = task
        self.description: str = description

    def __repr__(self) -> str:
        return f'Entry(start={self.start.strftime("%H:%M")!r}, end={self.end.strftime("%H:%M")!r},' \
               f' task={self.task!r}, description={self.description!r})'


class TaskEntry:
    """ Represents aggregated task entry (task model to be dumped into final report) """
    def __init__(self, task: str, duration: int = 0, date: datetime.date = None):
        self.date: datetime.date = date
        self.task: str = task
        self.duration: int = duration
        self.description: set = set()

    def update(self, duration: int, description: typing.Iterable) -> None:
        self.duration += duration
        self.description.update(description)

    def __repr__(self) -> str:
        return f'TaskEntry(task={self.task!r}, duration={self.duration!r}, description={self.description!r})'


# Parser
class ParserInterface:
    """ Defines parser contract """
    def parse(self, data: str) -> typing.Iterable:
        raise NotImplementedError


class Parser(ParserInterface):
    """ Parses tasks day report """
    ENTRY_REGEXP = r'^(?P<start>\d{1,2}[.:]\d{1,2})\s*-\s*(?P<end>\d{1,2}[.:]\d{1,2})\s*-\s*' \
                   r'(?P<task>(?:([a-z]+)-\d+|let))\s*(?:\s*-\s*(?P<description>.+)|)$'

    def __init__(self):
        self._entry_regexp = re.compile(self.ENTRY_REGEXP, re.IGNORECASE)

    def parse(self, data: str) -> typing.Generator[typing.Tuple[str, Entry], None, None]:
        line_list = data.split("\n")

        for line in line_list:
            if line.startswith('#'):
                continue  # Skip comment row

            entry_match = self._entry_regexp.match(line)
            if not entry_match:
                continue

            entry = entry_match.groupdict()
            task = entry['task'].upper()

            yield task, Entry(
                # 9.08 -> 09:08
                start=datetime.datetime.strptime(f"{int(entry['start'][:-3]):02d}:{entry['start'][-2:]}", '%H:%M'),
                end=datetime.datetime.strptime(f"{int(entry['end'][:-3]):02d}:{entry['end'][-2:]}", '%H:%M'),
                task=task,
                description=entry['description'] or ''
            )


# Report builder
class ViewBuilderInterface:
    """ Builds tasks report view """
    def build(self, data: list) -> str:
        raise NotImplementedError


class ReportViewBuilder(ViewBuilderInterface):
    """  Builds JSON serialized report to be passed for 3rd party components """
    def build(self, data: typing.Dict) -> str:
        task_list: typing.List[dict] = []

        for day in data:
            day_ = {
                '_': {'sum': 0},
                'date': day['date'].strftime('%Y-%m-%dT00:00:00.000'),
                'entries': []
            }

            task_list.append(day_)

            for task in day['entries'].values():
                day_['entries'].append({
                    'key': task.task,
                    'comment': ', '.join(sorted(task.description)),
                    'timespent': task.duration
                })
                day_['_']['sum'] += int(task.duration / 60)

        return json.dumps(task_list, indent=2, ensure_ascii=False)


class UserViewBuilder(ViewBuilderInterface):
    """ Builds basic table-like report for standard output """
    def build(self, data: typing.List[typing.Dict[str, TaskEntry]]) -> str:
        if len(data) == 0:
            return 'Nothing was done this day'

        view = '\n'

        for day in data:
            entries = day['entries']
            assert isinstance(entries, dict)

            for task_number, task in entries.items():
                assert isinstance(task, TaskEntry)

                cell_width = len(max(task_map.keys(), key=len))

                delta = datetime.timedelta(seconds=task.duration)

                view += ('{task:' + str(cell_width) + '} {time!s:8} {description!s}\n').format(
                    task=task.task,
                    time=f'{math.floor(delta.seconds / 3600):>2}h ' + str(math.ceil((delta.seconds % 3600) / 60)) + 'm',
                    description=', '.join(sorted(task.description)),
                )

        return view


# Processing
class Debug:
    NO_VERBOSE = 0
    VERBOSE = 1
    VERY_VERBOSE = 3
    VERY_VERY_VERBOSE = 7

    LEVELS_ = [NO_VERBOSE, VERBOSE, VERY_VERBOSE, VERY_VERY_VERBOSE]


parser = Parser()


def process_day(data: str, date: datetime.date) -> typing.Dict[str, TaskEntry]:
    """ Process day report and returns list of parsed row models """
    task_map: typing.Dict[str, TaskEntry] = {}  # aggregate
    keyword_splitter = re.compile(r'\s*,\s*')

    task_alias_map: typing.Dict[str, str] = config['task']['alias']
    task_description_map: typing.Dict[str, str] = config['task']['description']

    for task, entry in parser.parse(data=data):
        if debug_mode == Debug.VERY_VERY_VERBOSE:
            print('vvv:', entry)

        if task in task_alias_map:  # substitute task alias if such
            task = task_alias_map[task]

        if task not in task_map:  # processing day task first time
            task_map[task] = TaskEntry(task=task, date=date)

        task_map[task].update(  # bump duration and description
            duration=(entry.end - entry.start).seconds,
            description=filter(lambda x: x != '', keyword_splitter.split(entry.description))
        )

    for task_entry in task_map.values():  # just patch description if present
        if task_entry.task in task_description_map:
            task_entry.description = {task_description_map[task_entry.task]}

    return task_map


if __name__ == '__main__':
    # Arguments configuration
    import argparse

    def get_date_list(date_list: typing.List[str]) -> typing.List[datetime.date]:
        def get_date_list_on_interval(days: int, relative_to: datetime.date):
            sign = 1 if days > 0 else -1
            return [relative_to + datetime.timedelta(days=sign * days) for days in range(0, abs(days)+1)]

        def parse_ymd(date: str) -> datetime.date:
            return datetime.datetime.strptime(date, '%Y%m%d').date()

        if date_list is None:
            return [datetime.datetime.now().date()]

        date_list_length = len(date_list)

        if date_list_length == 0:
            return [datetime.datetime.now().date()]

        if date_list_length == 1:
            if re.match(r'-\d+', date_list[0]):
                return [datetime.datetime.now().date() + datetime.timedelta(days=int(date_list[0]))]

            if re.match(r'\d{8}', date_list[0]):
                return [parse_ymd(date_list[0])]

            raise Exception('Unsupported date format')

        if date_list_length >= 2:
            date_list_ = []

            if re.match(r'\d{8}', date_list[0]):
                date_list_.append(parse_ymd(date_list[0]))
            else:
                raise Exception('Unsupported date format')

            if re.match(r'[+-]\d+', date_list[1]):
                if date_list_length > 2:
                    raise Exception('Unsupported date format')
                return get_date_list_on_interval(days=int(date_list[1]), relative_to=date_list_[0])

            for date in date_list[1:]:
                if re.match(r'\d{8}', date):
                    date_list_.append(parse_ymd(date))
                else:
                    raise Exception('Unsupported date format')
            return date_list_
        raise Exception('Unsupported date format')

    argument_parser = argparse.ArgumentParser()

    group = argument_parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-j', '--json', action='store_true', dest='json', help='Builds report view')
    argument_parser.add_argument('date', action='store', nargs='*',
                                 help='Example: `-1`, `20200212`, `20200212 -1`, `20200212 +1`, `20200212 20200215` ')
    argument_parser.add_argument('-v', '--verbose', action='count', default=0)

    command_arguments = argument_parser.parse_args(args=sys.argv[1:])

    # Main
    if command_arguments.verbose + 1 > len(Debug.LEVELS_):
        print(argument_parser.print_help())
        exit(1)

    debug_mode = Debug.LEVELS_[command_arguments.verbose]

    date_list: typing.List[datetime.date] = get_date_list(command_arguments.date)

    if debug_mode == Debug.VERY_VERY_VERBOSE:
        print('vvv:', 'date list to process', date_list)

    absolute_bin_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    with open(absolute_bin_dir + '/../etc/wid.json') as fp:
        config = json.load(fp=fp)

    def process_date(date: datetime.date) -> typing.Union[typing.Dict[str, TaskEntry], None]:
        filename = f"{absolute_bin_dir!s}/{config['dir']}/{date.strftime('%Y%m%d')}.txt"

        if not os.path.exists(filename):
            if debug_mode >= Debug.VERBOSE:
                print('v:', filename, 'is not found')
            return None

        with open(filename) as fp:
            if debug_mode == Debug.VERY_VERY_VERBOSE:
                print('vvv: open file', filename)
            data = fp.read()
        return process_day(data=data, date=date)

    task_map_list = []
    for date in date_list:
        task_map = process_date(date)

        if debug_mode == Debug.VERY_VERY_VERBOSE:
            print('vvv: task map is', task_map)

        if task_map is None:
            continue

        task_map_list.append({
            'date': date,
            'entries': task_map,
        })

    # output
    view_builder: ViewBuilderInterface

    if command_arguments.json:
        view_builder = ReportViewBuilder()
    else:
        view_builder = UserViewBuilder()

    report = view_builder.build(data=task_map_list)

    print(report)
    exit(0)
