from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

# Stopwords mínimas — el vocabulario jurídico mexicano en español es denso y
# muchas "stopwords" estándar son señal aquí ("contra", "por", "que").
SPANISH_STOPWORDS_MIN = [
    "de",
    "la",
    "el",
    "y",
    "en",
    "a",
    "los",
    "las",
    "un",
    "una",
    "del",
    "al",
    "se",
    "por",
    "con",
    "para",
    "es",
    "su",
    "sus",
    "lo",
    "le",
    "este",
    "esta",
    "ese",
    "esa",
]


def build_pipeline() -> Pipeline:
    """TF-IDF (1-2 gramas) + LinearSVC calibrado para probabilidades."""
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.95,
                    sublinear_tf=True,
                    stop_words=SPANISH_STOPWORDS_MIN,
                ),
            ),
            (
                "clf",
                CalibratedClassifierCV(
                    estimator=LinearSVC(C=1.0, class_weight="balanced", dual="auto"),
                    method="sigmoid",
                    cv=3,
                ),
            ),
        ]
    )


# Etiquetas canónicas — el modelo internamente las codifica como índices,
# pero el resto del sistema usa estos strings.
LABELS = ("adjetivo", "sustantivo")
