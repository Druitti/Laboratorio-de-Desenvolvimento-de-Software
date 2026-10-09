"""Lead time de Santiago (#42) e CFR(a)/recuperação de Tavares (#43)."""
from statistics import median

from lab03.selection import timestamp

FAILURE_CONCLUSIONS = {'failure', 'timed_out', 'startup_failure'}
SUCCESS_CONCLUSION = 'success'


def lead_time(comparisons):
    """Horas; ausências são None. Commit com data inválida invalida seu intervalo.

    A variante por commit considera cada inclusão em uma release (não remove um
    SHA repetido em releases distintas). Duplicações dentro do intervalo somem.
    """
    releases, commits, audit = [], [], []
    for interval in comparisons:
        row = {k: interval.get(k) for k in ('release_id', 'base_tag', 'head_tag')}
        status = interval['status']
        values = []
        if status == 'ok':
            try:
                published = timestamp(interval['published_at'])
                unique = {c['sha']: c for c in interval['commits']}
                values = [(published - timestamp(c['commit']['author']['date'])).total_seconds() / 3600
                          for c in unique.values()]
                if any(v < 0 for v in values):
                    status = 'inconsistent_dates'
                elif not values:
                    status = 'no_commits'
            except (ValueError, TypeError, KeyError, AttributeError):
                status = 'inconsistent_dates'
        if status == 'ok':
            releases.append(max(values))
            commits.extend(values)
        audit.append({**row, 'status': status,
                      'commit_count': len(interval.get('commits', [])),
                      'lead_time_release_hours': max(values) if status == 'ok' else None})
    return {'lead_time_release_hours': median(releases) if releases else None,
            'lead_time_commit_hours': median(commits) if commits else None,
            'measured_releases': len(releases), 'measured_commit_inclusions': len(commits),
            'ignored_releases': len(audit) - len(releases), 'intervals': audit}


def classify_run(conclusion):
    """Tabela da seção 3: sucesso, falha, ou ignorado (nunca entra em nenhum cálculo)."""
    if conclusion == SUCCESS_CONCLUSION:
        return 'success'
    if conclusion in FAILURE_CONCLUSIONS:
        return 'failure'
    return 'ignored'


def change_failure_rate(runs):
    """CFR(a): falhas sobre falhas+sucessos. Sem runs válidos, a taxa é None, não zero."""
    failures = successes = ignored = 0
    for run in runs:
        kind = classify_run(run.get('conclusion'))
        if kind == 'success':
            successes += 1
        elif kind == 'failure':
            failures += 1
        else:
            ignored += 1
    total = failures + successes
    return {'cfr_ci': failures / total if total else None,
            'failures': failures, 'successes': successes, 'ignored': ignored}


def recovery_episodes(runs):
    """Mediana em horas dos episódios de recuperação, por workflow, sem misturar.

    Um episódio começa na primeira falha após um sucesso do mesmo workflow e
    termina no updated_at do próximo sucesso daquele workflow; falhas seguintes
    antes da recuperação pertencem ao mesmo episódio. Um episódio sem sucesso
    posterior na janela é censurado: preservado com duração None, nunca
    descartado. Runs ignorados (tabela da seção 3) não abrem nem fecham episódio.
    """
    by_workflow = {}
    for run in runs:
        kind = classify_run(run.get('conclusion'))
        if kind == 'ignored':
            continue
        by_workflow.setdefault(run['workflow_id'], []).append({**run, 'kind': kind})
    durations, details, censored = [], [], 0
    for workflow_id, workflow_runs in by_workflow.items():
        workflow_runs.sort(key=lambda r: timestamp(r['run_started_at']))
        seen_success = False
        open_episode = None
        for run in workflow_runs:
            if run['kind'] == 'success':
                if open_episode is not None:
                    hours = ((timestamp(run['updated_at']) - timestamp(open_episode['run_started_at']))
                             .total_seconds() / 3600)
                    durations.append(hours)
                    details.append({'workflow_id': workflow_id, 'started_at': open_episode['run_started_at'],
                                    'recovered_at': run['updated_at'], 'recovery_hours': hours, 'censored': False})
                    open_episode = None
                seen_success = True
            elif run['kind'] == 'failure' and seen_success and open_episode is None:
                open_episode = run
        if open_episode is not None:
            censored += 1
            details.append({'workflow_id': workflow_id, 'started_at': open_episode['run_started_at'],
                            'recovered_at': None, 'recovery_hours': None, 'censored': True})
    episodes = len(details)
    return {'recovery_hours': median(durations) if durations else None,
            'episodes': episodes, 'censored': censored,
            'censored_ratio': censored / episodes if episodes else None, 'details': details}
