from backend.moirae.catalog import QUESTIONS
from backend.moirae.alternative_feedback import alternative_feedback

def test_every_alternative_has_editorial_feedback_without_public_leak():
    for question in QUESTIONS:
        feedback=alternative_feedback(question)
        assert len(feedback)==len(question.options)
        assert all(item['explanation'].strip() for item in feedback)
        assert sum(item['correct'] for item in feedback)==1
        assert 'alternatives' not in question.public()
        assert 'explanation' not in question.public()

def test_official_key_matches_validated_batch():
    import json
    from pathlib import Path
    from backend.moirae.catalog import BY_ID
    rows=json.loads(Path('data/inep/enem-2025-validated.json').read_text(encoding='utf-8'))
    expected={136:'c',137:'b',144:'d',146:'b',150:'d',151:'d',152:'d',154:'c'}
    assert len(rows)==8
    for row in rows:
        assert row['answer']==expected[row['source']['number']]
        assert len(row['options'])==len(row['alternative_explanations'])==5
        assert row['source']['visual_review']
        assert BY_ID[row['id']].public()['provenance']['booklet']==7
