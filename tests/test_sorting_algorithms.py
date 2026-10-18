import pandas as pd

from backend.sorting.sorting_algorithms import (
    bubbleSort,
    bucketSort,
    countingSort,
    gnomeSort,
    heapSort,
    insertionSort,
    mergeSort,
    oddEvenSort,
    quickSort,
    heapSort,
    radixSort,
    selectionSort,
)


def _make_dataframe(values):
    return pd.DataFrame({"value": values})


def test_basic_ascending_order():
    df = _make_dataframe([3, 1, 2, 5, 4])
    for sorter in [
        bubbleSort,
        selectionSort,
        insertionSort,
        mergeSort,
        quickSort,
        heapSort,
        gnomeSort,
        countingSort,
        radixSort,
        bucketSort,
        oddEvenSort,
    ]:
        result = sorter(df.copy(), "value")
        assert result["value"].tolist() == [1, 2, 3, 4, 5]


def test_descending_order():
    df = _make_dataframe([3, 1, 2, 5, 4])
    for sorter in [
        bubbleSort,
        selectionSort,
        insertionSort,
        mergeSort,
        quickSort,
        gnomeSort,
        countingSort,
        radixSort,
        bucketSort,
        oddEvenSort,
    ]:
        result = sorter(df.copy(), "value", ascending=False)
        assert result["value"].tolist() == [5, 4, 3, 2, 1]


def test_supports_negatives_and_duplicates():
    df = _make_dataframe([3, -1, 3, 0, -2, 0, 2])
    for sorter in [bubbleSort, insertionSort, quickSort, gnomeSort, bucketSort, oddEvenSort]:
        result = sorter(df.copy(), "value")
        assert result["value"].tolist() == [-2, -1, 0, 0, 2, 3, 3]


def test_string_sorting_and_missing_values():
    df = pd.DataFrame({"value": ["charlie", "alice", None, "bob"]})
    result = bubbleSort(df.copy(), "value")
    assert result["value"].tolist() == ["alice", "bob", "charlie", None]


def test_metrics_are_reported():
    result = bubbleSort(_make_dataframe([3, 1, 2]), "value", return_metrics=True)
    assert result.success is True
    assert result.comparisons >= 1
    assert result.execution_time_ms >= 0
