"""
trend_engine.py
===============
Core regression engine for the Trend Analysis tab.

This is a direct port of the numerical core of the standalone Streamlit
"Piecewise Regression Dashboard" (regression.py) into the Django platform,
so that both the map/inventory explorer and the trend-analysis dashboard
run inside ONE Django program.

Provides:
  * ``SegmentResult``           - dataclass with all fitted statistics for one segment.
  * ``fit_piecewise_regression``- split a series at breakpoints, fit OLS /
                                  Huber / Theil-Sen per segment.
  * ``mann_kendall_test``       - non-parametric monotonic trend test.
  * ``sens_slope``              - Sen's slope estimator with CI.
  * ``prediction_band``         - pointwise prediction interval for plotting.

No Django or Streamlit imports: pure numpy / scipy / statsmodels, so the
module remains unit-testable in isolation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Literal, Sequence

import numpy as np
import statsmodels.api as sm
from scipy import stats

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Defaults (formerly config.py of the Streamlit app)
# ----------------------------------------------------------------------
CONFIDENCE_LEVEL: float = 0.95
MIN_POINTS_PER_SEGMENT: int = 3

RegressionMethod = Literal["ols", "huber", "theilsen"]


@dataclass
class SegmentResult:
    """All fitted quantities for a single regression segment."""

    segment_index: int
    start: float
    end: float
    n: int
    slope: float
    intercept: float
    r_squared: float
    adj_r_squared: float
    rmse: float
    mae: float
    mse: float
    std_error: float
    ci_low: float
    ci_high: float
    t_statistic: float
    p_value: float
    residual_variance: float
    method: str
    t_values: np.ndarray = field(repr=False)
    y_values: np.ndarray = field(repr=False)
    y_predicted: np.ndarray = field(repr=False)
    residuals: np.ndarray = field(repr=False)

    @property
    def equation(self) -> str:
        """Human-readable regression equation, e.g. 'y = -0.43x + 812.3'."""
        sign = "+" if self.intercept >= 0 else "-"
        return f"y = {self.slope:.4g}x {sign} {abs(self.intercept):.4g}"

    def as_table_row(self) -> dict:
        """Flatten this result into a dict suitable for a stats table row."""
        def _r(v, nd):
            return None if not np.isfinite(v) else round(float(v), nd)

        return {
            "Segment": self.segment_index,
            "Start": round(self.start, 3),
            "End": round(self.end, 3),
            "N": self.n,
            "Slope": _r(self.slope, 6),
            "Intercept": _r(self.intercept, 6),
            "Equation": self.equation,
            "R2": _r(self.r_squared, 4),
            "Adj_R2": _r(self.adj_r_squared, 4),
            "RMSE": _r(self.rmse, 4),
            "MAE": _r(self.mae, 4),
            "MSE": _r(self.mse, 4),
            "Std_Error": _r(self.std_error, 6),
            "CI_Low_95": _r(self.ci_low, 6),
            "CI_High_95": _r(self.ci_high, 6),
            "t_statistic": _r(self.t_statistic, 4),
            "p_value": _r(self.p_value, 6),
            "Residual_Variance": _r(self.residual_variance, 6),
            "Method": self.method,
        }


def _fit_single_segment(
    t: np.ndarray,
    y: np.ndarray,
    segment_index: int,
    method: RegressionMethod = "ols",
    confidence: float = CONFIDENCE_LEVEL,
) -> SegmentResult:
    """Fit one segment and compute its full statistics suite."""
    n = len(t)
    if n < 2:
        raise ValueError(
            f"Segment {segment_index} has only {n} point(s); at least 2 "
            "are required to fit a line."
        )

    X = sm.add_constant(t)

    if method == "huber":
        model = sm.RLM(y, X, M=sm.robust.norms.HuberT())
        fit = model.fit()
        intercept, slope = fit.params
        y_pred = fit.predict(X)
        # RLM does not provide classical R^2; compute manually
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        se_slope = float(fit.bse[1])
        t_stat = float(fit.tvalues[1])
        p_val = float(fit.pvalues[1])
    elif method == "theilsen":
        slope, intercept, lo_slope, hi_slope = stats.theilslopes(
            y, t, alpha=1 - confidence
        )
        y_pred = intercept + slope * t
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        se_slope = (hi_slope - lo_slope) / (2 * stats.norm.ppf(0.5 + confidence / 2))
        t_stat = slope / se_slope if se_slope > 0 else np.nan
        # Approximate p-value via normal distribution of slope estimate
        p_val = 2 * (1 - stats.norm.cdf(abs(t_stat))) if np.isfinite(t_stat) else np.nan
    else:  # ordinary least squares
        model = sm.OLS(y, X)
        fit = model.fit()
        intercept, slope = fit.params
        y_pred = fit.predict(X)
        r_squared = float(fit.rsquared)
        se_slope = float(fit.bse[1])
        t_stat = float(fit.tvalues[1])
        p_val = float(fit.pvalues[1])

    residuals = y - y_pred
    dof = max(n - 2, 1)
    ss_res = float(np.sum(residuals ** 2))
    adj_r_squared = (
        1 - (1 - r_squared) * (n - 1) / dof if n > 2 and np.isfinite(r_squared) else np.nan
    )
    rmse = float(np.sqrt(ss_res / n))
    mae = float(np.mean(np.abs(residuals)))
    mse = float(ss_res / n)
    residual_variance = float(ss_res / dof)

    t_crit = stats.t.ppf(0.5 + confidence / 2, dof)
    ci_low = slope - t_crit * se_slope
    ci_high = slope + t_crit * se_slope

    return SegmentResult(
        segment_index=segment_index,
        start=float(t.min()),
        end=float(t.max()),
        n=n,
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r_squared) if np.isfinite(r_squared) else float("nan"),
        adj_r_squared=float(adj_r_squared) if np.isfinite(adj_r_squared) else float("nan"),
        rmse=rmse,
        mae=mae,
        mse=mse,
        std_error=float(se_slope),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        t_statistic=float(t_stat) if np.isfinite(t_stat) else float("nan"),
        p_value=float(p_val) if np.isfinite(p_val) else float("nan"),
        residual_variance=residual_variance,
        method=method,
        t_values=t,
        y_values=y,
        y_predicted=np.asarray(y_pred),
        residuals=residuals,
    )


def fit_piecewise_regression(
    t: np.ndarray,
    y: np.ndarray,
    breakpoints: Sequence[float],
    method: RegressionMethod = "ols",
    confidence: float = CONFIDENCE_LEVEL,
) -> List[SegmentResult]:
    """
    Split the (t, y) series at the given breakpoints and fit an
    independent regression to each resulting segment.

    Parameters
    ----------
    t, y : np.ndarray
        Cleaned, sorted numeric time and value arrays of equal length.
    breakpoints : Sequence[float]
        Sorted breakpoint values (already validated). May be empty, in
        which case a single regression spans the whole series.
    method : {"ols", "huber", "theilsen"}
        Regression method to apply to every segment.
    confidence : float
        Confidence level for slope confidence intervals (default 0.95).

    Returns
    -------
    List[SegmentResult]
        One result per segment, in chronological order.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)

    edges = [float(t.min())] + [float(b) for b in breakpoints] + [float(t.max())]
    results: List[SegmentResult] = []

    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == 0:
            mask = (t >= lo) & (t <= hi)
        else:
            mask = (t > lo) & (t <= hi)

        t_seg, y_seg = t[mask], y[mask]
        if len(t_seg) < MIN_POINTS_PER_SEGMENT:
            logger.warning(
                "Skipping segment %d [%.3f, %.3f]: only %d points",
                i + 1, lo, hi, len(t_seg)
            )
            continue

        result = _fit_single_segment(
            t_seg, y_seg, segment_index=i + 1, method=method, confidence=confidence
        )
        results.append(result)

    if not results:
        raise ValueError(
            "No valid segments could be fit. Check your breakpoints and "
            "ensure each segment has enough data points."
        )

    return results


def prediction_band(
    seg: SegmentResult, confidence: float = CONFIDENCE_LEVEL
) -> tuple[np.ndarray, np.ndarray]:
    """
    Pointwise (1-alpha) confidence band for the fitted MEAN response of a
    segment, evaluated at the segment's own time points:

        y_hat(t) +/- t_crit * s * sqrt(1/n + (t - t_bar)^2 / S_xx)

    where s^2 is the residual variance. Used purely for plotting.
    """
    t = seg.t_values.astype(float)
    n = seg.n
    dof = max(n - 2, 1)
    s = float(np.sqrt(seg.residual_variance))
    t_bar = float(np.mean(t))
    sxx = float(np.sum((t - t_bar) ** 2))
    if sxx <= 0:
        half = np.zeros_like(t)
    else:
        t_crit = stats.t.ppf(0.5 + confidence / 2, dof)
        half = t_crit * s * np.sqrt(1.0 / n + (t - t_bar) ** 2 / sxx)
    return seg.y_predicted - half, seg.y_predicted + half


# ----------------------------------------------------------------------
# Non-parametric trend diagnostics
# ----------------------------------------------------------------------
def mann_kendall_test(y: np.ndarray) -> dict:
    """
    Perform the Mann-Kendall trend test on a series (order matters;
    assumes values are already sorted by time).

    Returns a dict with the test statistic S, variance, Z-score,
    p-value, and a plain-language trend label.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    s = 0
    for k in range(n - 1):
        s += np.sum(np.sign(y[k + 1:] - y[k]))

    unique, counts = np.unique(y, return_counts=True)
    tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0

    if s > 0:
        z = (s - 1) / np.sqrt(var_s) if var_s > 0 else 0.0
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s) if var_s > 0 else 0.0
    else:
        z = 0.0

    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    trend = "increasing" if (z > 0 and p_value < 0.05) else (
        "decreasing" if (z < 0 and p_value < 0.05) else "no significant trend"
    )

    return {
        "S": int(s),
        "variance_S": float(var_s),
        "Z": float(z),
        "p_value": float(p_value),
        "trend": trend,
    }


def sens_slope(
    t: np.ndarray, y: np.ndarray, confidence: float = CONFIDENCE_LEVEL
) -> dict:
    """
    Compute Sen's slope estimator (median of all pairwise slopes) with
    a confidence interval, using SciPy's Theil-Sen implementation.
    """
    slope, intercept, lo, hi = stats.theilslopes(y, t, alpha=1 - confidence)
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "ci_low": float(lo),
        "ci_high": float(hi),
    }
