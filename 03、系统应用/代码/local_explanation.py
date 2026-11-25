"""Compute a selected session's contributions from the actual regression bundle."""
import numpy as np
import pandas as pd
from models.revised import raw_features


def explain_session(bundle, query, expected_prediction):
    if len(query) != 1 or not query.session_id.is_unique:
        raise ValueError('Exactly one current session is required')
    reference = bundle['reference']
    query = query.copy()
    query['date'] = pd.to_datetime(query.date, errors='coerce')
    if query.date.isna().any() or query.date.iloc[0] <= pd.to_datetime(reference.date).max():
        raise ValueError('Explanation must be after the fitting cutoff')
    x = raw_features(reference, query, bundle['use_history']).fillna(bundle['median'])
    if list(x.columns) != bundle['features'] or not np.isfinite(x.to_numpy()).all():
        raise ValueError('Invalid explanation features')
    model = bundle['model']
    contributions = np.asarray(model.predict(x, pred_contrib=True), dtype=float)
    prediction = float(np.asarray(model.predict(x)).reshape(-1)[0])
    if contributions.shape != (1, len(x.columns) + 1) or not np.isfinite(contributions).all():
        raise ValueError('Invalid contribution output')
    baseline = float(contributions[0, -1])
    reconstructed = float(contributions.sum())
    displayed = max(0.0, prediction)
    if not np.isclose(reconstructed, prediction, atol=1e-7, rtol=0):
        raise ValueError('Contributions do not reconstruct the prediction')
    if not np.isfinite(expected_prediction) or not np.isclose(displayed, expected_prediction, atol=1e-7, rtol=0):
        raise ValueError('Explanation does not match the displayed prediction')
    table = pd.DataFrame({'feature': x.columns, 'value': x.iloc[0].to_numpy(),
                          'contribution_pp': contributions[0, :-1] * 100})
    table = table.iloc[np.argsort(-np.abs(table.contribution_pp.to_numpy()), kind='stable')].reset_index(drop=True)
    return {'session_id': query.session_id.iloc[0], 'baseline': baseline,
            'raw_prediction': prediction, 'prediction': displayed, 'table': table}
