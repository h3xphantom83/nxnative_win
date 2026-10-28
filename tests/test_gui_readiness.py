from nxnative_gui_readiness import readiness_counts


def test_unchecked():
    assert readiness_counts(None)['status'] == 'Not checked'
    assert readiness_counts([])['passed'] == 0


def test_ready_with_optional_missing():
    result = readiness_counts([
        {'name': 'clang', 'state': 'ok', 'required': True},
        {'name': 'SDK', 'state': 'ok', 'required': True},
        {'name': 'metal-tt', 'state': 'missing', 'required': False},
    ])
    assert result == {'status': 'Ready to build (dependency checks passed)',
                      'passed': 2, 'required': 2, 'issues': 0, 'optional_missing': 1}


def test_missing_and_wrong_both_count_as_required_issues():
    result = readiness_counts([
        {'state': 'missing', 'required': True},
        {'state': 'wrong', 'required': True},
        {'state': 'ok', 'required': True},
    ])
    assert result['issues'] == 2
    assert result['passed'] == 1
    assert result['status'] == 'Required dependencies missing'


def test_optional_wrong_is_not_blocking():
    result = readiness_counts([
        {'state': 'ok', 'required': True},
        {'state': 'wrong', 'required': False},
    ])
    assert result['issues'] == 0
    assert result['optional_missing'] == 1


def test_unknown_required_default_is_blocking():
    result = readiness_counts([{'state': 'unknown'}])
    assert result['issues'] == 1
