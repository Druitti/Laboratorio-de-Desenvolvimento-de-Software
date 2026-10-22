"""Validacao isolada da amostra-ouro e dos rotulos humanos do Lab03."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from urllib.parse import unquote, urlparse
from weakref import WeakSet

from lab03.selection import timestamp

ANNOTATORS = ('santiago', 'ferreira', 'tavares')
SOFTWARE_TYPES = ('library_framework', 'application_service', 'cli_tool', 'other')
YES_NO_UNCERTAIN = ('yes', 'no', 'uncertain')
SAMPLE_FIELDS = (
    'item_id', 'repository', 'repository_id', 'repository_url', 'release_id',
    'release_tag', 'release_url', 'published_at', 'release_notes_url',
    'commits_url', 'selection_procedure', 'eligibility_status', 'selection_reason',
)
LABEL_FIELDS = (
    'annotator_id', 'item_id', 'repository', 'repository_id', 'release_id',
    'software_type', 'user_facing', 'corrective_release', 'justification',
    'evidence_ref', 'evidence_url', 'evidence_insufficient', 'evaluated_at',
)
CONSENSUS_FIELDS = (
    'item_id', 'repository', 'repository_id', 'release_id', 'software_type',
    'user_facing', 'corrective_release', 'consensus_status',
    'consensus_justification', 'evidence_ref', 'evidence_url',
    'remaining_uncertainty', 'discussed_at',
)


_FROZEN_CONSENSUS_TOKEN = object()
_VALID_FROZEN_CONSENSUSES = WeakSet()


@dataclass(frozen=True, init=False, eq=False)
class FrozenConsensus:
    rows: object
    freeze_record: object
    artifact_paths: object

    def __init__(self, rows, freeze_record, artifact_paths, *, _token=None):
        if _token is not _FROZEN_CONSENSUS_TOKEN:
            raise TypeError('FrozenConsensus so pode ser criado pelo fluxo de congelamento.')
        object.__setattr__(self, 'rows', rows)
        object.__setattr__(self, 'freeze_record', freeze_record)
        object.__setattr__(self, 'artifact_paths', artifact_paths)


def _is_sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(character in '0123456789abcdef' for character in value))


def _consensus_rows_sha256(rows):
    payload = [dict(rows[item_id]) for item_id in sorted(rows)]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _valid_frozen_consensus(value):
    if not isinstance(value, FrozenConsensus) or value not in _VALID_FROZEN_CONSENSUSES:
        return False
    record = value.freeze_record
    if not isinstance(record, dict) and not isinstance(record, MappingProxyType):
        return False
    assessment_hashes = record.get('assessment_sha256', {})
    assessment_files = record.get('assessment_files', {})
    agreement = record.get('fleiss', {})
    artifact_paths = value.artifact_paths
    return (
        bool(record.get('sample_file'))
        and
        _is_sha256(record.get('sample_sha256'))
        and _is_sha256(record.get('sample_freeze_record_sha256'))
        and _is_sha256(record.get('consensus_sha256'))
        and _is_sha256(record.get('consensus_rows_sha256'))
        and _is_sha256(record.get('freeze_record_sha256'))
        and bool(record.get('consensus_file'))
        and bool(record.get('freeze_record_file'))
        and set(assessment_hashes) == set(ANNOTATORS)
        and set(assessment_files) == set(ANNOTATORS)
        and all(assessment_files.values())
        and set(artifact_paths) == {'sample', 'sample_freeze', 'consensus', 'freeze_record', 'assessments'}
        and set(artifact_paths['assessments']) == set(ANNOTATORS)
        and Path(artifact_paths['sample']).name == record['sample_file']
        and Path(artifact_paths['consensus']).name == record['consensus_file']
        and Path(artifact_paths['freeze_record']).name == record['freeze_record_file']
        and all(Path(artifact_paths['assessments'][name]).name == assessment_files[name]
            for name in ANNOTATORS)
        and all(_is_sha256(digest) for digest in assessment_hashes.values())
        and set(agreement) == {'software_type', 'user_facing', 'corrective_release'}
        and record.get('items') == len(value.rows) > 0
        and record['consensus_rows_sha256'] == _consensus_rows_sha256(value.rows)
    )


def _frozen_artifacts_unchanged(frozen_consensus):
    record = frozen_consensus.freeze_record
    paths = frozen_consensus.artifact_paths
    expected = {
        'sample': record['sample_sha256'],
        'sample_freeze': record['sample_freeze_record_sha256'],
        'consensus': record['consensus_sha256'],
        'freeze_record': record['freeze_record_sha256'],
        **{f'assessment:{name}': record['assessment_sha256'][name] for name in ANNOTATORS},
    }
    actual_paths = {
        'sample': paths['sample'], 'sample_freeze': paths['sample_freeze'],
        'consensus': paths['consensus'], 'freeze_record': paths['freeze_record'],
        **{f'assessment:{name}': paths['assessments'][name] for name in ANNOTATORS},
    }
    try:
        return all(hashlib.sha256(Path(actual_paths[name]).read_bytes()).hexdigest() == digest
                   for name, digest in expected.items())
    except OSError:
        return False


def _read_csv(path, required_fields, exact_fields=False, *, source_bytes=None):
    stream = (Path(path).open(encoding='utf-8-sig', newline='') if source_bytes is None
              else io.TextIOWrapper(io.BytesIO(source_bytes), encoding='utf-8-sig', newline=''))
    with stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError(f'Cabecalhos duplicados em {path}.')
        if (exact_fields and tuple(fields) != tuple(required_fields)) or not set(required_fields).issubset(fields):
            raise ValueError(f'Esquema CSV invalido em {path}.')
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError(f'Linha com colunas excedentes em {path}.')
    return rows


def _https_url(value):
    parsed = urlparse(value or '')
    return parsed.scheme == 'https' and bool(parsed.hostname)


def _github_repository_url(value, repository, *, exact=False):
    parsed = urlparse(value or '')
    path = [part for part in parsed.path.split('/') if part]
    expected = repository.split('/')
    return (parsed.scheme == 'https' and parsed.hostname in ('github.com', 'www.github.com')
            and [part.casefold() for part in path[:2]] == [part.casefold() for part in expected]
            and (not exact or len(path) == 2))


def _github_release_route(value, repository):
    parsed = urlparse(value or '')
    path = [part for part in parsed.path.split('/') if part]
    expected = repository.split('/')
    if (parsed.scheme != 'https' or parsed.hostname not in ('github.com', 'www.github.com')
            or [part.casefold() for part in path[:2]] != [part.casefold() for part in expected]):
        return None
    if len(path) == 5 and path[2:4] == ['releases', 'tag']:
        return 'tag', unquote(path[4])
    if len(path) == 4 and path[2] == 'releases' and path[3].isdigit():
        return 'id', path[3]
    return None


def _github_commits_url(value, repository):
    if not _github_repository_url(value, repository):
        return False
    path = [part for part in urlparse(value).path.split('/') if part]
    return len(path) >= 4 and path[2] in ('commit', 'commits', 'compare')


def _required(row, field):
    value = row.get(field)
    if value is None or not str(value).strip():
        raise ValueError(f'Campo obrigatorio ausente: {field}.')
    return str(value).strip()


def _required_exact(row, field):
    value = _required(row, field)
    if row[field] != value:
        raise ValueError(f'Identidade nao canonica: {field}.')
    return value


def validate_golden_sample(path, *, expected_repositories=60, releases_per_repository=5,
                           window_start='2025-01-01T00:00:00Z',
                           window_end='2026-01-01T00:00:00Z', source_bytes=None):
    """Validate a project-frozen sample without selecting or replacing any item."""
    rows = _read_csv(path, SAMPLE_FIELDS, source_bytes=source_bytes)
    if expected_repositories <= 0 or releases_per_repository <= 0:
        raise ValueError('Tamanho esperado da amostra deve ser positivo.')
    by_item, repo_ids, repo_names, counts, repo_release_ids = {}, {}, {}, Counter(), set()
    start, end = timestamp(window_start), timestamp(window_end)
    if start >= end:
        raise ValueError('Janela experimental invalida.')
    for row in rows:
        item_id = _required_exact(row, 'item_id')
        repository = _required_exact(row, 'repository')
        repository_id = _required_exact(row, 'repository_id')
        release_id = _required_exact(row, 'release_id')
        if item_id in by_item or (repository, release_id) in repo_release_ids:
            raise ValueError('IDs de item ou pares repositorio/release duplicados.')
        owner, separator, repo_name = repository.partition('/')
        if not separator or not owner or not repo_name or '/' in repo_name:
            raise ValueError(f'Repositorio invalido: {repository}.')
        if not repository_id.isdigit():
            raise ValueError(f'ID de repositorio invalido: {repository_id}.')
        if repository_id in repo_names and repo_names[repository_id] != repository:
            raise ValueError(f'ID de repositorio reutilizado: {repository_id}.')
        if repository in repo_ids and repo_ids[repository] != repository_id:
            raise ValueError(f'ID de repositorio inconsistente: {repository}.')
        repo_ids[repository] = repository_id
        repo_names[repository_id] = repository
        repo_release_ids.add((repository, release_id))
        repository_url = _required(row, 'repository_url')
        if not _github_repository_url(repository_url, repository, exact=True):
            raise ValueError('URL do repositorio nao corresponde a owner/repo.')
        release_tag = _required_exact(row, 'release_tag')
        release_route = _github_release_route(_required(row, 'release_url'), repository)
        expected_route = ('tag', release_tag)
        if release_route != expected_route and release_route != ('id', release_id):
            raise ValueError('URL release nao corresponde a tag/ID declarado.')
        notes_route = _github_release_route(_required(row, 'release_notes_url'), repository)
        if notes_route != release_route:
            raise ValueError('URL de notas nao corresponde a release declarada.')
        if not _github_commits_url(_required(row, 'commits_url'), repository):
            raise ValueError('URL de commits nao corresponde a owner/repo.')
        published = timestamp(_required(row, 'published_at'))
        if not start <= published < end:
            raise ValueError('Release da amostra fora da janela experimental.')
        _required(row, 'selection_procedure')
        _required(row, 'selection_reason')
        if row.get('eligibility_status') != 'eligible':
            raise ValueError('A amostra congelada so pode conter itens elegiveis.')
        by_item[item_id] = row
        counts[repository] += 1
    if len(repo_ids) != expected_repositories:
        raise ValueError(f'Esperados {expected_repositories} repositorios; encontrados {len(repo_ids)}.')
    if len(rows) != expected_repositories * releases_per_repository:
        raise ValueError('Quantidade de releases difere do tamanho definido para a amostra.')
    if any(counts[repository] != releases_per_repository for repository in repo_ids):
        raise ValueError(f'Cada repositorio deve contribuir exatamente {releases_per_repository} releases.')
    content = source_bytes if source_bytes is not None else Path(path).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    return {'rows': by_item, 'sha256': digest, 'repositories': len(repo_ids), 'releases': len(rows),
            'window_start': timestamp(window_start).isoformat(),
            'window_end': timestamp(window_end).isoformat()}


def write_sample_freeze_record(sample_path, output_path, selection_criteria, random_seed=None,
                               *, expected_repositories=60, releases_per_repository=5):
    """Write a hash/criteria record without modifying the frozen sample."""
    path = Path(output_path)
    if path.exists():
        raise FileExistsError(path)
    sample = validate_golden_sample(sample_path, expected_repositories=expected_repositories,
                                    releases_per_repository=releases_per_repository)
    _required({'selection_criteria': selection_criteria}, 'selection_criteria')
    record = {'sample_sha256': sample['sha256'], 'repositories': sample['repositories'],
              'releases': sample['releases'], 'window_start': sample['window_start'],
              'window_end': sample['window_end'], 'selection_criteria': selection_criteria,
              'random_seed': random_seed, 'frozen_at': datetime.now(timezone.utc).isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    return record


def write_individual_templates(sample, output_dir):
    """Create separate blank label sheets; fail rather than overwrite any assessment."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    targets = {annotator: out / f'human_labels_{annotator}.csv' for annotator in ANNOTATORS}
    existing = [path for path in targets.values() if path.exists()]
    if existing:
        raise FileExistsError(existing[0])
    paths = {}
    for annotator in ANNOTATORS:
        path = targets[annotator]
        with path.open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=LABEL_FIELDS, lineterminator='\n')
            writer.writeheader()
            for item in sample['rows'].values():
                writer.writerow({
                    'annotator_id': annotator,
                    'item_id': item['item_id'], 'repository': item['repository'],
                    'repository_id': item['repository_id'], 'release_id': item['release_id'],
                    'software_type': '', 'user_facing': '', 'corrective_release': '',
                    'justification': '', 'evidence_ref': '', 'evidence_url': '',
                    'evidence_insufficient': '', 'evaluated_at': '',
                })
        paths[annotator] = path
    return paths


def _validate_label_rows(path, sample, expected_annotator, source_bytes=None):
    rows = _read_csv(path, LABEL_FIELDS, exact_fields=True, source_bytes=source_bytes)
    result = {}
    for row in rows:
        item_id = _required_exact(row, 'item_id')
        if item_id not in sample:
            raise ValueError(f'Item fora da amostra congelada: {item_id}.')
        if item_id in result:
            raise ValueError(f'Item duplicado na rotulagem: {item_id}.')
        if row.get('annotator_id') != expected_annotator:
            raise ValueError(f'Arquivo nao pertence ao avaliador {expected_annotator}.')
        expected = sample[item_id]
        for field in ('repository', 'repository_id', 'release_id'):
            if row.get(field) != expected[field]:
                raise ValueError(f'Identidade divergente para {item_id}: {field}.')
        if row.get('software_type') not in SOFTWARE_TYPES:
            raise ValueError(f'Categoria software_type invalida em {item_id}.')
        if row.get('user_facing') not in YES_NO_UNCERTAIN:
            raise ValueError(f'Categoria user_facing invalida em {item_id}.')
        if row.get('corrective_release') not in YES_NO_UNCERTAIN:
            raise ValueError(f'Categoria corrective_release invalida em {item_id}.')
        if not _required(row, 'justification') or not _required(row, 'evidence_ref'):
            raise ValueError(f'Justificativa/evidencia ausente em {item_id}.')
        if not _https_url(_required(row, 'evidence_url')):
            raise ValueError(f'URL de evidencia invalida em {item_id}.')
        if row.get('evidence_insufficient') not in ('true', 'false'):
            raise ValueError(f'evidence_insufficient invalido em {item_id}.')
        if 'uncertain' in (row['software_type'], row['user_facing'], row['corrective_release']):
            if row['evidence_insufficient'] != 'true':
                raise ValueError(f'Incerteza sem indicador de evidencia insuficiente em {item_id}.')
        timestamp(_required(row, 'evaluated_at'))
        result[item_id] = row
    missing = set(sample) - set(result)
    if missing:
        raise ValueError(f'Rotulagem incompleta: {len(missing)} itens ausentes.')
    return result


def validate_independent_assessments(sample, assessment_paths, *, source_bytes=None):
    """Require the same complete frozen IDs in three isolated, schema-identical files."""
    if set(assessment_paths) != set(ANNOTATORS):
        raise ValueError(f'Sao obrigatorios os tres avaliadores: {", ".join(ANNOTATORS)}.')
    return {annotator: _validate_label_rows(assessment_paths[annotator], sample['rows'], annotator,
                                             (source_bytes or {}).get(annotator))
            for annotator in ANNOTATORS}


def fleiss_kappa(assessments, dimension):
    """Fleiss kappa for three fixed raters; `uncertain` is a substantive category."""
    if set(assessments) != set(ANNOTATORS):
        raise ValueError('Fleiss exige as tres avaliacoes independentes.')
    item_sets = [set(assessments[name]) for name in ANNOTATORS]
    if not item_sets[0] or any(items != item_sets[0] for items in item_sets[1:]):
        raise ValueError('IDs ou quantidade de itens diferem entre avaliadores.')
    if dimension not in ('software_type', 'user_facing', 'corrective_release'):
        raise ValueError(f'Dimensao desconhecida: {dimension}.')
    categories = SOFTWARE_TYPES if dimension == 'software_type' else YES_NO_UNCERTAIN
    counts = []
    for item_id in sorted(item_sets[0]):
        values = [assessments[name][item_id][dimension] for name in ANNOTATORS]
        if any(value not in categories for value in values):
            raise ValueError(f'Categoria invalida em {dimension} para {item_id}.')
        counts.append([values.count(category) for category in categories])
    item_agreement = [
        (sum(count * count for count in row) - len(ANNOTATORS)) /
        (len(ANNOTATORS) * (len(ANNOTATORS) - 1)) for row in counts]
    item_count = len(counts)
    proportions = [sum(row[index] for row in counts) / (item_count * len(ANNOTATORS))
                   for index in range(len(categories))]
    observed = sum(item_agreement) / item_count
    expected = sum(value * value for value in proportions)
    denominator = 1 - expected
    return {'dimension': dimension, 'items': item_count, 'raters': len(ANNOTATORS),
            'categories': list(categories), 'observed_agreement': observed,
            'expected_agreement': expected,
            'kappa': (observed - expected) / denominator if denominator else None,
            'status': 'ok' if denominator else 'zero_expected_disagreement'}


def validate_consensus(sample, path, *, source_bytes=None):
    """Validate human discussion output without deriving consensus by vote."""
    rows = _read_csv(path, CONSENSUS_FIELDS, exact_fields=True, source_bytes=source_bytes)
    result = {}
    for row in rows:
        item_id = _required_exact(row, 'item_id')
        if item_id not in sample['rows']:
            raise ValueError(f'Consenso contem item fora da amostra: {item_id}.')
        if item_id in result:
            raise ValueError(f'Item duplicado no consenso: {item_id}.')
        original = sample['rows'][item_id]
        for field in ('repository', 'repository_id', 'release_id'):
            if row.get(field) != original[field]:
                raise ValueError(f'Identidade divergente no consenso para {item_id}.')
        if row.get('software_type') not in SOFTWARE_TYPES:
            raise ValueError(f'software_type invalido no consenso para {item_id}.')
        for field in ('user_facing', 'corrective_release'):
            if row.get(field) not in YES_NO_UNCERTAIN:
                raise ValueError(f'{field} invalido no consenso para {item_id}.')
        if row.get('consensus_status') not in ('resolved', 'unresolved'):
            raise ValueError(f'Status de consenso invalido para {item_id}.')
        if row['consensus_status'] == 'unresolved':
            _required(row, 'remaining_uncertainty')
        _required(row, 'consensus_justification')
        _required(row, 'evidence_ref')
        if not _https_url(_required(row, 'evidence_url')):
            raise ValueError(f'URL de evidencia invalida no consenso para {item_id}.')
        timestamp(_required(row, 'discussed_at'))
        result[item_id] = row
    if set(result) != set(sample['rows']):
        raise ValueError('Consenso nao corresponde integralmente a amostra congelada.')
    return result


def freeze_human_consensus(sample_path, sample_freeze_path, assessment_paths,
                           consensus_path, output_path, *, expected_repositories=60,
                           releases_per_repository=5):
    """Freeze consensus only after all independent human and identity checks pass."""
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(output_path)
    source_paths = {
        'sample': Path(sample_path), 'sample_freeze': Path(sample_freeze_path),
        'consensus': Path(consensus_path),
        **{f'assessment:{name}': Path(path) for name, path in assessment_paths.items()},
    }
    input_bytes = {name: path.read_bytes() for name, path in source_paths.items()}
    hashes_before = {name: hashlib.sha256(content).hexdigest()
                     for name, content in input_bytes.items()}
    sample = validate_golden_sample(sample_path, expected_repositories=expected_repositories,
                                    releases_per_repository=releases_per_repository,
                                    source_bytes=input_bytes['sample'])
    sample_record = json.loads(input_bytes['sample_freeze'].decode('utf-8'))
    required_freeze_fields = {
        'sample_sha256', 'repositories', 'releases', 'window_start', 'window_end',
        'selection_criteria', 'random_seed', 'frozen_at',
    }
    if (not isinstance(sample_record, dict)
            or not required_freeze_fields.issubset(sample_record)
            or not isinstance(sample_record['selection_criteria'], str)
            or not sample_record['selection_criteria'].strip()
            or type(sample_record['repositories']) is not int
            or type(sample_record['releases']) is not int
            or not _is_sha256(sample_record['sample_sha256'])):
        raise ValueError('Manifesto de amostra congelada incompleto ou invalido.')
    timestamp(sample_record['frozen_at'])
    if sample_record.get('sample_sha256') != sample['sha256']:
        raise ValueError('Hash do manifesto de amostra nao corresponde ao arquivo congelado.')
    if (sample_record['repositories'] != sample['repositories']
            or sample_record['releases'] != sample['releases']
            or sample_record['window_start'] != sample['window_start']
            or sample_record['window_end'] != sample['window_end']):
        raise ValueError('Metadados do manifesto de amostra divergem do arquivo congelado.')
    assessment_bytes = {name: input_bytes[f'assessment:{name}'] for name in ANNOTATORS
                        if f'assessment:{name}' in input_bytes}
    assessments = validate_independent_assessments(sample, assessment_paths,
                                                   source_bytes=assessment_bytes)
    agreement = {dimension: fleiss_kappa(assessments, dimension)
                 for dimension in ('software_type', 'user_facing', 'corrective_release')}
    consensus = validate_consensus(sample, consensus_path, source_bytes=input_bytes['consensus'])
    hashes_after = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for name, path in source_paths.items()}
    if hashes_before != hashes_after or hashes_before['sample'] != sample['sha256']:
        raise ValueError('Arquivo de entrada mudou durante o congelamento do consenso.')
    record = {
        'sample_file': Path(sample_path).name,
        'sample_sha256': hashes_before['sample'],
        'sample_freeze_record_sha256': hashes_before['sample_freeze'],
        'assessment_files': {name: Path(assessment_paths[name]).name for name in ANNOTATORS},
        'assessment_sha256': {name: hashes_before[f'assessment:{name}']
                              for name in ANNOTATORS},
        'consensus_file': Path(consensus_path).name,
        'consensus_sha256': hashes_before['consensus'],
        'consensus_rows_sha256': _consensus_rows_sha256(consensus),
        'freeze_record_file': output_path.name,
        'items': len(consensus), 'fleiss': agreement,
        'frozen_at': datetime.now(timezone.utc).isoformat(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_bytes = (json.dumps(record, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    freeze_digest = hashlib.sha256(freeze_bytes).hexdigest()
    with output_path.open('xb') as stream:
        stream.write(freeze_bytes)
    frozen_rows = MappingProxyType({item_id: MappingProxyType(dict(row))
                                    for item_id, row in consensus.items()})
    frozen_record = dict(record)
    frozen_record['freeze_record_sha256'] = freeze_digest
    frozen_record['assessment_files'] = MappingProxyType(dict(record['assessment_files']))
    frozen_record['assessment_sha256'] = MappingProxyType(dict(record['assessment_sha256']))
    frozen_record['fleiss'] = MappingProxyType({
        dimension: MappingProxyType({**values, 'categories': tuple(values['categories'])})
        for dimension, values in record['fleiss'].items()
    })
    artifact_paths = MappingProxyType({
        'sample': Path(sample_path), 'sample_freeze': Path(sample_freeze_path),
        'consensus': Path(consensus_path), 'freeze_record': output_path,
        'assessments': MappingProxyType({name: Path(assessment_paths[name]) for name in ANNOTATORS}),
    })
    frozen = FrozenConsensus(frozen_rows, MappingProxyType(frozen_record), artifact_paths,
                             _token=_FROZEN_CONSENSUS_TOKEN)
    _VALID_FROZEN_CONSENSUSES.add(frozen)
    return frozen


def evaluate_corrective_predictions(predictions, frozen_consensus, heuristic_version):
    """Evaluate only a frozen, validated human reference; uncertain cases are exclusions."""
    if not _valid_frozen_consensus(frozen_consensus):
        raise RuntimeError('A avaliacao exige objeto de consenso congelado e validado.')
    if not _frozen_artifacts_unchanged(frozen_consensus):
        raise RuntimeError('Artefatos da referencia humana mudaram apos o congelamento.')
    consensus = frozen_consensus.rows
    prediction_by_release = {}
    for prediction in predictions:
        repository, release_id = prediction.get('repository'), prediction.get('release_id')
        if not repository or release_id is None:
            raise ValueError('Previsao sem identidade.')
        if prediction.get('prediction') not in YES_NO_UNCERTAIN:
            raise ValueError('Categoria de previsao invalida ou ausente.')
        key = (repository, str(release_id))
        if key in prediction_by_release:
            raise ValueError('Previsao sem identidade ou duplicada.')
        if prediction.get('heuristic_version') != heuristic_version:
            raise ValueError('Versao de heuristica divergente entre previsoes.')
        prediction_by_release[key] = prediction
    expected_predictions = {(row['repository'], str(row['release_id'])) for row in consensus.values()}
    if set(prediction_by_release) - expected_predictions:
        raise ValueError('Previsoes contem releases fora do consenso congelado.')
    missing_predictions = expected_predictions - set(prediction_by_release)
    if missing_predictions:
        raise ValueError(f'Previsoes ausentes para {len(missing_predictions)} itens do consenso.')
    if not _valid_frozen_consensus(frozen_consensus):
        raise RuntimeError('Consenso humano foi alterado durante a validacao das previsoes.')
    if not _frozen_artifacts_unchanged(frozen_consensus):
        raise RuntimeError('Artefatos da referencia humana mudaram durante a validacao das previsoes.')
    return score_corrective_pairs(consensus, prediction_by_release, heuristic_version)


def score_corrective_pairs(consensus, prediction_by_release, heuristic_version):
    """Score references already validated by a human-consensus workflow.

    Callers must first validate/freeze their reference, require one versioned
    prediction per (repository, release_id), and reject duplicate/missing IDs.
    This calculation alone is not evidence of independent human validation.
    ``uncertain`` predictions are abstentions, with explicit coverage/exclusions.
    """
    tp = fp = tn = fn = 0
    exclusions = []
    for item_id, human in consensus.items():
        key = (human['repository'], str(human['release_id']))
        prediction = prediction_by_release.get(key)
        if human.get('consensus_status') != 'resolved':
            reason = 'consensus_unresolved'
        elif human.get('corrective_release') not in ('yes', 'no'):
            reason = 'consensus_uncertain'
        elif prediction['prediction'] == 'uncertain':
            reason = 'prediction_uncertain'
        else:
            reason = None
        if reason:
            exclusions.append({'item_id': item_id, 'reason': reason})
            continue
        expected, actual = human['corrective_release'], prediction['prediction']
        if expected == 'yes' and actual == 'yes':
            tp += 1
        elif expected == 'no' and actual == 'yes':
            fp += 1
        elif expected == 'no' and actual == 'no':
            tn += 1
        else:
            fn += 1
    precision_denominator = tp + fp
    recall_denominator = tp + fn
    f1_denominator = 2 * tp + fp + fn
    precision = tp / precision_denominator if precision_denominator else None
    recall = tp / recall_denominator if recall_denominator else None
    f1 = 2 * tp / f1_denominator if f1_denominator else None
    items_total = len(consensus)
    items_evaluated = tp + fp + tn + fn
    prediction_uncertain = sum(prediction['prediction'] == 'uncertain'
                               for prediction in prediction_by_release.values())
    determinate_predictions = len(prediction_by_release) - prediction_uncertain
    return {'heuristic_version': heuristic_version, 'items_total': len(consensus),
            'items_evaluated': items_evaluated, 'items_excluded': len(exclusions),
            'exclusions': exclusions, 'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
            'prediction_coverage': determinate_predictions / items_total if items_total else None,
            'evaluation_coverage': items_evaluated / items_total if items_total else None,
            'prediction_uncertain': prediction_uncertain,
            'precision': precision, 'recall': recall, 'f1': f1,
            'status': 'ok' if f1 is not None else 'zero_metric_denominator'}
