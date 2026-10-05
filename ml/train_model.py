from pathlib import Path
import sys
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.predictor import clean_text

DATA = ROOT / 'data' / 'tickets.csv'
MODELS = ROOT / 'models'


def main():
    df = pd.read_csv(DATA).dropna(subset=['title', 'description', 'category'])
    df['text'] = (df['title'] + ' ' + df['description']).map(clean_text)
    x_train, x_test, y_train, y_test = train_test_split(df['text'], df['category'], test_size=0.2, random_state=42, stratify=df['category'])
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    train_vectors = vectorizer.fit_transform(x_train)
    test_vectors = vectorizer.transform(x_test)
    model = LogisticRegression(max_iter=1200, class_weight='balanced', random_state=42)
    model.fit(train_vectors, y_train)
    predictions = model.predict(test_vectors)
    print(f'Accuracy: {accuracy_score(y_test, predictions):.2%}')
    print(classification_report(y_test, predictions, zero_division=0))
    MODELS.mkdir(exist_ok=True)
    joblib.dump(model, MODELS / 'ticket_classifier.pkl')
    joblib.dump(vectorizer, MODELS / 'tfidf_vectorizer.pkl')
    print(f'Saved trained model artifacts to {MODELS}')


if __name__ == '__main__':
    main()
