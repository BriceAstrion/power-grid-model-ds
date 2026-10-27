"""POC-03: Plotly comparison of synthetic voltage series and illustrative sigma bands.

The band centre (estimated voltage) is a TEST ASSUMPTION, not a validated
state-estimation uncertainty definition. No validity decision is inferred.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import plotly.graph_objects as go


def example_fixture() -> dict[str, np.ndarray]:
    """Synthetic aligned time series; no state-estimation calculation is performed."""
    return {
        "time": np.array(["2026-01-01T10:00:00", "2026-01-01T10:05:00",
                          "2026-01-01T10:10:00", "2026-01-01T10:15:00",
                          "2026-01-01T10:20:00"], dtype="datetime64[s]"),
        "measured": np.array([230.0, 231.1, 229.8, 230.7, 231.2]),
        "estimated": np.array([229.8, 230.8, 230.0, 230.4, 230.9]),
        "sigma": np.array([0.5, 0.6, 0.5, 0.7, 0.6]),
    }


def prepare_band(time, measured, estimated, sigma, multiplier: float) -> dict:
    """Validate aligned inputs and calculate an illustrative estimate-centred band.

    Missing measured/estimated values are allowed as NaN and remain missing.
    A finite sigma is required where an estimate exists; sigma must be >= 0.
    """
    t = np.asarray(time)
    m = np.asarray(measured, dtype=float)
    e = np.asarray(estimated, dtype=float)
    s = np.asarray(sigma, dtype=float)

    if any(a.ndim != 1 for a in (t, m, e, s)):
        raise ValueError("Time and voltage series must be one-dimensional")
    if not (len(t) == len(m) == len(e) == len(s)) or len(t) == 0:
        raise ValueError("Time, measured, estimated and sigma must have equal nonzero lengths")
    if not np.issubdtype(t.dtype, np.datetime64):
        raise ValueError("Time must contain datetime64 timestamps")
    if np.isnat(t).any() or np.any(t[1:] <= t[:-1]):
        raise ValueError("Timestamps must be present, strictly increasing and unique")
    if not np.isfinite(multiplier) or multiplier < 0:
        raise ValueError("Sigma multiplier must be finite and non-negative")
    if np.isinf(m).any() or np.isinf(e).any():
        raise ValueError("Voltage series may contain NaN but not infinity")
    if np.isinf(s).any() or np.any(s[np.isfinite(s)] < 0):
        raise ValueError("Sigma must not be infinite or negative")
    if np.any(np.isfinite(e) & ~np.isfinite(s)):
        raise ValueError("Sigma must be finite wherever an estimate is available")

    # An estimate-centred interval is used only to test the rendering mechanism.
    lower = e - multiplier * s
    upper = e + multiplier * s
    # If the estimate is missing, both band boundaries remain missing.
    lower[~np.isfinite(e)] = np.nan
    upper[~np.isfinite(e)] = np.nan
    return {
        "time": t.copy(), "measured": m.copy(), "estimated": e.copy(),
        "sigma": s.copy(), "lower": lower, "upper": upper,
        "multiplier": float(multiplier),
    }


def build_figure(band: dict) -> go.Figure:
    """Render lower/upper boundaries and measured/estimated voltage traces."""
    x = band["time"].astype("datetime64[ms]").astype(str).tolist()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=band["lower"], mode="lines", name="Lower band",
        line={"width": 0}, hoverinfo="skip", connectgaps=False,
    ))
    fig.add_trace(go.Scatter(
        x=x, y=band["upper"], mode="lines", name="Sigma band",
        fill="tonexty", fillcolor="rgba(100,140,220,0.20)",
        line={"width": 0}, connectgaps=False,
        hovertemplate="Upper band: %{y:.3f} V<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=band["measured"], mode="lines+markers", name="Measured",
        connectgaps=False, hovertemplate="Measured: %{y:.3f} V<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=band["estimated"], mode="lines+markers", name="Estimated",
        connectgaps=False, hovertemplate="Estimated: %{y:.3f} V<extra></extra>",
    ))
    fig.update_layout(
        title=f"POC-03: Synthetic voltage comparison (illustrative ±{band['multiplier']:g}σ)",
        xaxis_title="Timestamp", yaxis_title="Voltage magnitude (V)",
        template="plotly_white", hovermode="x unified",
        annotations=[{
            "x": 0.5, "y": -0.25, "xref": "paper", "yref": "paper", "showarrow": False,
            "text": "Band centred on estimate for this technical test only; sigma semantics not validated.",
            "font": {"size": 11},
        }],
        margin={"b": 100},
    )
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="POC-03 Plotly sigma-band prototype")
    parser.add_argument("--multiplier", type=float, default=2.0)
    parser.add_argument("--output", type=Path, default=Path("experiments/poc03_sigma_bands.html"))
    args = parser.parse_args()
    band = prepare_band(**example_fixture(), multiplier=args.multiplier)
    fig = build_figure(band)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(args.output), include_plotlyjs=True, full_html=True)
    print(f"POC-03: HTML chart written to {args.output.resolve()}")
    print(f"POC-03: {len(band['time'])} aligned synthetic timestamps; multiplier={args.multiplier:g}")
    for i in range(len(band["time"])):
        print(f"  {str(band['time'][i])}: measured={band['measured'][i]:.3f}, "
              f"estimated={band['estimated'][i]:.3f}, "
              f"lower={band['lower'][i]:.3f}, upper={band['upper'][i]:.3f}")
    print("NOTE: Band centre and sigma values are synthetic test assumptions.")


if __name__ == "__main__":
    main()
