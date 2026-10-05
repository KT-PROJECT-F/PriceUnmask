from backend.converters import snapshots_to_dataframe


def test_snapshots_to_dataframe_empty():
    df = snapshots_to_dataframe([])

    assert df is not None
    assert df.empty