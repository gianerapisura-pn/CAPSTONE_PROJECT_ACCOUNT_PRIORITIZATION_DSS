"""Frozen CatBoost wrapper required by the authorized serialized artifact."""

import numpy as np
from catboost import CatBoostClassifier
from sklearn.impute import SimpleImputer


class FrozenCatBoost:
    def __init__(self, **params):
        self.params = params

    def fit(self, features, target):
        self.imputer = SimpleImputer(strategy="median")
        transformed = self.imputer.fit_transform(features)
        self.model = CatBoostClassifier(**self.params)
        self.model.fit(transformed, target)
        self.named_steps = {"imputer": self.imputer, "model": self.model}
        return self

    def predict(self, features):
        return np.asarray(
            self.model.predict(self.imputer.transform(features)), dtype=int
        ).ravel()

    def predict_proba(self, features):
        return self.model.predict_proba(self.imputer.transform(features))
