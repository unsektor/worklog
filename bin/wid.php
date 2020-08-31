<?php # "wid" is stands for "what i did ?"

# todo add `--f` option to fill task description with template
# todo add `--week|-w` option to create report for week
# todo option -r (report for this week), -r -1 (report for previous week)
# todo auto smash void with tasks

namespace md\job\wid {
    use DateTime, DateTimeImmutable, DateTimeInterface;
    use const JSON_PRETTY_PRINT, JSON_UNESCAPED_UNICODE;
    use function array_map;
    use function define;
    use function file, file_exists, floor;
    use function in_array;
    use function json_encode;
    use function preg_match;
    use function sprintf, str_repeat, str_replace;
    use function touch;

    const WORKLOG_DIR                  = __DIR__ . '\..\отчёты';
    const WORKLOG_ENTRY_REGEXP_PATTERN = '/^(?<start>[0-9]{1,2}\.[0-9]{2})-(?<end>[0-9]{1,2}\.[0-9]{2})\s+(?:-|)\s+(?<task>((?:[a-zA-Z]{2,15}-[0-9]{1,6})|void|let))(?:(\s+(?:-)\s+(?<description>.*)|))\s*$/i';
    const VOID_TASK_NUMBER             = 'VOID';
    const TYPICAL_TASK_MAP             = [
        'WDDADM-3'       => 'TeamWox / JIRA / Stash / Fisheye',  # Работа с TeamWox, Jira и т.д.
        'PP-2991'        => 'обсуждение выполненных задач - проблем и вопросов / stand-up',  # Еженедельная летучка
        VOID_TASK_NUMBER => '<not specified>',  # And what i did ?
    ];

    /** Task number alias to task number */
    const TASK_NUMBER_ALIAS_MAP = [
        // Let'uchka task
        'LET' => 'PP-2991',
    ];

    /** Day work duration (in minutes). (480 minutes = 8 hours * 60 minutes) */
    const DAY_WORK_DURATION_IN_MINUTES = 480;

    /** Log */
    function _(string $message, int $verboseLevel = 0): void
    {
        /** @noinspection PhpUndefinedConstantInspection */
        if ($verboseLevel <= VERBOSE) {
            print($message);
        }
    }

    /** Returns DateTime rounded (fractions down) difference in minutes. */
    function get_datetime_difference_in_minutes(DateTimeInterface $start, DateTimeInterface $end): int
    {
        $differenceInSeconds = $end->getTimestamp() - $start->getTimestamp();
        return floor($differenceInSeconds / 60);  // difference in minutes
    }

    /** Returns entries grouped by task (aggregate) */
    function group_by_task(array $entries): array
    {
        $entriesGroupedByTask = [];
        foreach ($entries as $line => $entry) {
            if (!preg_match(WORKLOG_ENTRY_REGEXP_PATTERN, $entry, $matches)) {
                continue;  // mute parse error, deal with it. (or write worklog correct)
            }

            $task        = !isset($matches['task']) ? '-' : strtoupper($matches['task']);
            $description = !isset($matches['description']) ? '-' : trim($matches['description']);

            $start = new DateTime($matches['start']);
            $end   = new DateTime($matches['end']);

            $isTaskNumberAlias = array_key_exists($task, TASK_NUMBER_ALIAS_MAP);
            if ($isTaskNumberAlias) {
                $task = TASK_NUMBER_ALIAS_MAP[$task];
            }

            $timeDifferenceInMinutes = get_datetime_difference_in_minutes($start, $end);

            $entriesGroupedByTask[$task][] = [
                'start'       => $start->format('H:i'),
                'end'         => $end->format('H:i'),
              # 'period'      => $scalarStart . '-' . $scalarEnd,
                'interval'    => $timeDifferenceInMinutes,
                'description' => $description,
            ];
        }

        return $entriesGroupedByTask;
    }

    /** (Sum) */
    function collapse_entries_grouped_by_task(array $entriesGroupedByTask): array
    {
        $collapsedEntriesGroupedByTask = [];

        foreach ($entriesGroupedByTask as $task => $taskEntries) {
            $interval              = 0;
            $descriptionCollection = [[]];

            foreach ($taskEntries as $taskEntry) {
                $interval                += (int) $taskEntry['interval'];
                $descriptionCollection[] = preg_split('/(\s+|\s*),(\s+|\s*)/', $taskEntry['description']);
            }

            $isTypicalTask = array_key_exists($task, TYPICAL_TASK_MAP);
            if ($isTypicalTask) {
                $scalarDescription = TYPICAL_TASK_MAP[$task];
            } else {
                /** @noinspection SlowArrayOperationsInLoopInspection */
                $description       = array_merge(...$descriptionCollection);
                $description       = array_filter($description);
                $description       = array_unique($description);
                $description       = array_diff($description, ['-']);
                $scalarDescription = implode(', ', $description);
            }

            $collapsedEntriesGroupedByTask[] = [
                'number'      => $task,
                'interval'    => $interval,
                'description' => $scalarDescription,
            ];
        }

        return $collapsedEntriesGroupedByTask;
    }

    function convert_to_plugin(array $collapsedEntriesGroupedByTask, DateTimeInterface $worklogDateTime): array
    {
        $convertToPluginClosure = function (array $task): array {
            return [
                'key'       => $task['number'],
                'timespent' => $task['interval'] * 60,
                'comment'   => $task['description'],
            ];
        };

        return [
            'entries' => array_map($convertToPluginClosure, $collapsedEntriesGroupedByTask),
            'date'    => $worklogDateTime->format('Y-m-d\TH:i:s.000'),
        ];
    }

    function handle_day(?string $dayQuery): int
    {
        $now = new DateTimeImmutable();
        switch (true) {
            case 0 !== preg_match('/\d{8}/', $dayQuery):
                // concrete worklog, (eg. 20171202)
                $dayScalarDateTime = $dayQuery;
                $dayDateTime       = new DateTime($dayScalarDateTime);
                break;

            case 0 !== preg_match('/(?P<day>(-\d{1,4}|y))/', $dayQuery, $matches):
                // relative worklog (eg. day: -1, -2, -3, y (= -1))
                $day         = (int) $matches['day'];
                $day         = str_replace('-', '', $day); # TODO FIX AD-HOC
                $modify      = sprintf('-%u weekday', $day);
                $dayDateTime = $now->modify($modify);
                break;

            default:  // today worklog
                $dayDateTime = $now;
                break;
        }

        $dayScalarDateTime = $dayDateTime->format('Ymd');
        $dayWorklogPath    = WORKLOG_DIR . "\\{$dayScalarDateTime}.txt";

        if (!file_exists($dayWorklogPath)) {
            if ($dayDateTime->format('N') >= 6) {  // is weekend date ?
                _(" ! Worklog file does not exists at \"{$dayWorklogPath}\".");
                _("\n * {$dayScalarDateTime} is weekend day.");
                return 1;
            }

            /* let me */ touch($dayWorklogPath);
        }

        $fileContents                  = file($dayWorklogPath);
        $entriesGroupedByTask          = group_by_task($fileContents);
        $collapsedEntriesGroupedByTask = collapse_entries_grouped_by_task($entriesGroupedByTask);

        /** @noinspection PhpUndefinedConstantInspection */
        if (VERBOSE >= 2) {
            // Output full report (JSON format)
            $report = [
                'date'              => $dayScalarDateTime,
                'entries'           => $entriesGroupedByTask,
                'collapsed_entries' => $collapsedEntriesGroupedByTask,
            ];

            _(json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), 2);
            _("\n\n" . str_repeat('-', 50) . "\n\n", 2);
        }

        if (VERBOSE >= 0) {
            _(json_encode(
                    convert_to_plugin($collapsedEntriesGroupedByTask, $dayDateTime),
                    JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE
            ), 0);
        }

        if (VERBOSE >= 1) {
            _("\n\n" . str_repeat('-', 50) . "\n\n", 1);

            // Outputs table style report
            _("{$dayDateTime->format('d F, Y (l)')}:\n\n");

            $totalWorkMinutes = 0;
            foreach ($collapsedEntriesGroupedByTask as $taskData) {
                $taskNumber      = $taskData['number'];
                $taskTime        = $taskData['interval'];
                $taskDescription = $taskData['description'];

                if (VOID_TASK_NUMBER !== $taskNumber) {
                    // do not count void task time
                    $totalWorkMinutes += $taskTime;
                }

                // todo use max length task here instead 9
                _(sprintf("%-9s %3um %s\n", $taskNumber, $taskTime, $taskDescription));
            }

            $isFriday = $dayDateTime->format('N') == 5;
            $dayWorkDurationInMinutes = $isFriday ? 420 : 480;


            $totalWorkPercentage = (int) floor(($totalWorkMinutes / $dayWorkDurationInMinutes) * 100);  // fraction down round
            _("\nTotal: {$totalWorkMinutes} / $dayWorkDurationInMinutes ({$totalWorkPercentage}%)\n");
        }
        return 0;
    }

    /** Main */
    function main(string ...$argv): int
    {
        \chdir(__DIR__);

        if (1) {  // detect verbosity level
            foreach ($argv as $key => $value) {
                if (in_array($value, ['-v', '-vv', '-vvv'], true)) {
                    $VERBOSE = ['-v' => 1, '-vv' => 2, '-vvv' => 3][$value];
                    unset($argv[$key]);
                }
            }

            define('VERBOSE', $VERBOSE ?? 0);
        }

        if (1) {  // mode : look concrete day
            return handle_day($argv[1] ?? null);
        }

        return 0;
    }
}

namespace {
    return md\job\wid\main(...$argv);
}
