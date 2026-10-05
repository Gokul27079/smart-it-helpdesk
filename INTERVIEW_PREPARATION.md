# Interview Preparation

## 60-second explanation

Smart IT Help Desk is a Flask web application for employee IT support. A user submits a title, description, identity, and department. The backend combines the text, cleans it, converts it to TF-IDF features, and uses a trained Logistic Regression classifier to predict one of eight IT categories. It also calculates a confidence score, applies transparent priority rules for urgent language, and maps the category to a support team. Results are persisted in SQLite with a status workflow and audit log. The dashboard is database-driven and exposes REST APIs, making the system practical to extend.

## Core questions

1. **What problem does it solve?** It reduces manual triage time and makes routing consistent.
2. **Why TF-IDF?** It is interpretable, efficient for short support text, and a strong baseline for sparse text classification.
3. **Why Logistic Regression?** It is fast, handles sparse features well, supports `predict_proba`, and is easier to explain than a deep model.
4. **How does classification work?** Title and description are cleaned, vectorized, and passed to the trained model; the highest probability class is returned.
5. **How is confidence calculated?** The model's maximum class probability is shown as a percentage; below 60% triggers manual review.
6. **How is priority detected?** Normalized text is checked against ordered Critical, High, Medium, and Low phrase rules. Critical rules win.
7. **Why SQLite?** It is zero-configuration, portable, and sufficient for a local/intermediate project.
8. **How is Flask organized?** Routes handle HTTP, the database class handles persistence, services hold business rules, and ML modules handle training/prediction.
9. **How are APIs useful?** A future portal, mobile app, or automation can reuse classification and ticket operations.
10. **What is the database design?** Tickets store the current state; ticket_logs preserve status history with a foreign key.
11. **How do you handle missing model artifacts?** The UI/API reports a clear setup error and instructs the operator to run the training script rather than returning a fake result.
12. **How do you handle invalid input?** Required fields, email syntax, minimum lengths, attachment extensions, invalid IDs, and invalid statuses are validated with friendly errors.
13. **What is a limitation?** The starter dataset is small and supervised; production would need real labeled tickets, drift monitoring, and human feedback.
14. **How would you improve accuracy?** Add more balanced labeled data, tune n-grams/regularization with cross-validation, and compare linear SVM or transformer embeddings.
15. **How would you deploy it?** Use Gunicorn behind a reverse proxy, PostgreSQL, object storage for attachments, secret environment variables, authentication, logging, and monitoring.

## Challenges and future improvements

The main trade-off is balancing explainability with predictive power. The system keeps the classifier simple and supplements it with visible rules. Future versions can add feedback-driven retraining, SLA timers, authentication, notifications, semantic embeddings, and production-grade persistence.
