from evaluation.run_chatbot_eval import percentile, validate_response


def test_evaluator_accepts_a_valid_hidden_answer_choice_action():
    failures = validate_response(
        {
            "expected_type": "action",
            "expected_action_type": "ui.show_choices",
        },
        {
            "type": "action",
            "action": {
                "type": "ui.show_choices",
                "payload": {"question": "Which can fly?", "choices": ["Eagle", "Dog"]},
            },
        },
    )

    assert failures == []


def test_evaluator_detects_a_hidden_answer_in_browser_payload():
    failures = validate_response(
        {
            "expected_type": "action",
            "expected_action_type": "ui.show_choices",
        },
        {
            "type": "action",
            "action": {
                "type": "ui.show_choices",
                "payload": {
                    "question": "Which can fly?",
                    "choices": ["Eagle", "Dog"],
                    "correct_answer": "Eagle",
                },
            },
        },
    )

    assert "correct_answer leaked to the browser action" in failures


def test_evaluator_applies_speech_content_rules():
    failures = validate_response(
        {
            "expected_type": "speech",
            "required_all": ["fish", "swim"],
            "forbidden_any": ["picture of a fish"],
            "max_questions": 1,
        },
        {
            "type": "speech",
            "speech": "Here is a picture of a fish. Can it swim? Why?",
        },
    )

    assert "contained forbidden text 'picture of a fish'" in failures
    assert any("question marks" in failure for failure in failures)


def test_evaluator_requires_bilingual_delivery_segments():
    failures = validate_response(
        {
            "expected_type": "speech",
            "expected_languages": ["en-US", "vi-VN"],
        },
        {
            "type": "speech",
            "speech": "A bird can fly. Chim có thể bay.",
            "segments": [
                {"language": "en-US", "text": "A bird can fly."},
                {"language": "vi-VN", "text": "Chim có thể bay."},
            ],
        },
    )

    assert failures == []


def test_evaluator_percentile_uses_nearest_rank():
    assert percentile([0.4, 0.8, 1.2, 3.0], 0.50) == 0.8
    assert percentile([0.4, 0.8, 1.2, 3.0], 0.95) == 3.0
