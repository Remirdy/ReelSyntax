import statistics
import time

from ReelSyntax_Skills.tools.registry import ROOT, load_index, read_json
from ReelSyntax_Skills.tools.route import route_task


def evaluate(path=None):
    dataset = read_json(path or ROOT / 'tests/routing-eval.json')
    document = load_index()
    results, latencies = [], []
    true_positive = selected_count = relevant_count = top1 = violations = no_match_errors = no_match_count = 0
    for case in dataset['cases']:
        start = time.perf_counter()
        result = route_task(case['task'], document['skills'])
        latencies.append((time.perf_counter() - start) * 1000)
        selected = [row['id'] for row in result['selected']]
        relevant = set(case['relevant'])
        forbidden = set(case.get('forbidden', []))
        true_positive += len(set(selected) & relevant)
        selected_count += len(selected)
        relevant_count += len(relevant)
        top1 += bool(selected and selected[0] in relevant) if relevant else not selected
        violations += bool(set(selected) & forbidden)
        if not relevant:
            no_match_count += 1
            no_match_errors += bool(selected)
        results.append({'id': case['id'], 'selected': selected, 'relevant_found': sorted(set(selected) & relevant),
                        'missed': sorted(relevant - set(selected)), 'forbidden_selected': sorted(set(selected) & forbidden),
                        'body_reads': result['skill_bodies_read'], 'estimated_tokens': result['estimated_loaded_tokens_if_all_selected']})
    return {'dataset_version': dataset['version'], 'case_count': len(results), 'registry_digest': document['digest'],
            'precision_at_k_micro': true_positive / selected_count if selected_count else None,
            'recall_at_k_micro': true_positive / relevant_count if relevant_count else None,
            'top1_accuracy': top1 / len(results), 'hard_constraint_violation_rate': violations / len(results),
            'no_match_error_rate': no_match_errors / no_match_count if no_match_count else None,
            'latency_ms_median': statistics.median(latencies), 'latency_ms_max': max(latencies),
            'scope': 'Local authored routing dataset; incomplete relevance labels can understate precision. No host activation or media correctness is measured.',
            'cases': results}
