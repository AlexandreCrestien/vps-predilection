import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
import mlflow.xgboost

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.class_weight import compute_sample_weight

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, f1_score, precision_score, recall_score,
)
from sklearn.impute import SimpleImputer

from imblearn.over_sampling import SMOTE
from imblearn.combine import SMOTEENN
from imblearn.pipeline import Pipeline as ImbPipeline

import xgboost as xgb


DATA_PATH   = '../data/df_stats.csv'   
EXPERIMENT  = "classification_politique"
GROUPS      = ["centre", "droite", "gauche"]
RANDOM_STATE = 42

def load_and_prepare(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", dtype={"Code_INSEE": str})

    drop_cols = [
        "Année", "Libellé de la commune", "Inscrits", "Abstentions",
        "% Abs/Ins", "Votants", "% Vot/Ins", "Blancs", "% Blancs/Ins",
        "% Blancs/Vot", "Nuls", "% Nuls/Ins", "% Nuls/Vot", "Exprimés",
        "% Exp/Ins", "% Exp/Vot", "% gauche/Exp", "% centre/Exp", "% droite/Exp",
    ]
    df = df.drop(columns=drop_cols)

    pop_active_cols = [
        "Hommes", "Femmes", "Agriculteurs", "Artisans", "Cadres",
        "Intermédiaires", "Employés", "Ouvriers", "Retraités", "Etudiants",
        "Inactifs", "15-24 ans", "25-39 ans", "40-54 ans", "55-64 ans",
        "65-79 ans", "80 ans et +", "Mariés", "Pacsés", "Concubinage",
        "Veufs", "Divorcés", "Célibataires",
    ]
    for col in pop_active_cols:
        df[col] = df[col] / df["Population_active"] * 100

    household_cols = [
        "Personne seule", "Homme seul", "Femme seule", "Colocation",
        "Famille", "Famille monoparentale", "Couple sans enfant",
        "Couple avec enfants",
    ]
    for col in household_cols:
        df[col] = df[col] / df["Population avec enfants"] * 100

    return df


def compute_metrics(y_true, y_pred, labels, prefix="test") -> dict:
    report = classification_report(y_true, y_pred, target_names=labels, output_dict=True)
    metrics = {
        f"{prefix}_accuracy": accuracy_score(y_true, y_pred),
        f"{prefix}_f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        f"{prefix}_f1_weighted": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        f"{prefix}_precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        f"{prefix}_recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
    }
    for label in labels:
        if label in report:
            metrics[f"{prefix}_f1_{label}"] = report[label]["f1-score"]
            metrics[f"{prefix}_recall_{label}"] = report[label]["recall"]
            metrics[f"{prefix}_precision_{label}"] = report[label]["precision"]
    return metrics


def overfit_gap(train_acc: float, test_acc: float) -> str:
    gap = abs(train_acc - test_acc)
    if gap > 0.10:
        return "overfitting"
    elif train_acc < 0.75:
        return "underfitting"
    return "good"


def run_experiment(
    run_name: str,
    pipeline,
    X_train, X_test, y_train, y_test,
    params: dict,
    labels: list,
    fit_kwargs: dict | None = None,
    model_flavor=mlflow.sklearn,
    label_names=None
):
    fit_kwargs = fit_kwargs or {}
    if label_names is None:
        label_names = [str(l) for l in labels]

    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(params)
        pipeline.fit(X_train, y_train, **fit_kwargs)

        y_pred_test  = pipeline.predict(X_test)
        y_pred_train = pipeline.predict(X_train)

        train_metrics = compute_metrics(y_train, y_pred_train, label_names, prefix="train")
        test_metrics  = compute_metrics(y_test,  y_pred_test,  label_names, prefix="test")
        all_metrics   = {**train_metrics, **test_metrics}
        all_metrics["overfit_status"] = overfit_gap(
            train_metrics["train_accuracy"], test_metrics["test_accuracy"]
        )
        mlflow.log_metrics({k: v for k, v in all_metrics.items() if isinstance(v, float)})
        mlflow.set_tag("overfit_status", all_metrics["overfit_status"])

        cm = confusion_matrix(y_test, y_pred_test, labels=labels)
        cm_df = pd.DataFrame(cm, index=[f"real_{g}" for g in labels],
                             columns=[f"pred_{g}" for g in labels])
        cm_path = f"/tmp/{run_name.replace(' ', '_')}_cm.csv"
        cm_df.to_csv(cm_path)
        mlflow.log_artifact(cm_path, artifact_path="confusion_matrices")

        report_str = classification_report(y_test, y_pred_test, target_names=label_names)
        report_path = f"/tmp/{run_name.replace(' ', '_')}_report.txt"
        with open(report_path, "w") as f:
            f.write(f"Run: {run_name}\n\n{report_str}")
        mlflow.log_artifact(report_path, artifact_path="classification_reports")

        model_flavor.log_model(pipeline, artifact_path="model")

        print(f"  ✓ {run_name:45s}  "
              f"train={train_metrics['train_accuracy']:.2%}  "
              f"test={test_metrics['test_accuracy']:.2%}  "
              f"f1_macro={test_metrics['test_f1_macro']:.3f}  "
              f"[{all_metrics['overfit_status']}]")

        return pipeline, test_metrics


def main():
    print("Loading data …")
    df = load_and_prepare(DATA_PATH)

    X = df.drop(columns=["Code_INSEE", "Résultat"])
    y = df["Résultat"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=RANDOM_STATE, stratify=y
    )

    le = LabelEncoder()
    y_train_xgb = le.fit_transform(y_train)
    y_test_xgb  = le.transform(y_test)
    xgb_labels  = list(le.classes_)       # ["centre", "droite", "gauche"]

    print(f"Train: {X_train.shape}  |  Test: {X_test.shape}")
    print(f"Class distribution (train):\n{y_train.value_counts()}\n")

    mlflow.set_experiment(EXPERIMENT)

    results = []

    print("\n Logistic Regression ")

    _, m = run_experiment(
        run_name="LR - Baseline",
        pipeline=Pipeline([
            ("imputer",    SimpleImputer(strategy="median")),
            ("scaler",     StandardScaler()),
            ("classifier", LogisticRegression(random_state=RANDOM_STATE)),
        ]),
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        params={"model": "LogisticRegression", "strategy": "baseline", "max_iter": 100},
        labels=GROUPS,
    )
    results.append({"run": "LR - Baseline", **m})

    _, m = run_experiment(
        run_name="LR - SMOTE",
        pipeline=ImbPipeline([
            ("imputer",    SimpleImputer(strategy="median")),
            ("scaler",     StandardScaler()),
            ("smote",      SMOTE(random_state=RANDOM_STATE, sampling_strategy="all")),
            ("classifier", LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)),
        ]),
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        params={"model": "LogisticRegression", "strategy": "SMOTE",
                "max_iter": 1000, "smote_strategy": "all"},
        labels=GROUPS,
    )
    results.append({"run": "LR - SMOTE", **m})

    _, m = run_experiment(
        run_name="LR - Balanced",
        pipeline=Pipeline([
            ("imputer",    SimpleImputer(strategy="median")),
            ("scaler",     StandardScaler()),
            ("classifier", LogisticRegression(random_state=RANDOM_STATE,
                                              class_weight="balanced")),
        ]),
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        params={"model": "LogisticRegression", "strategy": "class_weight_balanced"},
        labels=GROUPS,
    )
    results.append({"run": "LR - Balanced", **m})

    print("\n Random Forest ")

    RF_PARAMS = dict(
        n_estimators=200, random_state=RANDOM_STATE, max_depth=10,
        min_samples_leaf=5, max_features="sqrt", min_samples_split=15,
    )

    _, m = run_experiment(
        run_name="RF - Baseline",
        pipeline=Pipeline([
            ("imputer",    SimpleImputer(strategy="median")),
            ("scaler",     StandardScaler()),
            ("classifier", RandomForestClassifier(**RF_PARAMS)),
        ]),
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        params={"model": "RandomForest", "strategy": "baseline", **RF_PARAMS},
        labels=GROUPS,
    )
    results.append({"run": "RF - Baseline", **m})

    _, m = run_experiment(
        run_name="RF - SMOTE",
        pipeline=ImbPipeline([
            ("imputer",    SimpleImputer(strategy="median")),
            ("scaler",     StandardScaler()),
            ("smote",      SMOTE(random_state=RANDOM_STATE, sampling_strategy="all")),
            ("classifier", RandomForestClassifier(**RF_PARAMS)),
        ]),
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        params={"model": "RandomForest", "strategy": "SMOTE",
                "smote_strategy": "all", **RF_PARAMS},
        labels=GROUPS,
    )
    results.append({"run": "RF - SMOTE", **m})

    RF_PARAMS_W = {**RF_PARAMS, "class_weight": "balanced"}
    _, m = run_experiment(
        run_name="RF - Balanced",
        pipeline=Pipeline([
            ("imputer",    SimpleImputer(strategy="median")),
            ("scaler",     StandardScaler()),
            ("classifier", RandomForestClassifier(**RF_PARAMS_W)),
        ]),
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        params={"model": "RandomForest", "strategy": "class_weight_balanced", **RF_PARAMS_W},
        labels=GROUPS,
    )
    results.append({"run": "RF - Balanced", **m})

    print("\n XGBoost ")

    XGB_PARAMS = dict(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.0,
        random_state=RANDOM_STATE, n_jobs=-1,
        objective="multi:softprob", eval_metric="mlogloss",
    )

    _, m = run_experiment(
        run_name="XGB - SMOTE",
        pipeline=ImbPipeline([
            ("imputer",    SimpleImputer(strategy="median")),
            ("scaler",     StandardScaler()),
            ("smote",      SMOTE(random_state=RANDOM_STATE, sampling_strategy="all")),
            ("classifier", xgb.XGBClassifier(**XGB_PARAMS)),
        ]),
        X_train=X_train, X_test=X_test,
        y_train=y_train_xgb, y_test=y_test_xgb,
        params={"model": "XGBoost", "strategy": "SMOTE",
                "smote_strategy": "all", **XGB_PARAMS},
        labels=list(range(len(xgb_labels))),
        label_names=xgb_labels,
        model_flavor=mlflow.sklearn,
    )
    results.append({"run": "XGB - SMOTE", **m})

    _, m = run_experiment(
        run_name="XGB - SMOTEENN",
        pipeline=ImbPipeline([
            ("imputer",    SimpleImputer(strategy="median")),
            ("scaler",     StandardScaler()),
            ("smote",      SMOTEENN(
                random_state=RANDOM_STATE,
                smote=SMOTE(sampling_strategy={0: 10000, 2: 8000},
                            random_state=RANDOM_STATE),
            )),
            ("classifier", xgb.XGBClassifier(**XGB_PARAMS)),
        ]),
        X_train=X_train, X_test=X_test,
        y_train=y_train_xgb, y_test=y_test_xgb,
        params={"model": "XGBoost", "strategy": "SMOTEENN",
                "smoteenn_centre": 10000, "smoteenn_gauche": 8000, **XGB_PARAMS},
        labels=list(range(len(xgb_labels))),
        label_names=xgb_labels,
        model_flavor=mlflow.sklearn,
    )
    results.append({"run": "XGB - SMOTEENN", **m})

    xgb_pipeline_w = ImbPipeline([
        ("imputer",    SimpleImputer(strategy="median")),
        ("scaler",     StandardScaler()),
        ("classifier", xgb.XGBClassifier(**XGB_PARAMS)),
    ])
    sample_weights = compute_sample_weight(class_weight="balanced", y=y_train_xgb)

    _, m = run_experiment(
        run_name="XGB - Balanced",
        pipeline=xgb_pipeline_w,
        X_train=X_train, X_test=X_test,
        y_train=y_train_xgb, y_test=y_test_xgb,
        params={"model": "XGBoost", "strategy": "sample_weight_balanced", **XGB_PARAMS},
        labels=list(range(len(xgb_labels))),
        label_names=xgb_labels,
        fit_kwargs={"classifier__sample_weight": sample_weights},
        model_flavor=mlflow.sklearn,
    )
    results.append({"run": "XGB - Balanced", **m})

    print("\nSummary (sorted by test F1 macro) ")
    summary = (
        pd.DataFrame(results)
        .sort_values("test_f1_macro", ascending=False)
        [["run", "test_accuracy", "test_f1_macro", "test_f1_weighted",
          "test_recall_macro", "test_precision_macro"]]
    )
    pd.set_option("display.float_format", "{:.4f}".format)
    print(summary.to_string(index=False))

    best = summary.iloc[0]
    print(f"\n Best run: {best['run']}  —  F1 macro: {best['test_f1_macro']:.4f}")
    print("\nRun `mlflow ui` then open http://localhost:5000 to explore results.")


if __name__ == "__main__":
    main()