from livekit.agents.voice.filler_detection import (
    FillerDetectionConfig,
    FillerDetector,
)


def test_pure_filler():
    """Test: Pure filler words should be detected"""
    print("\n=== Test 1: Pure Filler ===")
    config = FillerDetectionConfig()
    detector = FillerDetector(config)

    test_cases = [
        "uh",
        "umm",
        "hmm uh",
        "uh umm hmm",
        "ah eh er",
    ]

    for transcript in test_cases:
        is_filler, metadata = detector.is_filler_only(transcript, confidence=1.0)
        print(
            f"  '{transcript}' -> {is_filler} (reason: {metadata.reason}, "
            f"fillers: {metadata.matched_fillers})"
        )
        assert is_filler, f"Expected '{transcript}' to be detected as filler"

    print("All pure filler tests passed")


def test_real_interruption():
    """Test: Real interruptions should NOT be detected as filler"""
    print("\n=== Test 2: Real Interruptions ===")
    config = FillerDetectionConfig()
    detector = FillerDetector(config)

    test_cases = [
        "wait",
        "stop",
        "wait one second",
        "no not that one",
        "hold on",
    ]

    for transcript in test_cases:
        is_filler, metadata = detector.is_filler_only(transcript, confidence=1.0)
        print(
            f"  '{transcript}' -> {is_filler} (reason: {metadata.reason}, "
            f"non_fillers: {metadata.non_filler_words})"
        )
        assert not is_filler, f"Expected '{transcript}' to be real speech"

    print("All real interruption tests passed")


def test_mixed_speech():
    """Test: Mixed speech with commands should be allowed"""
    print("\n=== Test 3: Mixed Filler + Command ===")
    config = FillerDetectionConfig(non_filler_ratio_threshold=0.3)
    detector = FillerDetector(config)

    test_cases = [
        ("umm okay stop", True),  # 2/3 = 0.67 non-filler -> allow
        ("uh wait", True),  # 1/2 = 0.5 non-filler -> allow
        ("hmm yeah", True),  # 1/2 = 0.5 non-filler -> allow
        ("uh umm wait", True),  # 1/3 = 0.33 non-filler -> allow
        ("uh umm hmm okay", False),  # 1/4 = 0.25 non-filler -> ignore (below threshold)
    ]

    for transcript, expected_allow in test_cases:
        is_filler, metadata = detector.is_filler_only(transcript, confidence=1.0)
        should_allow = not is_filler
        print(
            f"  '{transcript}' -> allow={should_allow} "
            f"(ratio: {metadata.non_filler_ratio:.2f}, "
            f"fillers: {metadata.matched_fillers}, "
            f"non_fillers: {metadata.non_filler_words})"
        )
        assert (
            should_allow == expected_allow
        ), f"Expected '{transcript}' allow={expected_allow}"

    print("All mixed speech tests passed")


def test_low_confidence():
    """Test: Low confidence transcripts should be ignored"""
    print("\n=== Test 4: Low Confidence ===")
    config = FillerDetectionConfig(min_confidence_threshold=0.5)
    detector = FillerDetector(config)

    test_cases = [
        ("hmm yeah", 0.2, True),  # Low confidence -> ignore
        ("hmm yeah", 0.6, False),  # High confidence -> check content (not pure filler)
        ("wait", 0.1, True),  # Low confidence -> ignore even if command
        ("wait", 0.8, False),  # High confidence -> allow
    ]

    for transcript, confidence, expected_ignore in test_cases:
        is_filler, metadata = detector.is_filler_only(transcript, confidence=confidence)
        print(
            f"  '{transcript}' (conf={confidence}) -> ignore={is_filler} "
            f"(reason: {metadata.reason})"
        )
        assert (
            is_filler == expected_ignore
        ), f"Expected '{transcript}' at {confidence} confidence to be ignore={expected_ignore}"

    print("All low confidence tests passed")


def test_empty_transcript():
    """Test: Empty transcripts should be ignored"""
    print("\n=== Test 5: Empty Transcript ===")
    config = FillerDetectionConfig()
    detector = FillerDetector(config)

    test_cases = ["", "   ", "\t\n"]

    for transcript in test_cases:
        is_filler, metadata = detector.is_filler_only(transcript, confidence=1.0)
        print(f"  '{repr(transcript)}' -> {is_filler} (reason: {metadata.reason})")
        assert is_filler, f"Expected empty transcript to be ignored"

    print("All empty transcript tests passed")


def test_dynamic_updates():
    """Test: Dynamic updates to ignored words list"""
    print("\n=== Test 6: Dynamic Updates ===")
    config = FillerDetectionConfig(
        ignored_words=["uh", "um"], allow_dynamic_updates=True
    )
    detector = FillerDetector(config)

    # Initially "hmm" is not in the list
    is_filler, _ = detector.is_filler_only("hmm", confidence=1.0)
    print(f"  'hmm' before adding -> {is_filler}")
    assert not is_filler, "Expected 'hmm' not to be filler initially"

    # Add "hmm" to the list
    detector.add_ignored_words(["hmm"])
    is_filler, _ = detector.is_filler_only("hmm", confidence=1.0)
    print(f"  'hmm' after adding -> {is_filler}")
    assert is_filler, "Expected 'hmm' to be filler after adding"

    # Remove "hmm" from the list
    detector.remove_ignored_words(["hmm"])
    is_filler, _ = detector.is_filler_only("hmm", confidence=1.0)
    print(f"  'hmm' after removing -> {is_filler}")
    assert not is_filler, "Expected 'hmm' not to be filler after removing"

    print("All dynamic update tests passed")


def test_case_sensitivity():
    """Test: Case insensitive matching"""
    print("\n=== Test 7: Case Sensitivity ===")

    # Case insensitive (default)
    config_insensitive = FillerDetectionConfig(
        ignored_words=["uh"], case_insensitive=True
    )
    detector_insensitive = FillerDetector(config_insensitive)

    for variant in ["uh", "UH", "Uh", "uH"]:
        is_filler, _ = detector_insensitive.is_filler_only(variant, confidence=1.0)
        print(f"  Case insensitive: '{variant}' -> {is_filler}")
        assert is_filler, f"Expected '{variant}' to match with case insensitive"

    # Case sensitive
    config_sensitive = FillerDetectionConfig(
        ignored_words=["uh"], case_insensitive=False
    )
    detector_sensitive = FillerDetector(config_sensitive)

    is_filler, _ = detector_sensitive.is_filler_only("uh", confidence=1.0)
    print(f"  Case sensitive: 'uh' -> {is_filler}")
    assert is_filler

    is_filler, _ = detector_sensitive.is_filler_only("UH", confidence=1.0)
    print(f"  Case sensitive: 'UH' -> {is_filler}")
    assert not is_filler, "Expected 'UH' not to match with case sensitive"

    print("All case sensitivity tests passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Filler Detection Unit Tests")
    print("=" * 60)

    try:
        test_pure_filler()
        test_real_interruption()
        test_mixed_speech()
        test_low_confidence()
        test_empty_transcript()
        test_dynamic_updates()
        test_case_sensitivity()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"TEST FAILED: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()