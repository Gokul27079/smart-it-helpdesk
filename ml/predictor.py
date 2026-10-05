import re
from pathlib import Path
import joblib

CATEGORIES = ['Hardware', 'Software', 'Network', 'Access & Account', 'Security', 'Email', 'Database', 'Other']


def clean_text(text):
    text = str(text or '').lower()
    text = re.sub(r'[^a-z0-9& ]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


class TicketPredictor:
    def __init__(self, model_dir):
        self.model_dir = Path(model_dir)
        self.model = None
        self.vectorizer = None
        self.load_error = None
        try:
            self.model = joblib.load(self.model_dir / 'ticket_classifier.pkl')
            self.vectorizer = joblib.load(self.model_dir / 'tfidf_vectorizer.pkl')
        except Exception as exc:
            self.load_error = str(exc)

    @property
    def available(self):
        return self.model is not None and self.vectorizer is not None

    def predict(self, title, description):
        if not self.available:
            raise RuntimeError('The trained AI model is unavailable. Run python ml/train_model.py.')
        text = clean_text(f'{title} {description}')
        vector = self.vectorizer.transform([text])
        probabilities = self.model.predict_proba(vector)[0]
        index = probabilities.argmax()
        category = self.model.classes_[index]
        confidence = float(probabilities[index])
        top_terms = []
        feature_names = self.vectorizer.get_feature_names_out()
        for idx in vector.toarray()[0].argsort()[::-1]:
            if vector.toarray()[0][idx] > 0:
                top_terms.append(feature_names[idx])
            if len(top_terms) == 5:
                break
        return {'category': category, 'confidence': confidence, 'keywords': top_terms,
                'explanation': f"TF-IDF + Logistic Regression identified language associated with {category}."}
