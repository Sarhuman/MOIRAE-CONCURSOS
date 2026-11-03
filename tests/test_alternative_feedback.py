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
