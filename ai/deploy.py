from flask import Flask, request, jsonify
from ensemble_predictor import EnsemblePredictor

app = Flask(__name__)
predictor = EnsemblePredictor("./improved_models") #path

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True)
    if "question" not in data:
        return jsonify({"error": "JSON 需包含 'question' 欄位"}), 400
    result = predictor.predict(data["question"])
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
