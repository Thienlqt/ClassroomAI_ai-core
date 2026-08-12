from classroom_ai.policies import refers_to_unavailable_visual


def test_visual_reference_policy_detects_fake_screen_claims():
    assert refers_to_unavailable_visual("Now look at the dog.")
    assert refers_to_unavailable_visual("I have a picture here.")
    assert refers_to_unavailable_visual("See the answer on the screen.")


def test_visual_reference_policy_allows_plain_verbal_teaching():
    assert not refers_to_unavailable_visual("A dog can jump. Can you say that sentence?")
