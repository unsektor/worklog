const jiraUrl = `https://jira.company.com`;
const userName = 'your.username';

function _toJson(response) {
    var contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
        return response.json();
    }
    throw new TypeError("Oops, we haven't got JSON!");
}

function search(project_key) {  // eg. project_key = PP-1000
    return fetch(`${jiraUrl}/rest/api/2/issue/${project_key}?fields=project%2Csummary%2Ctimeestimate%2Cissuetype`);
}

function validate(data) {
    let headers = new Headers();
    headers.append('Content-Type', 'application/json');
    return fetch(`${jiraUrl}/rest/tempo-timesheets/3/worklogs/validate`, {
        method: 'POST', body: JSON.stringify(data), headers: headers
    })
}

function submit(data) {
    let headers = new Headers();
    headers.append('Content-Type', 'application/json');
    return fetch(`${jiraUrl}/rest/tempo-timesheets/3/worklogs/`, {
        method: 'POST', body: JSON.stringify(data), headers: headers
    });
}

function _(task, dateStarted) {
    search(task['key'])
        .then(_toJson)
        .then(function (data) {
            return {
                "id": null,
                "issue": {
                    "key": task['key'].toUpperCase(),
                    "remainingEstimateSeconds": Math.max(0, data.fields.timeestimate - task['timespent']),
                    "id": data.id
                },
                "timeSpentSeconds": task['timespent'],
                "dateStarted": dateStarted,
                "comment": task['comment'],
                "meta": {"analytics-origin-action": "clicked"},
                "author": {"name": userName},
                "workAttributeValues": []
            }
        }).then(worklog => validate(worklog).then(function () {submit(worklog)}));
}

function submitDay(day) {
    let dateStarted = day['date'];  // eg. "2019-04-30T00:00:00.000"
    let taskList = day['entries'];

    for (task of taskList) {
        _(task, dateStarted);
    }
}

function submitDays(days) {
    for (day of days) {
        submitDay(day);
    }
}
