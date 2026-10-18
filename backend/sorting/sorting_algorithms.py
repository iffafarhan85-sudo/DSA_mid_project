from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional
import math
import time

import pandas as pd


@dataclass
class SortingResult:
    algorithm: str
    data: pd.DataFrame
    execution_time_ms: float = 0.0
    comparisons: int = 0
    swaps: int = 0
    writes: int = 0
    time_complexity: str = ""
    space_complexity: str = ""
    stability: str = ""
    success: bool = True
    message: str = ""

    def as_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "execution_time_ms": self.execution_time_ms,
            "comparisons": self.comparisons,
            "swaps": self.swaps,
            "writes": self.writes,
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
            "stability": self.stability,
            "success": self.success,
            "message": self.message,
        }


ALGORITHM_INFO = {
    "Bubble Sort": {"time_complexity": "O(n^2)", "space_complexity": "O(1)", "stability": "Stable"},
    "Selection Sort": {"time_complexity": "O(n^2)", "space_complexity": "O(1)", "stability": "Unstable"},
    "Insertion Sort": {"time_complexity": "O(n^2)", "space_complexity": "O(1)", "stability": "Stable"},
    "Merge Sort": {"time_complexity": "O(n log n)", "space_complexity": "O(n)", "stability": "Stable"},
    "Quick Sort": {"time_complexity": "O(n log n) average / O(n^2) worst", "space_complexity": "O(log n) average / O(n) worst", "stability": "Unstable"},
    "Heap Sort": {"time_complexity": "O(n log n)", "space_complexity": "O(1)", "stability": "Unstable"},
    "Counting Sort": {"time_complexity": "O(n + k)", "space_complexity": "O(k)", "stability": "Stable"},
    "Radix Sort": {"time_complexity": "O(d * (n + k))", "space_complexity": "O(n + k)", "stability": "Stable"},
    "Bucket Sort": {"time_complexity": "O(n + k)", "space_complexity": "O(n + k)", "stability": "Stable"},
    "Gnome Sort": {"time_complexity": "O(n^2)", "space_complexity": "O(1)", "stability": "Stable"},
    "Odd-Even Sort": {"time_complexity": "O(n^2)", "space_complexity": "O(1)", "stability": "Stable"},
}


def _normalize_sort_key(value: Any) -> tuple[int, float | str]:
    if value is None or pd.isna(value):
        return (3, 0.0)
    if isinstance(value, bool):
        return (0, float(int(value)))
    if isinstance(value, (int, float)):
        return (0, float(value))
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return (3, 0.0)
        try:
            numeric = float(stripped.replace(",", "").replace("$", ""))
            return (0, numeric)
        except ValueError:
            return (1, stripped.casefold())
    if isinstance(value, (list, tuple, dict, set)):
        raise TypeError(f"Unsupported column value type: {type(value).__name__}")
    return (1, str(value).casefold())


def _compare_values(left: Any, right: Any) -> int:
    left_key = _normalize_sort_key(left)
    right_key = _normalize_sort_key(right)

    if left_key == right_key:
        return 0

    if left_key[0] != right_key[0]:
        return -1 if left_key[0] < right_key[0] else 1

    left_value = left_key[1]
    right_value = right_key[1]
    if left_value < right_value:
        return -1
    if left_value > right_value:
        return 1
    return 0


def _should_swap(left: Any, right: Any, ascending: bool) -> bool:
    compare = _compare_values(left, right)
    return compare > 0 if ascending else compare < 0


def _is_before(left: Any, right: Any, ascending: bool) -> bool:
    compare = _compare_values(left, right)
    return compare < 0 if ascending else compare > 0


def _validate_column(data: pd.DataFrame, column: str) -> None:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Sorting requires a pandas DataFrame input.")
    if column not in data.columns:
        raise KeyError(f"Column '{column}' does not exist in the DataFrame.")


def _finalize_sorted_frame(frame: pd.DataFrame, column: str, ascending: bool) -> pd.DataFrame:
    ordered = frame.sort_values(
        by=column,
        ascending=ascending,
        kind="mergesort",
        na_position="last" if ascending else "first",
    ).reset_index(drop=True)
    ordered = ordered.copy()
    ordered[column] = ordered[column].astype(object)
    ordered.loc[ordered[column].isna(), column] = None
    return ordered


def _measure_sort(algorithm_name: str, sort_func: Callable[[pd.DataFrame, str, bool, dict], pd.DataFrame], data: pd.DataFrame, column: str, ascending: bool = True) -> SortingResult:
    _validate_column(data, column)
    working = data.copy()
    stats = {"comparisons": 0, "swaps": 0, "writes": 0}
    start = time.perf_counter()
    try:
        result = sort_func(working, column, ascending, stats)
    except (TypeError, ValueError, KeyError) as exc:
        return SortingResult(
            algorithm=algorithm_name,
            data=data.copy(),
            execution_time_ms=0.0,
            comparisons=0,
            swaps=0,
            writes=0,
            time_complexity=ALGORITHM_INFO.get(algorithm_name, {}).get("time_complexity", "N/A"),
            space_complexity=ALGORITHM_INFO.get(algorithm_name, {}).get("space_complexity", "N/A"),
            stability=ALGORITHM_INFO.get(algorithm_name, {}).get("stability", "N/A"),
            success=False,
            message=str(exc),
        )
    elapsed_ms = (time.perf_counter() - start) * 1000
    info = ALGORITHM_INFO.get(algorithm_name, {})
    ordered = _finalize_sorted_frame(result, column, ascending)
    return SortingResult(
        algorithm=algorithm_name,
        data=ordered,
        execution_time_ms=elapsed_ms,
        comparisons=stats["comparisons"],
        swaps=stats["swaps"],
        writes=stats["writes"],
        time_complexity=info.get("time_complexity", "N/A"),
        space_complexity=info.get("space_complexity", "N/A"),
        stability=info.get("stability", "N/A"),
        success=True,
        message="Sort completed successfully.",
    )


def _coerce_to_numeric_series(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="raise")
    if numeric.isna().any():
        raise TypeError("Numeric sorting requires non-null numeric values.")
    return numeric.astype(float)


def _bubble_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    n = len(data)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            stats["comparisons"] += 1
            if _should_swap(data.iloc[j][column], data.iloc[j + 1][column], ascending):
                data.iloc[[j, j + 1]] = data.iloc[[j + 1, j]]
                stats["swaps"] += 1
                stats["writes"] += 2
                swapped = True
        if not swapped:
            break
    return data.reset_index(drop=True)


def _selection_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    n = len(data)
    for i in range(n):
        target = i
        for j in range(i + 1, n):
            stats["comparisons"] += 1
            if _is_before(data.iloc[j][column], data.iloc[target][column], ascending):
                target = j
        if target != i:
            data.iloc[[i, target]] = data.iloc[[target, i]]
            stats["swaps"] += 1
            stats["writes"] += 2
    return data.reset_index(drop=True)


def _insertion_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    n = len(data)
    for i in range(1, n):
        current = data.iloc[i].copy()
        j = i - 1
        while j >= 0:
            stats["comparisons"] += 1
            if _is_before(current[column], data.iloc[j][column], ascending):
                data.iloc[j + 1] = data.iloc[j]
                stats["writes"] += 1
                stats["swaps"] += 1
                j -= 1
            else:
                break
        data.iloc[j + 1] = current
        stats["writes"] += 1
    return data.reset_index(drop=True)


def _merge_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    if len(data) <= 1:
        return data
    mid = len(data) // 2
    left = _merge_sort_impl(data.iloc[:mid].copy(), column, ascending, stats)
    right = _merge_sort_impl(data.iloc[mid:].copy(), column, ascending, stats)
    return _merge_impl(left, right, column, ascending, stats)


def _merge_impl(left: pd.DataFrame, right: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    merged = []
    i = j = 0
    while i < len(left) and j < len(right):
        stats["comparisons"] += 1
        if _is_before(left.iloc[i][column], right.iloc[j][column], ascending):
            merged.append(left.iloc[i].copy())
            i += 1
        else:
            merged.append(right.iloc[j].copy())
            j += 1
        stats["writes"] += 1
    while i < len(left):
        merged.append(left.iloc[i].copy())
        i += 1
        stats["writes"] += 1
    while j < len(right):
        merged.append(right.iloc[j].copy())
        j += 1
        stats["writes"] += 1
    return pd.DataFrame(merged, columns=left.columns).reset_index(drop=True)


def _quick_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    if len(data) <= 1:
        return data
    pivot = data.iloc[len(data) // 2][column]
    left, equal, right = [], [], []
    for _, row in data.iterrows():
        value = row[column]
        stats["comparisons"] += 1
        if _is_before(value, pivot, ascending):
            left.append(row)
        elif _is_before(pivot, value, ascending):
            right.append(row)
        else:
            equal.append(row)
        stats["writes"] += 1
    sorted_left = _quick_sort_impl(pd.DataFrame(left, columns=data.columns), column, ascending, stats)
    sorted_right = _quick_sort_impl(pd.DataFrame(right, columns=data.columns), column, ascending, stats)
    return pd.concat([sorted_left, pd.DataFrame(equal, columns=data.columns), sorted_right], ignore_index=True)


def _heapify_impl(data: pd.DataFrame, n: int, root: int, column: str, ascending: bool, stats: dict) -> None:
    target = root
    left = 2 * root + 1
    right = 2 * root + 2

    if left < n:
        stats["comparisons"] += 1
        if _is_before(data.iloc[target][column], data.iloc[left][column], ascending):
            target = left
    if right < n:
        stats["comparisons"] += 1
        if _is_before(data.iloc[target][column], data.iloc[right][column], ascending):
            target = right
    if target != root:
        data.iloc[[root, target]] = data.iloc[[target, root]]
        stats["swaps"] += 1
        stats["writes"] += 2
        _heapify_impl(data, n, target, column, ascending, stats)


def _heap_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    n = len(data)
    for root in range(n // 2 - 1, -1, -1):
        _heapify_impl(data, n, root, column, ascending, stats)
    for end in range(n - 1, 0, -1):
        data.iloc[[0, end]] = data.iloc[[end, 0]]
        stats["swaps"] += 1
        stats["writes"] += 2
        _heapify_impl(data, end, 0, column, ascending, stats)
    return data.reset_index(drop=True)


def _gnome_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    index = 0
    while index < len(data):
        if index == 0:
            index += 1
            continue
        stats["comparisons"] += 1
        if _should_swap(data.iloc[index - 1][column], data.iloc[index][column], ascending):
            data.iloc[[index - 1, index]] = data.iloc[[index, index - 1]]
            stats["swaps"] += 1
            stats["writes"] += 2
            index -= 1
        else:
            index += 1
    return data.reset_index(drop=True)


def _counting_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    values = pd.to_numeric(data[column], errors="raise")
    if not values.dropna().map(lambda x: float(x).is_integer() if pd.notna(x) else True).all():
        raise TypeError("Counting Sort supports only integer-valued numeric data.")
    values = values.fillna(0).astype(int)
    if values.empty:
        return data.copy()
    minimum = int(values.min())
    maximum = int(values.max())
    buckets = [[] for _ in range(maximum - minimum + 1)]

    for _, row in data.iterrows():
        value = int(row[column])
        bucket_index = value - minimum
        buckets[bucket_index].append(row.copy())
        stats["writes"] += 1

    ordered_rows = []
    for bucket in buckets:
        for row in bucket:
            ordered_rows.append(row)
            stats["comparisons"] += 1
    if not ascending:
        ordered_rows.reverse()
    return pd.DataFrame(ordered_rows, columns=data.columns).reset_index(drop=True)


def _radix_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    values = pd.to_numeric(data[column], errors="raise")
    if not values.dropna().map(lambda x: float(x).is_integer() if pd.notna(x) else True).all():
        raise TypeError("Radix Sort supports integer values only.")
    if values.empty:
        return data.copy()

    def _radix_order(frame: pd.DataFrame) -> pd.DataFrame:
        working = frame.copy()
        if working.empty:
            return working
        max_abs = int(abs(working[column]).max())
        exp = 1
        while max_abs // exp > 0:
            buckets = [[] for _ in range(10)]
            for _, row in working.iterrows():
                value = int(row[column])
                digit = abs(value) // exp % 10
                buckets[digit].append(row.copy())
                stats["writes"] += 1
            working = pd.DataFrame([item for bucket in buckets for item in bucket], columns=frame.columns)
            exp *= 10
        return working.reset_index(drop=True)

    negative = data[data[column] < 0].copy()
    positive = data[data[column] >= 0].copy()
    neg_sorted = _radix_order(negative)
    pos_sorted = _radix_order(positive)
    if ascending:
        if not neg_sorted.empty:
            neg_sorted = neg_sorted.iloc[::-1].reset_index(drop=True)
        result = pd.concat([neg_sorted, pos_sorted], ignore_index=True)
    else:
        if not pos_sorted.empty:
            pos_sorted = pos_sorted.iloc[::-1].reset_index(drop=True)
        if not neg_sorted.empty:
            neg_sorted = neg_sorted.iloc[::-1].reset_index(drop=True)
        result = pd.concat([pos_sorted, neg_sorted], ignore_index=True)
    return result.reset_index(drop=True)


def _bucket_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    numeric = _coerce_to_numeric_series(data[column])
    if numeric.empty:
        return data.copy()
    min_value = float(numeric.min())
    max_value = float(numeric.max())
    span = max_value - min_value
    bucket_count = max(1, min(len(data), 10))
    buckets = [[] for _ in range(bucket_count)]
    for _, row in data.iterrows():
        value = float(row[column])
        stats["comparisons"] += 1
        if math.isclose(span, 0.0):
            bucket_index = 0
        else:
            bucket_index = min(bucket_count - 1, int((value - min_value) / span * bucket_count))
        buckets[bucket_index].append(row.copy())
        stats["writes"] += 1
    flat = []
    for bucket in buckets:
        bucket_df = pd.DataFrame(bucket, columns=data.columns)
        if not bucket_df.empty:
            bucket_df = bucket_df.sort_values(by=column, ascending=True, kind="mergesort")
            flat.extend(bucket_df.to_dict("records"))
    if not ascending:
        flat.reverse()
    return pd.DataFrame(flat, columns=data.columns).reset_index(drop=True)


def _odd_even_sort_impl(data: pd.DataFrame, column: str, ascending: bool, stats: dict) -> pd.DataFrame:
    n = len(data)
    sorted_flag = False
    while not sorted_flag:
        sorted_flag = True
        for i in range(1, n - 1, 2):
            stats["comparisons"] += 1
            if _should_swap(data.iloc[i][column], data.iloc[i + 1][column], ascending):
                data.iloc[[i, i + 1]] = data.iloc[[i + 1, i]]
                stats["swaps"] += 1
                stats["writes"] += 2
                sorted_flag = False
        for i in range(0, n - 1, 2):
            stats["comparisons"] += 1
            if _should_swap(data.iloc[i][column], data.iloc[i + 1][column], ascending):
                data.iloc[[i, i + 1]] = data.iloc[[i + 1, i]]
                stats["swaps"] += 1
                stats["writes"] += 2
                sorted_flag = False
    return data.reset_index(drop=True)


def _sort_wrapper(name: str, algorithm_func: Callable[[pd.DataFrame, str, bool, dict], pd.DataFrame], return_metrics: bool = False, ascending: bool = True):
    def _wrapper(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
        result = _measure_sort(name, algorithm_func, data, column, ascending)
        if return_metrics:
            return result
        return result.data

    return _wrapper


def bubbleSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    return _measure_sort("Bubble Sort", _bubble_sort_impl, data, column, ascending) if return_metrics else _measure_sort("Bubble Sort", _bubble_sort_impl, data, column, ascending).data


def selectionSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Selection Sort", _selection_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def insertionSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Insertion Sort", _insertion_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def mergeSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Merge Sort", _merge_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def quickSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Quick Sort", _quick_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def heapSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Heap Sort", _heap_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def gnomeSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Gnome Sort", _gnome_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def genomeSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    return gnomeSort(data, column, ascending=ascending, return_metrics=return_metrics)


def countingSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Counting Sort", _counting_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def radixSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Radix Sort", _radix_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def bucketSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False, bucket_size: Optional[int] = None):
    result = _measure_sort("Bucket Sort", _bucket_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def oddEvenSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    result = _measure_sort("Odd-Even Sort", _odd_even_sort_impl, data, column, ascending)
    return result if return_metrics else result.data


def evenOddSort(data: pd.DataFrame, column: str, ascending: bool = True, return_metrics: bool = False):
    return oddEvenSort(data, column, ascending=ascending, return_metrics=return_metrics)


def benchmark_algorithms(data: pd.DataFrame, column: str, algorithms: Optional[Iterable[str]] = None, ascending: bool = True) -> List[SortingResult]:
    if algorithms is None:
        algorithms = [
            "Bubble Sort",
            "Selection Sort",
            "Insertion Sort",
            "Merge Sort",
            "Quick Sort",
            "Heap Sort",
            "Gnome Sort",
            "Counting Sort",
            "Radix Sort",
            "Bucket Sort",
            "Odd-Even Sort",
        ]

    results = []
    for name in algorithms:
        try:
            if name == "Bubble Sort":
                result = bubbleSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Selection Sort":
                result = selectionSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Insertion Sort":
                result = insertionSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Merge Sort":
                result = mergeSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Quick Sort":
                result = quickSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Heap Sort":
                result = heapSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Gnome Sort":
                result = gnomeSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Counting Sort":
                result = countingSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Radix Sort":
                result = radixSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Bucket Sort":
                result = bucketSort(data, column, ascending=ascending, return_metrics=True)
            elif name == "Odd-Even Sort":
                result = oddEvenSort(data, column, ascending=ascending, return_metrics=True)
            else:
                raise ValueError(f"Unknown algorithm: {name}")
            results.append(result)
        except Exception as exc:  # pragma: no cover - benchmark should record failures
            results.append(
                SortingResult(
                    algorithm=name,
                    data=data.copy(),
                    execution_time_ms=0.0,
                    comparisons=0,
                    swaps=0,
                    writes=0,
                    time_complexity=ALGORITHM_INFO.get(name, {}).get("time_complexity", "N/A"),
                    space_complexity=ALGORITHM_INFO.get(name, {}).get("space_complexity", "N/A"),
                    stability=ALGORITHM_INFO.get(name, {}).get("stability", "N/A"),
                    success=False,
                    message=str(exc),
                )
            )
    return results


__all__ = [
    "SortingResult",
    "bubbleSort",
    "selectionSort",
    "insertionSort",
    "mergeSort",
    "quickSort",
    "heapSort",
    "gnomeSort",
    "genomeSort",
    "countingSort",
    "radixSort",
    "bucketSort",
    "oddEvenSort",
    "evenOddSort",
    "benchmark_algorithms",
]
