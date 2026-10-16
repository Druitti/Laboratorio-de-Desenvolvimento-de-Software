"""SemVer, heuristica de releases corretivas e CFR(b) para o Lab03."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

from lab03.selection import timestamp

HEURISTIC_VERSION = '1.0.7'
FOLLOWUP_DAYS = 7

_IDENTIFIER = r'(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)'
_SEMVER = re.compile(
    rf'^(?P<prefix>v)?(?P<major>0|[1-9][0-9]*)\.'
    rf'(?P<minor>0|[1-9][0-9]*)\.(?P<patch>0|[1-9][0-9]*)'
    rf'(?:-(?P<prerelease>{_IDENTIFIER}(?:\.{_IDENTIFIER})*))?'
    rf'(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
)
_CORRECTION_PATTERNS = (
    ('hotfix', re.compile(r'\bhotfix(?:es)?\b', re.IGNORECASE)),
    ('bug_fix', re.compile(r'\bbug[ -]?fix(?:es|ed|ing)?\b', re.IGNORECASE)),
    ('fixes_defect', re.compile(
        r'\bfix(?:es|ed)?\s+(?:(?:the|a|an|this|critical|security)\s+)*'
        r'(?:bug|issue|regression|crash|error|defect|vulnerability)\b', re.IGNORECASE)),
    ('defect_resolved', re.compile(
        r'\b(?:bug|issue|regression|crash|error|defect|vulnerability)\s+'
        r'(?:fix(?:ed)?|resolv(?:e|ed)|correct(?:ed)?)\b', re.IGNORECASE)),
    ('revert', re.compile(
        r'^\s*revert(?:ed|ing)?(?:\s*[:"-]|\s+(?:commit|change|pull request|pr)\b)', re.IGNORECASE)),
    ('regression_fix', re.compile(
        r'\bregression\s+(?:fix(?:ed)?|resolv(?:e|ed)|correct(?:ed)?)\b', re.IGNORECASE)),
)
_NON_CORRECTION_PATTERNS = (
    ('feature_delivery', re.compile(
        r'\b(?:new feature|features? added|introduc(?:e|es|ed|ing)|'
        r'add(?:s|ed|ing)?\s+(?:a\s+)?(?:new\s+)?(?:feature|command|api|support)|'
        r'breaking change|deprecat(?:e|ed|ion))\b', re.IGNORECASE)),
)
_NEGATION_BEFORE = re.compile(
    r"\b(?:no|not|never|without|isn't|aren't|wasn't|weren't|no longer|"
    r"doesn['’]t|don['’]t|didn['’]t|can['’]t|won['’]t|wouldn['’]t|"
    r"shouldn['’]t|couldn['’]t|does not|do not|did not|cannot|can not|"
    r"will not|would not|should not|could not)\s+"
    r"(?:(?:actually|really|necessarily|ever|yet)\s+)*"
    r"(?:(?:need|have)\s+to\s*|(?:(?:the|a|an|any|necessary|required)\s+){0,3})$", re.IGNORECASE)
_NEGATION_AFTER = re.compile(
    r'^\s+(?:(?:(?:(?:is|are|was|were|has|have|had|does|do|did|will|would|should|could|must|might)'
    r'(?:n[’\']t)?|won[’\']t)\s+)?'
    r'(?:not\s+(?:(?:yet|ever|necessarily|actually|really)\s+)*(?:be\s+)?'
    r'(?:required|needed|included|necessary|applicable)|'
    r'never\s+(?:(?:yet|ever|necessarily|actually|really)\s+)*(?:be\s+)?'
    r'(?:required|needed|included|necessary|applicable)|unnecessary)\b'
    r'|(?:(?:is|are|was|were|has|have|had|does|do|did|will|would|should|could|must|might)n[’\']t|won[’\']t)\s+'
    r'(?:(?:yet|ever|necessarily|actually|really)\s+)*(?:be\s+)?'
    r'(?:required|needed|included|necessary|applicable)\b)', re.IGNORECASE)


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = ()

    @property
    def is_prerelease(self):
        return bool(self.prerelease)


def parse_semver(value):
    """Parse SemVer 2.0.0, permitting only an optional lowercase ``v`` prefix."""
    if not isinstance(value, str):
        return None
    match = _SEMVER.fullmatch(value)
    if not match:
        return None
    prerelease = tuple(match.group('prerelease').split('.')) if match.group('prerelease') else ()
    build = tuple(match.group('build').split('.')) if match.group('build') else ()
    return SemVer(*(_parse_component(match.group(name)) for name in ('major', 'minor', 'patch')),
                  prerelease, build)


def _parse_component(value):
    number = 0
    for start in range(0, len(value), 9):
        chunk = value[start:start + 9]
        number = number * (10 ** len(chunk)) + int(chunk)
    return number


def compare_semver(left, right):
    """Return -1, 0, or 1 by SemVer precedence; build metadata is ignored."""
    left = parse_semver(left) if isinstance(left, str) else left
    right = parse_semver(right) if isinstance(right, str) else right
    if left is None or right is None:
        raise ValueError('As duas versoes precisam ser SemVer validas.')
    left_core = (left.major, left.minor, left.patch)
    right_core = (right.major, right.minor, right.patch)
    if left_core != right_core:
        return (left_core > right_core) - (left_core < right_core)
    if not left.prerelease or not right.prerelease:
        return (bool(left.prerelease) < bool(right.prerelease)) - (bool(left.prerelease) > bool(right.prerelease))
    for left_id, right_id in zip(left.prerelease, right.prerelease):
        if left_id == right_id:
            continue
        left_numeric, right_numeric = left_id.isdigit(), right_id.isdigit()
        if left_numeric and right_numeric:
            return ((len(left_id), left_id) > (len(right_id), right_id)) - (
                (len(left_id), left_id) < (len(right_id), right_id))
        if left_numeric != right_numeric:
            return -1 if left_numeric else 1
        return (left_id > right_id) - (left_id < right_id)
    return (len(left.prerelease) > len(right.prerelease)) - (len(left.prerelease) < len(right.prerelease))


def version_increment(previous, current):
    """Describe component changes; callers choose predecessors by publication time."""
    if previous is None:
        return 'no_previous_release'
    if current is None:
        return 'unparseable_version'
    if compare_semver(current, previous) < 0:
        return 'downgrade'
    if (previous.major, previous.minor, previous.patch) == (current.major, current.minor, current.patch):
        if previous.prerelease != current.prerelease:
            return 'prerelease_transition'
        return 'unchanged'
    if current.major != previous.major:
        return 'major'
    if current.minor != previous.minor:
        return 'minor'
    return 'patch'


def _release_payload(release):
    return release.get('release', release)


def _text_sources(release, commits):
    payload = _release_payload(release)
    sources = []
    for field, label in (('name', 'release_title'), ('body', 'release_notes')):
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            sources.append((label, value))
    for commit in commits or ():
        message = (commit.get('commit') or {}).get('message')
        if isinstance(message, str) and message.strip():
            sources.append((f"commit:{commit.get('sha', 'unknown')}", message))
    return sources


def classify_release(release, previous_release=None, commits=()):
    """Classify a release with auditable text signals and non-conclusive SemVer context.

    Positive correction evidence takes precedence, including mixed releases. A
    clearly described feature delivery can support ``no``; a PATCH increment
    by itself, missing text, or other ambiguous evidence remains ``uncertain``.
    """
    payload = _release_payload(release)
    tag = payload.get('tag_name')
    current = parse_semver(tag)
    previous = parse_semver(_release_payload(previous_release).get('tag_name')) if previous_release else None
    if not current:
        increment = 'unparseable_version'
    elif previous_release is None:
        increment = 'no_previous_release'
    elif previous is None:
        increment = 'previous_version_unparseable'
    else:
        increment = version_increment(previous, current)
    evidence = []
    negative_evidence = []
    sources = _text_sources(release, commits)
    for source, text in sources:
        for name, pattern in _CORRECTION_PATTERNS:
            for match in pattern.finditer(text):
                if not _is_negated(text, match.start(), match.end()):
                    evidence.append({'signal': name, 'source': source,
                                     'excerpt': text[max(0, match.start() - 80):match.end() + 120].strip()})
        for name, pattern in _NON_CORRECTION_PATTERNS:
            for match in pattern.finditer(text):
                if not _is_negated(text, match.start(), match.end()):
                    negative_evidence.append({'signal': name, 'source': source,
                                              'excerpt': text[max(0, match.start() - 80):match.end() + 120].strip()})
    if evidence:
        prediction, reason = 'yes', 'explicit_correction_evidence'
    elif negative_evidence and increment in ('major', 'minor'):
        prediction, reason = 'no', 'feature_evidence_with_major_or_minor_increment'
    elif increment == 'patch':
        prediction, reason = 'uncertain', 'patch_increment_alone_is_not_proof'
    elif not sources:
        prediction, reason = 'uncertain', 'no_textual_evidence_available'
    elif negative_evidence:
        prediction, reason = 'uncertain', 'feature_evidence_without_semver_context'
    else:
        prediction, reason = 'uncertain', 'no_sufficient_correction_or_noncorrection_evidence'
    return {
        'heuristic_version': HEURISTIC_VERSION,
        'release_id': payload.get('id'),
        'release_tag': tag,
        'semver': _semver_record(current),
        'previous_release_id': _release_payload(previous_release).get('id') if previous_release else None,
        'previous_release_tag': _release_payload(previous_release).get('tag_name') if previous_release else None,
        'previous_semver': _semver_record(previous),
        'previous_semver_status': ('not_available' if previous_release is None else
                       'interpreted' if previous is not None else 'unparseable'),
        'version_increment': increment,
        'semver_status': 'interpreted' if current else 'unparseable',
        'prediction': prediction,
        'analysis_status': 'analyzed' if sources else 'insufficient_text_evidence',
        'reason': reason,
        'correction_evidence': evidence,
        'non_correction_evidence': negative_evidence,
        'text_sources_available': [source for source, _ in sources],
    }


def _semver_record(version):
    if version is None:
        return None
    return {'major': version.major, 'minor': version.minor, 'patch': version.patch,
            'prerelease': list(version.prerelease), 'build': list(version.build)}


def _is_negated(text, start, end):
    prefix = text[max(0, start - 60):start]
    if re.search(r'\bnot only\s*$', prefix, re.IGNORECASE):
        return False
    suffix = text[end:end + 60]
    return bool(_NEGATION_BEFORE.search(prefix) or _NEGATION_AFTER.search(suffix))


def classify_repository(raw):
    """Build chronological predictions from one complete releases collector artifact."""
    if not raw.get('complete'):
        return {'repository': raw.get('repository'), 'complete': False,
                'heuristic_version': HEURISTIC_VERSION, 'predictions': [],
                'status': 'incomplete_release_data'}
    records = [record for record in raw.get('releases', [])
               if record.get('on_default_branch')
               and record.get('status') in ('before_window', 'in_window')
               and not _release_payload(record).get('draft')
               and not _release_payload(record).get('prerelease')]
    records.sort(key=lambda record: (timestamp(_release_payload(record)['published_at']),
                                     _release_payload(record)['id']))
    intervals = {interval.get('release_id'): interval
                 for interval in raw.get('comparisons', {}).get('stable', [])}
    predictions, previous = [], None
    for record in records:
        payload = _release_payload(record)
        interval = intervals.get(payload.get('id'), {})
        result = classify_release(record, previous, interval.get('commits', []))
        result.update({'repository': raw.get('repository'), 'published_at': payload.get('published_at'),
                       'release_url': payload.get('html_url'), 'in_window': record.get('status') == 'in_window',
                       'release_status': record.get('status'), 'comparison_status': interval.get('status')})
        predictions.append(result)
        previous = record
    return {'repository': raw.get('repository'), 'complete': True,
            'heuristic_version': HEURISTIC_VERSION, 'predictions': predictions,
            'status': 'analyzed'}


def calculate_cfr_b(releases, window_start, window_end, *, complete=True, followup_days=FOLLOWUP_DAYS):
    """Calculate CFR(b) with explicit right-censoring and unresolved outcomes.

    A fully observed reference must satisfy ``published_at + followup < end``.
    The strict inequality is necessary because the experiment's end is
    exclusive, while a correction exactly seven days later would qualify.
    """
    start, end = timestamp(window_start), timestamp(window_end)
    if start >= end or type(followup_days) is not int or followup_days <= 0:
        raise ValueError('Janela e periodo de acompanhamento devem ser positivos.')
    rows = list(releases)
    ids = [row.get('release_id') for row in rows]
    if any(value is None for value in ids) or len(ids) != len(set(ids)):
        raise ValueError('IDs de release ausentes ou duplicados.')
    dated = []
    invalid_dates = set()
    for row in rows:
        try:
            published = timestamp(row.get('published_at'))
        except (ValueError, TypeError, AttributeError):
            invalid_dates.add(row['release_id'])
            dated.append((row, None))
        else:
            dated.append((row, published))
    if invalid_dates:
        audit = [{'release_id': row['release_id'],
                  'status': 'invalid_timestamp' if row['release_id'] in invalid_dates
                  else 'not_evaluated_due_to_invalid_timestamps',
                  'followed_by_correction': None} for row in rows]
        return _empty_cfr_b('invalid_timestamps', len(rows), followup_days, audit)
    if not complete:
        audit = [{'release_id': row['release_id'], 'status': 'not_evaluated_incomplete_data',
                  'followed_by_correction': None} for row in rows]
        return _empty_cfr_b('incomplete_release_data', len(rows), followup_days, audit)
    mismatches = set()
    for row, published in dated:
        expected_in_window = start <= published < end
        if ('in_window' in row and
                (type(row['in_window']) is not bool or row['in_window'] != expected_in_window)):
            mismatches.add(row['release_id'])
    if mismatches:
        audit = [{'release_id': row['release_id'],
                  'status': 'window_mismatch' if row['release_id'] in mismatches
                  else 'not_evaluated_due_to_window_mismatch',
                  'followed_by_correction': None} for row in rows]
        return _empty_cfr_b('window_mismatch', len(rows), followup_days, audit)
    audit = []
    observed = [(row, published) for row, published in dated if start <= published < end]
    outside = [(row, published) for row, published in dated if not start <= published < end]
    observed.sort(key=lambda pair: (pair[1], str(pair[0]['release_id'])))
    horizon = timedelta(days=followup_days)
    censored = eligible = numerator = unknown = 0
    corrective = sum(row.get('prediction') == 'yes' for row, _ in observed)
    for row, published in observed:
        if published + horizon >= end:
            censored += 1
            audit.append({'release_id': row['release_id'], 'status': 'right_censored',
                          'followup_days_available': (end - published).total_seconds() / 86400,
                          'followed_by_correction': None})
            continue
        eligible += 1
        followups = [(next_row, next_published) for next_row, next_published in observed
                     if timedelta(0) < next_published - published <= horizon]
        has_correction = any(next_row.get('prediction') == 'yes' for next_row, _ in followups)
        uncertain_followup = any(next_row.get('prediction') not in ('yes', 'no')
                                 for next_row, _ in followups)
        if has_correction:
            numerator += 1
            status, outcome = 'followed_by_correction', True
        elif uncertain_followup:
            unknown += 1
            status, outcome = 'uncertain_followup', None
        else:
            status, outcome = 'no_observed_correction', False
        audit.append({'release_id': row['release_id'], 'status': status,
                      'followup_days_available': (end - published).total_seconds() / 86400,
                      'followup_release_ids': [item['release_id'] for item, _ in followups],
                      'followed_by_correction': outcome})
    for row, _ in outside:
        audit.append({'release_id': row['release_id'], 'status': 'outside_window',
                      'followed_by_correction': None})
    denominator = eligible - unknown
    rate = numerator / denominator if denominator else None
    return {'status': 'ok' if denominator else 'denominator_zero',
            'window_start': start.isoformat(), 'window_end': end.isoformat(),
            'followup_days': followup_days, 'releases_analyzed': len(rows),
            'in_window_releases': len(observed), 'eligible_references': eligible,
            'outside_window_releases': len(outside), 'censored_releases': censored,
            'uncertain_followup_references': unknown,
            'corrective_releases': corrective, 'numerator': numerator,
            'denominator': denominator, 'cfr_b': rate,
            'cfr_b_percent': 100 * rate if rate is not None else None,
            'audit': audit}


def aggregate_cfr_b(repository_results):
    """Pool repository numerators and denominators; do not average repo rates."""
    results = list(repository_results)
    valid = [result for result in results if result.get('status') in ('ok', 'denominator_zero')]
    excluded = [{'repository': result.get('repository'), 'status': result.get('status', 'missing_status')}
                for result in results if result not in valid]
    numerator = sum(result.get('numerator') or 0 for result in valid)
    denominator = sum(result.get('denominator') or 0 for result in valid)
    rate = numerator / denominator if denominator else None
    status = 'partial_data' if excluded else ('ok' if denominator else 'denominator_zero')
    return {'status': status,
            'repositories': len(results),
            'repositories_included': len(valid),
            'excluded_repositories': excluded,
            'numerator': numerator, 'denominator': denominator,
            'cfr_b': rate, 'cfr_b_percent': 100 * rate if rate is not None else None,
            'releases_analyzed': sum(result.get('releases_analyzed', 0) for result in valid),
            'censored_releases': sum(result.get('censored_releases', 0) for result in valid),
            'uncertain_followup_references': sum(
                result.get('uncertain_followup_references', 0) for result in valid)}


def _empty_cfr_b(status, releases_analyzed, followup_days, audit):
    return {'status': status, 'followup_days': followup_days,
            'releases_analyzed': releases_analyzed, 'in_window_releases': 0,
            'eligible_references': 0, 'outside_window_releases': 0, 'censored_releases': 0,
            'uncertain_followup_references': 0, 'corrective_releases': 0,
            'numerator': 0, 'denominator': 0, 'cfr_b': None,
            'cfr_b_percent': None, 'audit': audit}