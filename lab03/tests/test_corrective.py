"""Synthetic tests for corrective-release heuristics and CFR(b)."""
from datetime import timedelta

import pytest

from lab03.corrective import (aggregate_cfr_b, calculate_cfr_b, classify_release,
                              classify_repository, compare_semver, parse_semver,
                              version_increment)
from lab03.selection import timestamp


def release(release_id, published_at, prediction='no', **extra):
    return {'release_id': release_id, 'published_at': published_at,
            'prediction': prediction, **extra}


def test_semver_stable_v_prefix_and_metadata():
    assert parse_semver('1.2.3') == parse_semver('v1.2.3')
    assert parse_semver('1.2.4-rc.1+build.7').prerelease == ('rc', '1')
    assert parse_semver('release-2025-03') is None
    assert parse_semver('01.2.3') is None


def test_semver_numeric_components_exceeding_python_int_limit_parse():
    parsed = parse_semver(f'{"9" * 4301}.0.0')
    assert parsed is not None
    assert compare_semver(parsed, parse_semver('9.0.0')) == 1


def test_semver_numeric_prerelease_identifiers_exceeding_int_limit_compare():
    assert compare_semver(f'1.0.0-{"9" * 4301}', '1.0.0-9') == 1


@pytest.mark.parametrize(('left', 'right'), [
    ('1.2.3', '1.2.4'), ('1.2.4', '1.3.0'), ('1.9.0', '2.0.0'),
    ('1.0.0-alpha.1', '1.0.0-alpha.beta'), ('1.0.0-rc.1', '1.0.0')])
def test_semver_precedence(left, right):
    assert compare_semver(left, right) == -1
    assert compare_semver(right, left) == 1
    assert compare_semver(left, left + '+build.1') == 0


@pytest.mark.parametrize(('previous', 'current', 'expected'), [
    ('1.2.3', '1.2.4', 'patch'), ('1.2.3', '1.3.0', 'minor'),
    ('1.2.3', '2.0.0', 'major'), ('1.2.3-rc.1', '1.2.3', 'prerelease_transition'),
    ('1.2.3', '1.2.3', 'unchanged'), ('2.0.0', '1.9.0', 'downgrade')])
def test_version_increment(previous, current, expected):
    assert version_increment(parse_semver(previous), parse_semver(current)) == expected
    assert version_increment(None, parse_semver(current)) == 'no_previous_release'


def test_patch_is_not_conclusive_and_semver_context_is_reported():
    result = classify_release({'id': 2, 'tag_name': 'v1.2.4', 'name': 'Update', 'body': ''},
                              {'id': 1, 'tag_name': 'v1.2.3', 'name': 'Previous'}, [])
    assert result['prediction'] == 'uncertain'
    assert result['reason'] == 'patch_increment_alone_is_not_proof'
    assert result['heuristic_version'] == '1.0.7'
    assert result['previous_release_id'] == 1
    assert result['version_increment'] == 'patch'


def test_existing_predecessor_with_invalid_tag_is_not_reported_as_absent():
    result = classify_release({'id': 2, 'tag_name': '1.2.3', 'name': 'Update'},
                              {'id': 1, 'tag_name': 'release-2024-01'})
    assert result['previous_release_id'] == 1
    assert result['previous_semver'] is None
    assert result['previous_semver_status'] == 'unparseable'
    assert result['version_increment'] == 'previous_version_unparseable'


@pytest.mark.parametrize('text,source', [
    ('Hotfix: restore authentication', 'release_title'),
    ('Fixes the regression in parsing', 'release_notes'),
    ('Revert "feature: broken cache"', 'commit:abc')])
def test_explicit_correction_evidence(text, source):
    release_data = {'id': 5, 'tag_name': 'release-5', 'name': '', 'body': ''}
    commits = [{'sha': 'abc', 'commit': {'message': text}}]
    if source == 'release_title':
        release_data['name'] = text
        commits = []
    elif source == 'release_notes':
        release_data['body'] = text
        commits = []
    result = classify_release(release_data, commits=commits)
    assert result['prediction'] == 'yes'
    assert result['correction_evidence'][0]['source'] == source


@pytest.mark.parametrize('text', [
    'No bug fix is required for this release.',
    'This change is not a hotfix.',
    'Bug fixes are not included in this release.',
    "This doesn't fix the bug.",
    "This won't fix the issue.",
    "We can't fix the regression here.",
    'This release does not actually fix the bug.',
    'Bug fix was not necessary.',
    "Bug fix wasn't necessary.",
    "We don't need to fix the bug.",
    'We do not need to fix the bug.',
    "Bug fix won't be included in this release.",
    'Bug fix will not be included in this release.',
    'Bug fix is not yet included in this release.',
    'Bug fix will never be included in this release.',
    'Bug fix was never actually included in this release.',
])
def test_negated_correction_language_is_not_positive_evidence(text):
    result = classify_release({'id': 9, 'tag_name': 'release-9', 'name': text})
    assert result['prediction'] == 'uncertain'
    assert result['correction_evidence'] == []


def test_not_only_does_not_negate_correction_evidence():
    result = classify_release({'id': 9, 'tag_name': 'release-9',
                               'name': 'Not only bug fixes, but also a new feature'})
    assert result['prediction'] == 'yes'


def test_negated_feature_signal_does_not_support_prediction_no():
    result = classify_release({'id': 2, 'tag_name': '2.0.0', 'name': 'No new feature in this release'},
                              {'id': 1, 'tag_name': '1.4.0'})
    assert result['prediction'] == 'uncertain'
    assert result['non_correction_evidence'] == []


def test_contracted_negated_feature_is_not_noncorrection_evidence():
    result = classify_release({'id': 2, 'tag_name': '2.0.0',
                               'name': "New feature isn't included in this release."},
                              {'id': 1, 'tag_name': '1.4.0'})
    assert result['prediction'] == 'uncertain'
    assert result['non_correction_evidence'] == []


def test_later_positive_correction_match_is_not_hidden_by_negated_match():
    result = classify_release({
        'id': 2, 'tag_name': 'release-2',
        'name': 'No hotfix is needed; this release includes a hotfix for the crash'})
    assert result['prediction'] == 'yes'
    assert any(signal['signal'] == 'hotfix' for signal in result['correction_evidence'])


def test_affirmative_fix_and_included_phrases_remain_correction_evidence():
    for text in ('Bug fix included in this release.', 'We need to fix the bug.'):
        result = classify_release({'id': 9, 'tag_name': 'release-9', 'name': text})
        assert result['prediction'] == 'yes'
        assert result['correction_evidence']


def test_mixed_release_with_new_feature_and_fix_is_corrective():
    result = classify_release({'id': 2, 'tag_name': '2.0.0', 'name': 'New feature and bug fix'},
                              {'id': 1, 'tag_name': '1.4.0'})
    assert result['prediction'] == 'yes'
    assert result['correction_evidence']
    assert result['non_correction_evidence']


def test_noncorrection_requires_semver_and_explicit_feature_text():
    result = classify_release({'id': 2, 'tag_name': '2.0.0', 'name': 'New feature release'},
                              {'id': 1, 'tag_name': '1.4.0'})
    assert result['prediction'] == 'no'
    assert classify_release({'id': 3, 'tag_name': 'release-2025-03', 'name': 'Update'})['prediction'] == 'uncertain'


def test_repository_predictions_use_publication_order_and_primary_release_contract():
    raw = {
        'repository': 'org/project', 'complete': True,
        'releases': [
            {'status': 'in_window', 'on_default_branch': True,
             'release': {'id': 2, 'tag_name': 'v1.1.0', 'name': 'Fixes a bug', 'body': '',
                         'published_at': '2025-04-01T00:00:00Z', 'draft': False, 'prerelease': False}},
            {'status': 'in_window', 'on_default_branch': True,
             'release': {'id': 1, 'tag_name': 'v1.0.0', 'name': 'Initial release', 'body': '',
                         'published_at': '2025-03-01T00:00:00Z', 'draft': False, 'prerelease': False}},
            {'status': 'in_window', 'on_default_branch': False,
             'release': {'id': 3, 'tag_name': 'v1.2.0', 'name': 'New feature', 'body': '',
                         'published_at': '2025-05-01T00:00:00Z', 'draft': False, 'prerelease': False}},
            {'status': 'in_window', 'on_default_branch': True,
             'release': {'id': 4, 'tag_name': 'v1.2.0-rc.1', 'name': 'Candidate', 'body': '',
                         'published_at': '2025-05-02T00:00:00Z', 'draft': False, 'prerelease': True}},
        ],
        'comparisons': {'stable': [{'release_id': 2, 'status': 'ok',
                                    'commits': [{'sha': 'abc', 'commit': {'message': 'Fixes a bug'}}]}]},
    }
    result = classify_repository(raw)
    assert [row['release_id'] for row in result['predictions']] == [1, 2]
    assert result['predictions'][1]['previous_release_id'] == 1
    assert result['predictions'][1]['prediction'] == 'yes'
    assert result['predictions'][1]['correction_evidence'][0]['source'] == 'release_title'


def test_repository_with_incomplete_release_collection_has_no_predictions():
    result = classify_repository({'repository': 'org/project', 'complete': False,
                                  'releases': [{'release': {'id': 1, 'tag_name': '1.0.0'}}]})
    assert result['status'] == 'incomplete_release_data'
    assert result['predictions'] == []


def test_cfr_b_includes_exact_seven_day_event():
    result = calculate_cfr_b([
        release(1, '2025-01-01T00:00:00Z'),
        release(2, '2025-01-08T00:00:00Z', 'yes')],
        '2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    assert result['numerator'] == 1
    assert result['denominator'] == 2
    assert result['cfr_b'] == 0.5


def test_cfr_b_excludes_event_after_seven_days_and_accepts_before():
    result = calculate_cfr_b([
        release(1, '2025-01-01T00:00:00Z'),
        release(2, '2025-01-08T00:00:01Z', 'yes'),
        release(3, '2025-01-10T00:00:00Z', 'yes')],
        '2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    assert result['audit'][0]['followup_release_ids'] == []
    assert result['audit'][0]['status'] == 'no_observed_correction'
    assert result['numerator'] == 1
    assert result['denominator'] == 3


def test_same_timestamp_is_not_a_subsequent_release_and_multiple_fixes_count_once():
    result = calculate_cfr_b([
        release(1, '2025-01-01T00:00:00Z'),
        release(2, '2025-01-01T00:00:00Z', 'yes'),
        release(3, '2025-01-02T00:00:00Z', 'yes'),
        release(4, '2025-01-03T00:00:00Z', 'yes')],
        '2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    first = next(row for row in result['audit'] if row['release_id'] == 1)
    assert first['followup_release_ids'] == [3, 4]
    assert result['numerator'] == 3


def test_cfr_b_right_censoring_uses_strict_exclusive_end_boundary():
    end = timestamp('2026-01-01T00:00:00Z')
    cutoff = end - timedelta(days=7)
    values = [cutoff - timedelta(microseconds=1), cutoff, cutoff + timedelta(microseconds=1)]
    rows = [release(i, value.isoformat()) for i, value in enumerate(values, start=1)]
    result = calculate_cfr_b(rows, '2025-01-01T00:00:00Z', end.isoformat())
    assert [row['status'] for row in result['audit']] == [
        'no_observed_correction', 'right_censored', 'right_censored']
    assert result['eligible_references'] == 1
    assert result['censored_releases'] == 2
    assert result['denominator'] == 1


def test_cfr_b_unknown_followup_is_not_converted_to_negative():
    result = calculate_cfr_b([
        release(1, '2025-01-01T00:00:00Z'),
        release(2, '2025-01-02T00:00:00Z', 'uncertain')],
        '2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    assert result['uncertain_followup_references'] == 1
    assert result['denominator'] == 1
    assert result['audit'][0]['followed_by_correction'] is None


@pytest.mark.parametrize('values,status', [
    ([release(1, 'bad')], 'invalid_timestamps'),
    ([release(1, None)], 'invalid_timestamps')])
def test_cfr_b_invalid_or_outside_window(values, status):
    result = calculate_cfr_b(values, '2025-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
    assert result['status'] == status
    assert result['cfr_b'] is None


@pytest.mark.parametrize('flag,date', [
    (False, '2025-01-02T00:00:00Z'),
    (True, '2024-12-31T23:59:59Z'),
    (True, '2026-01-01T00:00:00Z')])
def test_cfr_b_rejects_in_window_flag_timestamp_disagreement(flag, date):
    result = calculate_cfr_b([release(1, date, in_window=flag)],
                             '2025-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
    assert result['status'] == 'window_mismatch'
    assert result['cfr_b'] is None


def test_cfr_b_audits_out_of_window_release_without_counting_it():
    result = calculate_cfr_b([release(1, '2024-12-31T23:59:59Z', in_window=False)],
                             '2025-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
    assert result['status'] == 'denominator_zero'
    assert result['outside_window_releases'] == 1
    assert result['audit'][0]['status'] == 'outside_window'


def test_correction_published_at_exclusive_window_end_is_not_observed():
    result = calculate_cfr_b([
        release(1, '2025-01-01T00:00:00Z'),
        release(2, '2025-01-02T00:00:00Z'),
        release(3, '2025-01-09T00:00:00Z', 'yes', in_window=False)],
        '2025-01-01T00:00:00Z', '2025-01-09T00:00:00Z')
    assert result['status'] == 'ok'
    assert result['numerator'] == 0
    assert result['audit'][0]['followup_release_ids'] == [2]


def test_cfr_b_duplicate_ids_incomplete_data_and_zero_denominator():
    args = ('2025-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
    with pytest.raises(ValueError, match='duplicados'):
        calculate_cfr_b([release(1, args[0]), release(1, args[0])], *args)
    incomplete = calculate_cfr_b([release(1, args[0])], *args, complete=False)
    assert incomplete['status'] == 'incomplete_release_data' and incomplete['cfr_b'] is None
    assert incomplete['audit'] == [{'release_id': 1, 'status': 'not_evaluated_incomplete_data',
                                    'followed_by_correction': None}]
    zero = calculate_cfr_b([], *args)
    assert zero['status'] == 'denominator_zero' and zero['cfr_b_percent'] is None


def test_cfr_b_uses_published_at_and_not_commit_dates():
    result = calculate_cfr_b([
        release(1, '2025-01-01T00:00:00Z', commit_date='2025-01-30T00:00:00Z'),
        release(2, '2025-01-02T00:00:00Z', 'yes', commit_date='2024-12-01T00:00:00Z')],
        '2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    assert result['numerator'] == 1
    assert result['audit'][0]['followup_release_ids'] == [2]


def test_aggregate_pools_counts_instead_of_averaging_rates():
    rows = [
        {'status': 'ok', 'numerator': 1, 'denominator': 2, 'releases_analyzed': 4, 'censored_releases': 1},
        {'status': 'ok', 'numerator': 0, 'denominator': 8, 'releases_analyzed': 10, 'censored_releases': 2}]
    result = aggregate_cfr_b(rows)
    assert result['cfr_b'] == 0.1
    assert result['denominator'] == 10


def test_aggregate_does_not_hide_incomplete_repository_results():
    result = aggregate_cfr_b([
        {'repository': 'ok/repo', 'status': 'ok', 'numerator': 1, 'denominator': 2},
        {'repository': 'bad/repo', 'status': 'invalid_timestamps', 'numerator': 0, 'denominator': 0}])
    assert result['status'] == 'partial_data'
    assert result['cfr_b'] == 0.5
    assert result['repositories_included'] == 1
    assert result['excluded_repositories'] == [
        {'repository': 'bad/repo', 'status': 'invalid_timestamps'}]


def test_error_audit_preserves_all_rows_and_configured_followup_days():
    rows = [release(1, 'bad'), release(2, '2025-01-02T00:00:00Z')]
    invalid = calculate_cfr_b(rows, '2025-01-01T00:00:00Z', '2026-01-01T00:00:00Z',
                              followup_days=3)
    assert invalid['followup_days'] == 3
    assert invalid['audit'] == [
        {'release_id': 1, 'status': 'invalid_timestamp', 'followed_by_correction': None},
        {'release_id': 2, 'status': 'not_evaluated_due_to_invalid_timestamps',
         'followed_by_correction': None}]


def test_window_mismatch_audits_every_release():
    result = calculate_cfr_b([
        release(1, '2025-01-02T00:00:00Z', in_window=False),
        release(2, '2025-01-03T00:00:00Z', in_window=True)],
        '2025-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
    assert result['audit'] == [
        {'release_id': 1, 'status': 'window_mismatch', 'followed_by_correction': None},
        {'release_id': 2, 'status': 'not_evaluated_due_to_window_mismatch',
         'followed_by_correction': None}]