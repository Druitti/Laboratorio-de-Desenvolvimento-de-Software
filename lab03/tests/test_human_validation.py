"""Synthetic workflow tests for frozen samples and independent human labels."""
import csv
from types import MappingProxyType

import pytest
import lab03.human_validation as human_validation

from lab03.human_validation import (ANNOTATORS, CONSENSUS_FIELDS, FrozenConsensus, LABEL_FIELDS,
                                    SAMPLE_FIELDS, evaluate_corrective_predictions,
                                    fleiss_kappa, freeze_human_consensus,
                                    validate_consensus,
                                    validate_golden_sample,
                                    validate_independent_assessments,
                                    write_individual_templates,
                                    write_sample_freeze_record)

WINDOW_START = '2025-01-01T00:00:00Z'
WINDOW_END = '2026-01-01T00:00:00Z'


def write_rows(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def sample_rows(repository_count=2, releases_per_repository=3):
    rows = []
    for repo_number in range(1, repository_count + 1):
        repository = f'org/repo{repo_number}'
        for release_number in range(1, releases_per_repository + 1):
            item_number = len(rows) + 1
            release_id = str(repo_number * 100 + release_number)
            release_url = f'https://github.com/{repository}/releases/tag/v1.{release_number}.0'
            rows.append({
                'item_id': f'item-{item_number}', 'repository': repository,
                'repository_id': str(1000 + repo_number),
                'repository_url': f'https://github.com/{repository}',
                'release_id': release_id, 'release_tag': f'v1.{release_number}.0',
                'release_url': release_url, 'published_at': f'2025-02-{release_number:02d}T00:00:00Z',
                'release_notes_url': release_url,
                'commits_url': f'https://github.com/{repository}/commits/main/',
                'selection_procedure': 'synthetic deterministic fixture',
                'eligibility_status': 'eligible', 'selection_reason': 'synthetic test item',
            })
    return rows


def write_sample(tmp_path, rows=None):
    path = tmp_path / 'gold_sample.csv'
    write_rows(path, SAMPLE_FIELDS, rows if rows is not None else sample_rows())
    return path


def make_label_rows(sample, annotator, corrective=None):
    values = corrective or ['yes', 'no', 'yes', 'no', 'uncertain', 'no']
    rows = []
    for index, item in enumerate(sample['rows'].values()):
        label = values[index]
        rows.append({
            'annotator_id': annotator, 'item_id': item['item_id'],
            'repository': item['repository'], 'repository_id': item['repository_id'],
            'release_id': item['release_id'], 'software_type': 'library_framework',
            'user_facing': 'yes', 'corrective_release': label,
            'justification': 'Fixture evidence supports this label.',
            'evidence_ref': 'release notes, section 1',
            'evidence_url': item['release_notes_url'],
            'evidence_insufficient': 'true' if label == 'uncertain' else 'false',
            'evaluated_at': '2026-10-15T12:00:00Z',
        })
    return rows


def write_label_files(tmp_path, sample):
    paths = {}
    for annotator in ANNOTATORS:
        path = tmp_path / f'human_labels_{annotator}.csv'
        write_rows(path, LABEL_FIELDS, make_label_rows(sample, annotator))
        paths[annotator] = path
    return paths


def consensus_rows(sample):
    labels = ['yes', 'yes', 'no', 'no', 'uncertain', 'no']
    rows = []
    for index, item in enumerate(sample['rows'].values()):
        rows.append({
            'item_id': item['item_id'], 'repository': item['repository'],
            'repository_id': item['repository_id'], 'release_id': item['release_id'],
            'software_type': 'library_framework', 'user_facing': 'yes',
            'corrective_release': labels[index],
            'consensus_status': 'unresolved' if index == 5 else 'resolved',
            'consensus_justification': 'Discussion evidence recorded.',
            'evidence_ref': 'release notes, section 1',
            'evidence_url': item['release_notes_url'],
            'remaining_uncertainty': 'Discussed but unresolved' if index == 5 else '',
            'discussed_at': '2026-10-15T12:00:00Z',
        })
    return rows


def freeze_synthetic_consensus(tmp_path, sample, rows=None):
    sample_path = tmp_path / 'gold_sample.csv'
    write_rows(sample_path, SAMPLE_FIELDS, list(sample['rows'].values()))
    sample_freeze_path = tmp_path / 'sample_freeze.json'
    write_sample_freeze_record(sample_path, sample_freeze_path, 'synthetic procedure',
                               expected_repositories=2, releases_per_repository=3)
    assessment_paths = write_label_files(tmp_path, sample)
    consensus_path = tmp_path / 'human_consensus.csv'
    write_rows(consensus_path, CONSENSUS_FIELDS, rows if rows is not None else consensus_rows(sample))
    return freeze_human_consensus(sample_path, sample_freeze_path, assessment_paths,
                                  consensus_path, tmp_path / 'consensus_freeze.json',
                                  expected_repositories=2, releases_per_repository=3)


def test_golden_sample_validates_size_links_window_and_hash(tmp_path):
    path = write_sample(tmp_path)
    result = validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)
    assert result['repositories'] == 2
    assert result['releases'] == 6
    assert len(result['sha256']) == 64
    assert set(result['rows']) == {f'item-{index}' for index in range(1, 7)}


def test_golden_sample_rejects_wrong_size_duplicate_and_bad_window(tmp_path):
    path = write_sample(tmp_path, sample_rows()[:-1])
    with pytest.raises(ValueError, match='Quantidade'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)
    rows = sample_rows()
    rows[1]['item_id'] = rows[0]['item_id']
    write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='duplicados'):
        validate_golden_sample(tmp_path / 'gold_sample.csv', expected_repositories=2,
                               releases_per_repository=3)
    rows = sample_rows()
    rows[0]['published_at'] = WINDOW_END
    write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='fora da janela'):
        validate_golden_sample(tmp_path / 'gold_sample.csv', expected_repositories=2,
                               releases_per_repository=3)


def test_golden_sample_requires_evidence_urls_and_eligible_status(tmp_path):
    rows = sample_rows()
    rows[0]['commits_url'] = ''
    path = write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='obrigatorio ausente'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)
    rows[0]['commits_url'] = 'https://github.com/org/repo1/commits/main/'
    rows[0]['eligibility_status'] = 'pending'
    write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='elegiveis'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)


def test_golden_sample_rejects_invalid_window_and_repository_id(tmp_path):
    path = write_sample(tmp_path)
    with pytest.raises(ValueError, match='Janela experimental invalida'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3,
                               window_start=WINDOW_END, window_end=WINDOW_END)
    rows = sample_rows()
    rows[0]['repository_id'] = 'not-numeric'
    write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='ID de repositorio invalido'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)


@pytest.mark.parametrize(('field', 'value'), [
    ('repository', ' org/repo1'), ('release_id', '101 '),
])
def test_golden_sample_rejects_noncanonical_identity_whitespace(tmp_path, field, value):
    rows = sample_rows()
    rows[0][field] = value
    path = write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='Identidade nao canonica'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)


def test_golden_sample_rejects_links_or_repository_ids_from_other_repo(tmp_path):
    rows = sample_rows()
    rows[0]['release_url'] = 'https://github.com/elsewhere/wrong/releases/tag/v1'
    path = write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='URL release nao corresponde'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)
    rows = sample_rows()
    rows[0]['release_url'] = 'https://github.com/org/repo1/releases/tag/v9.9.9'
    write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='URL release nao corresponde'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)
    rows[0]['release_url'] = 'https://github.com/org/repo1/releases/tag/v1.1.0'
    rows[0]['release_notes_url'] = 'https://github.com/org/repo1/releases/tag/v9.9.9'
    write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='URL de notas nao corresponde'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)
    rows = sample_rows()
    rows[3]['repository_id'] = rows[0]['repository_id']
    write_sample(tmp_path, rows)
    with pytest.raises(ValueError, match='ID de repositorio reutilizado'):
        validate_golden_sample(path, expected_repositories=2, releases_per_repository=3)


def test_freeze_record_hashes_but_does_not_overwrite(tmp_path):
    sample_path = write_sample(tmp_path)
    freeze_path = tmp_path / 'sample_freeze.json'
    record = write_sample_freeze_record(
        sample_path, freeze_path, 'synthetic procedure', expected_repositories=2,
        releases_per_repository=3, random_seed=7)
    assert record['random_seed'] == 7
    assert len(record['sample_sha256']) == 64
    with pytest.raises(FileExistsError):
        write_sample_freeze_record(sample_path, freeze_path, 'different')


def test_individual_templates_are_isolated_and_never_overwrite(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    paths = write_individual_templates(sample, tmp_path / 'labels')
    assert set(paths) == set(ANNOTATORS)
    sheets = {name: list(csv.DictReader(path.open(encoding='utf-8', newline='')))
              for name, path in paths.items()}
    item_ids = [row['item_id'] for row in sheets['santiago']]
    assert all([row['item_id'] for row in rows] == item_ids for rows in sheets.values())
    assert all({row['annotator_id'] for row in rows} == {name}
               for name, rows in sheets.items())
    assert all(not row['corrective_release'] for rows in sheets.values() for row in rows)
    assert all('heuristic' not in path.read_text(encoding='utf-8').lower() for path in paths.values())
    with pytest.raises(FileExistsError):
        write_individual_templates(sample, tmp_path / 'labels')


def test_template_creation_does_not_leave_partial_assessor_files(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    output = tmp_path / 'partial'
    output.mkdir()
    (output / 'human_labels_tavares.csv').write_text('existing', encoding='utf-8')
    with pytest.raises(FileExistsError):
        write_individual_templates(sample, output)
    assert not (output / 'human_labels_santiago.csv').exists()
    assert not (output / 'human_labels_ferreira.csv').exists()


def test_three_complete_individual_files_match_same_sample(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    paths = write_label_files(tmp_path, sample)
    assessments = validate_independent_assessments(sample, paths)
    assert set(assessments) == set(ANNOTATORS)
    assert all(len(rows) == 6 for rows in assessments.values())


def test_assessment_barrier_rejects_missing_assessor_or_ids(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    paths = write_label_files(tmp_path, sample)
    with pytest.raises(ValueError, match='tres avaliadores'):
        validate_independent_assessments(sample, {'santiago': paths['santiago']})
    rows = make_label_rows(sample, 'santiago')[:-1]
    write_rows(paths['santiago'], LABEL_FIELDS, rows)
    with pytest.raises(ValueError, match='incompleta'):
        validate_independent_assessments(sample, paths)


def test_individual_and_consensus_item_ids_must_be_canonical(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    paths = write_label_files(tmp_path, sample)
    labels = make_label_rows(sample, 'santiago')
    labels[0]['item_id'] = ' item-1 '
    write_rows(paths['santiago'], LABEL_FIELDS, labels)
    with pytest.raises(ValueError, match='Identidade nao canonica: item_id'):
        validate_independent_assessments(sample, paths)
    rows = consensus_rows(sample)
    rows[0]['item_id'] = ' item-1 '
    path = tmp_path / 'human_consensus.csv'
    write_rows(path, CONSENSUS_FIELDS, rows)
    with pytest.raises(ValueError, match='Identidade nao canonica: item_id'):
        validate_consensus(sample, path)


@pytest.mark.parametrize('field,value,reason', [
    ('corrective_release', 'maybe', 'Categoria corrective_release'),
    ('evidence_url', '', 'obrigatorio ausente'),
    ('evidence_insufficient', '', 'evidence_insufficient'),
    ('evaluated_at', 'not-a-date', 'Invalid isoformat'),
])
def test_assessment_rejects_invalid_fields(tmp_path, field, value, reason):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    paths = write_label_files(tmp_path, sample)
    rows = make_label_rows(sample, 'santiago')
    rows[0][field] = value
    write_rows(paths['santiago'], LABEL_FIELDS, rows)
    with pytest.raises(ValueError, match=reason):
        validate_independent_assessments(sample, paths)


def test_uncertain_label_requires_insufficient_evidence_flag(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    paths = write_label_files(tmp_path, sample)
    rows = make_label_rows(sample, 'santiago')
    rows[0]['corrective_release'] = 'uncertain'
    rows[0]['evidence_insufficient'] = 'false'
    write_rows(paths['santiago'], LABEL_FIELDS, rows)
    with pytest.raises(ValueError, match='Incerteza sem indicador'):
        validate_independent_assessments(sample, paths)


def test_fleiss_kappa_treats_uncertain_as_a_category():
    ids = ('a', 'b', 'c')
    values = ('yes', 'no', 'uncertain')
    assessments = {
        annotator: {item_id: {'corrective_release': value}
                    for item_id, value in zip(ids, values)}
        for annotator in ANNOTATORS
    }
    result = fleiss_kappa(assessments, 'corrective_release')
    assert result['items'] == 3
    assert result['categories'] == ['yes', 'no', 'uncertain']
    assert result['kappa'] == 1.0


def test_fleiss_kappa_zero_expected_disagreement_is_explicit():
    assessments = {annotator: {'a': {'user_facing': 'yes'}} for annotator in ANNOTATORS}
    result = fleiss_kappa(assessments, 'user_facing')
    assert result['kappa'] is None
    assert result['status'] == 'zero_expected_disagreement'


def test_fleiss_rejects_incomplete_or_invalid_dimensions():
    assessments = {annotator: {'a': {'corrective_release': 'yes'}} for annotator in ANNOTATORS}
    assessments['tavares'] = {}
    with pytest.raises(ValueError, match='IDs ou quantidade'):
        fleiss_kappa(assessments, 'corrective_release')
    assessments['tavares'] = {'a': {'corrective_release': 'yes'}}
    with pytest.raises(ValueError, match='Dimensao desconhecida'):
        fleiss_kappa(assessments, 'unknown')
    assessments = {annotator: {'a': {'corrective_release': 'invalid'}} for annotator in ANNOTATORS}
    with pytest.raises(ValueError, match='Categoria invalida'):
        fleiss_kappa(assessments, 'corrective_release')


def test_consensus_requires_exact_sample_and_manual_status(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                    releases_per_repository=3)
    path = tmp_path / 'consensus.csv'
    rows = consensus_rows(sample)
    write_rows(path, CONSENSUS_FIELDS, rows)
    result = validate_consensus(sample, path)
    assert len(result) == 6
    assert result['item-6']['consensus_status'] == 'unresolved'
    rows.pop()
    write_rows(path, CONSENSUS_FIELDS, rows)
    with pytest.raises(ValueError, match='nao corresponde'):
        validate_consensus(sample, path)


def test_consensus_cannot_freeze_without_three_complete_assessments(tmp_path):
    sample_path = write_sample(tmp_path)
    sample = validate_golden_sample(sample_path, expected_repositories=2,
                                    releases_per_repository=3)
    sample_freeze = tmp_path / 'sample_freeze.json'
    write_sample_freeze_record(sample_path, sample_freeze, 'synthetic procedure',
                               expected_repositories=2, releases_per_repository=3)
    assessments = write_label_files(tmp_path, sample)
    consensus_path = tmp_path / 'human_consensus.csv'
    write_rows(consensus_path, CONSENSUS_FIELDS, consensus_rows(sample))
    freeze_path = tmp_path / 'consensus_freeze.json'
    with pytest.raises(ValueError, match='tres avaliadores'):
        freeze_human_consensus(sample_path, sample_freeze,
                               {key: value for key, value in assessments.items() if key != 'tavares'},
                               consensus_path, freeze_path, expected_repositories=2,
                               releases_per_repository=3)
    assert not freeze_path.exists()


def test_consensus_freeze_rejects_sample_changed_after_freezing(tmp_path):
    sample_path = write_sample(tmp_path)
    sample = validate_golden_sample(sample_path, expected_repositories=2,
                                    releases_per_repository=3)
    sample_freeze = tmp_path / 'sample_freeze.json'
    write_sample_freeze_record(sample_path, sample_freeze, 'synthetic procedure',
                               expected_repositories=2, releases_per_repository=3)
    assessments = write_label_files(tmp_path, sample)
    consensus_path = tmp_path / 'human_consensus.csv'
    write_rows(consensus_path, CONSENSUS_FIELDS, consensus_rows(sample))
    rows = sample_rows()
    rows[0]['selection_reason'] = 'mutated after freeze'
    write_sample(sample_path.parent, rows)
    freeze_path = tmp_path / 'consensus_freeze.json'
    with pytest.raises(ValueError, match='Hash do manifesto'):
        freeze_human_consensus(sample_path, sample_freeze, assessments,
                               consensus_path, freeze_path, expected_repositories=2,
                               releases_per_repository=3)
    assert not freeze_path.exists()


def test_consensus_freeze_rejects_incomplete_sample_record(tmp_path):
    sample_path = write_sample(tmp_path)
    sample = validate_golden_sample(sample_path, expected_repositories=2,
                                    releases_per_repository=3)
    sample_freeze = tmp_path / 'sample_freeze.json'
    sample_freeze.write_text('{' + f'"sample_sha256":"{sample["sha256"]}"' + '}', encoding='utf-8')
    assessments = write_label_files(tmp_path, sample)
    consensus_path = tmp_path / 'human_consensus.csv'
    write_rows(consensus_path, CONSENSUS_FIELDS, consensus_rows(sample))
    freeze_path = tmp_path / 'consensus_freeze.json'
    with pytest.raises(ValueError, match='Manifesto de amostra congelada incompleto'):
        freeze_human_consensus(sample_path, sample_freeze, assessments, consensus_path,
                               freeze_path, expected_repositories=2, releases_per_repository=3)
    assert not freeze_path.exists()


def test_consensus_freeze_rejects_input_mutation_during_validation(tmp_path, monkeypatch):
    sample_path = write_sample(tmp_path)
    sample = validate_golden_sample(sample_path, expected_repositories=2,
                                    releases_per_repository=3)
    sample_freeze = tmp_path / 'sample_freeze.json'
    write_sample_freeze_record(sample_path, sample_freeze, 'synthetic procedure',
                               expected_repositories=2, releases_per_repository=3)
    assessments = write_label_files(tmp_path, sample)
    consensus_path = tmp_path / 'human_consensus.csv'
    write_rows(consensus_path, CONSENSUS_FIELDS, consensus_rows(sample))
    original_validate = human_validation.validate_consensus

    def mutate_assessment_after_validation(validated_sample, consensus_file, *, source_bytes=None):
        result = original_validate(validated_sample, consensus_file, source_bytes=source_bytes)
        with assessments['santiago'].open('ab') as stream:
            stream.write(b'\n')
        return result

    monkeypatch.setattr(human_validation, 'validate_consensus', mutate_assessment_after_validation)
    freeze_path = tmp_path / 'consensus_freeze.json'
    with pytest.raises(ValueError, match='mudou durante o congelamento'):
        freeze_human_consensus(sample_path, sample_freeze, assessments, consensus_path,
                               freeze_path, expected_repositories=2, releases_per_repository=3)
    assert not freeze_path.exists()


def test_unresolved_consensus_requires_remaining_uncertainty(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                    releases_per_repository=3)
    rows = consensus_rows(sample)
    rows[-1]['remaining_uncertainty'] = ''
    path = tmp_path / 'consensus.csv'
    write_rows(path, CONSENSUS_FIELDS, rows)
    with pytest.raises(ValueError, match='remaining_uncertainty'):
        validate_consensus(sample, path)


def test_prediction_evaluation_requires_frozen_consensus_and_version(tmp_path):
    with pytest.raises(RuntimeError, match='consenso congelado'):
        evaluate_corrective_predictions([], {}, '1.0.7')
    with pytest.raises(TypeError, match='so pode ser criado'):
        FrozenConsensus({}, {}, {})
    forged = object.__new__(FrozenConsensus)
    object.__setattr__(forged, 'rows', {})
    object.__setattr__(forged, 'freeze_record', {})
    with pytest.raises(RuntimeError, match='objeto de consenso congelado'):
        evaluate_corrective_predictions([], forged, '1.0.7')
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    frozen = freeze_synthetic_consensus(tmp_path, sample)
    with pytest.raises(ValueError, match='Versao de heuristica'):
        evaluate_corrective_predictions([{'repository': 'org/repo1', 'release_id': 101,
                                          'heuristic_version': '1.0.6',
                                          'prediction': 'yes'}], frozen, '1.0.7')
    with pytest.raises(ValueError, match='Previsao sem identidade'):
        evaluate_corrective_predictions([{'repository': 'org/repo1',
                                          'heuristic_version': '1.0.7', 'prediction': 'yes'}],
                                        frozen, '1.0.7')


def test_frozen_consensus_provenance_is_deeply_read_only(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    frozen = freeze_synthetic_consensus(tmp_path, sample)
    with pytest.raises(TypeError):
        frozen.freeze_record['assessment_sha256']['santiago'] = '0' * 64
    with pytest.raises(TypeError):
        frozen.freeze_record['fleiss']['corrective_release']['kappa'] = 0.0


def test_evaluation_rejects_consensus_rows_modified_after_freeze(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    frozen = freeze_synthetic_consensus(tmp_path, sample)
    changed_rows = dict(frozen.rows)
    item_id = next(iter(changed_rows))
    changed_rows[item_id] = MappingProxyType({**changed_rows[item_id], 'corrective_release': 'no'})
    object.__setattr__(frozen, 'rows', MappingProxyType(changed_rows))
    predictions = [{'repository': row['repository'], 'release_id': row['release_id'],
                    'heuristic_version': '1.0.7', 'prediction': 'no'}
                   for row in sample['rows'].values()]
    with pytest.raises(RuntimeError, match='objeto de consenso congelado'):
        evaluate_corrective_predictions(predictions, frozen, '1.0.7')


def test_evaluation_rejects_artifact_change_after_freeze(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    frozen = freeze_synthetic_consensus(tmp_path, sample)
    with frozen.artifact_paths['assessments']['santiago'].open('ab') as stream:
        stream.write(b'\n')
    predictions = [{'repository': item['repository'], 'release_id': item['release_id'],
                    'heuristic_version': '1.0.7', 'prediction': 'no'}
                   for item in sample['rows'].values()]
    with pytest.raises(RuntimeError, match='Artefatos da referencia humana mudaram'):
        evaluate_corrective_predictions(predictions, frozen, '1.0.7')


def test_evaluation_rejects_freeze_manifest_change_after_freeze(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    frozen = freeze_synthetic_consensus(tmp_path, sample)
    with frozen.artifact_paths['freeze_record'].open('ab') as stream:
        stream.write(b' ')
    predictions = [{'repository': item['repository'], 'release_id': item['release_id'],
                    'heuristic_version': '1.0.7', 'prediction': 'no'}
                   for item in sample['rows'].values()]
    with pytest.raises(RuntimeError, match='Artefatos da referencia humana mudaram'):
        evaluate_corrective_predictions(predictions, frozen, '1.0.7')


def test_evaluation_rechecks_artifacts_after_consuming_predictions(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    frozen = freeze_synthetic_consensus(tmp_path, sample)

    def predictions_with_side_effect():
        for item in sample['rows'].values():
            yield {'repository': item['repository'], 'release_id': item['release_id'],
                   'heuristic_version': '1.0.7', 'prediction': 'no'}
        with frozen.artifact_paths['freeze_record'].open('ab') as stream:
            stream.write(b' ')

    with pytest.raises(RuntimeError, match='mudaram durante a validacao das previsoes'):
        evaluate_corrective_predictions(predictions_with_side_effect(), frozen, '1.0.7')


def test_evaluation_rechecks_consensus_rows_after_consuming_predictions(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    frozen = freeze_synthetic_consensus(tmp_path, sample)

    def predictions_that_mutate_frozen_rows():
        for item in sample['rows'].values():
            yield {'repository': item['repository'], 'release_id': item['release_id'],
                   'heuristic_version': '1.0.7', 'prediction': 'no'}
        changed_rows = dict(frozen.rows)
        first_item = next(iter(changed_rows))
        changed_rows[first_item] = MappingProxyType({
            **changed_rows[first_item], 'corrective_release': 'no'})
        object.__setattr__(frozen, 'rows', MappingProxyType(changed_rows))

    with pytest.raises(RuntimeError, match='Consenso humano foi alterado'):
        evaluate_corrective_predictions(predictions_that_mutate_frozen_rows(), frozen, '1.0.7')


def test_confusion_metrics_exclusions_and_zero_denominators(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    path = tmp_path / 'consensus.csv'
    write_rows(path, CONSENSUS_FIELDS, consensus_rows(sample))
    frozen = freeze_synthetic_consensus(tmp_path, sample, consensus_rows(sample))
    predictions = []
    labels = ['yes', 'no', 'yes', 'no', 'uncertain', 'yes']
    for item, prediction in zip(sample['rows'].values(), labels):
        predictions.append({'repository': item['repository'], 'release_id': item['release_id'],
                            'heuristic_version': '1.0.7', 'prediction': prediction})
    result = evaluate_corrective_predictions(predictions, frozen, '1.0.7')
    assert (result['tp'], result['fp'], result['tn'], result['fn']) == (1, 1, 1, 1)
    assert result['precision'] == 0.5 and result['recall'] == 0.5 and result['f1'] == 0.5
    assert result['items_evaluated'] == 4 and result['items_excluded'] == 2
    assert [row['reason'] for row in result['exclusions']] == [
        'consensus_uncertain', 'consensus_unresolved']
    unresolved_rows = consensus_rows(sample)
    for row in unresolved_rows:
        row['consensus_status'] = 'unresolved'
        row['remaining_uncertainty'] = 'Synthetic unresolved case'
    zero_dir = tmp_path / 'zero_denominator'
    zero_dir.mkdir()
    unresolved = freeze_synthetic_consensus(zero_dir, sample, unresolved_rows)
    zero_predictions = [{'repository': item['repository'], 'release_id': item['release_id'],
                         'heuristic_version': '1.0.7', 'prediction': 'no'}
                        for item in sample['rows'].values()]
    zero = evaluate_corrective_predictions(zero_predictions, unresolved, '1.0.7')
    assert zero['precision'] is None and zero['recall'] is None and zero['f1'] is None
    assert zero['status'] == 'zero_metric_denominator'


def test_prediction_uncertainty_missing_and_extra_predictions_are_audited(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    path = tmp_path / 'consensus.csv'
    rows = consensus_rows(sample)
    for row in rows:
        row['consensus_status'] = 'resolved'
        row['corrective_release'] = 'no'
    write_rows(path, CONSENSUS_FIELDS, rows)
    frozen = freeze_synthetic_consensus(tmp_path, sample, rows)
    predictions = []
    for index, item in enumerate(sample['rows'].values()):
        predictions.append({'repository': item['repository'], 'release_id': item['release_id'],
                            'heuristic_version': '1.0.7',
                            'prediction': 'uncertain' if index == 0 else 'no'})
    result = evaluate_corrective_predictions(predictions, frozen, '1.0.7')
    assert result['items_excluded'] == 1
    assert result['exclusions'][0]['reason'] == 'prediction_uncertain'
    assert result['prediction_coverage'] == pytest.approx(5 / 6)
    assert result['prediction_uncertain'] == 1
    assert result['evaluation_coverage'] == pytest.approx(5 / 6)
    with pytest.raises(ValueError, match='Previsoes ausentes'):
        evaluate_corrective_predictions(predictions[:-1], frozen, '1.0.7')
    for invalid_prediction in ('maybe', ''):
        malformed = [dict(prediction) for prediction in predictions]
        malformed[0]['prediction'] = invalid_prediction
        with pytest.raises(ValueError, match='Categoria de previsao invalida'):
            evaluate_corrective_predictions(malformed, frozen, '1.0.7')
    missing_field = [dict(prediction) for prediction in predictions]
    missing_field[0].pop('prediction')
    with pytest.raises(ValueError, match='Categoria de previsao invalida'):
        evaluate_corrective_predictions(missing_field, frozen, '1.0.7')
    predictions.append({'repository': 'other/repo', 'release_id': 1,
                        'heuristic_version': '1.0.7', 'prediction': 'yes'})
    with pytest.raises(ValueError, match='fora do consenso'):
        evaluate_corrective_predictions(predictions, frozen, '1.0.7')


def test_all_abstentions_are_counted_even_when_consensus_excludes_items(tmp_path):
    sample = validate_golden_sample(write_sample(tmp_path), expected_repositories=2,
                                     releases_per_repository=3)
    rows = consensus_rows(sample)
    for row in rows:
        row['consensus_status'] = 'unresolved'
        row['remaining_uncertainty'] = 'Synthetic unresolved case'
    frozen = freeze_synthetic_consensus(tmp_path, sample, rows)
    predictions = [{'repository': item['repository'], 'release_id': item['release_id'],
                    'heuristic_version': '1.0.7', 'prediction': 'uncertain'}
                   for item in sample['rows'].values()]
    result = evaluate_corrective_predictions(predictions, frozen, '1.0.7')
    assert result['prediction_uncertain'] == 6
    assert result['prediction_coverage'] == 0.0
    assert result['evaluation_coverage'] == 0.0
