"""Lead time de Santiago (#42). Entradas auditadas pelo coletor de releases."""
from statistics import median

from lab03.selection import timestamp


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
