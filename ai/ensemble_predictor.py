import os, json, pickle, torch, numpy as np
from transformers import AutoTokenizer
from typing import List, Dict
from train import (             
    ImprovedEnhancedBertClassifier,
    AdaptiveBertClassifier,
    BertClassifier,
    EnhancedBertClassifier,
)

class EnsemblePredictor:
    def __init__(self, model_dir: str, device: str | None = None):
        self.model_dir = model_dir
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        with open(os.path.join(model_dir, "model_configs.json"), "r", encoding="utf-8") as f:
            self.model_cfgs: List[Dict] = json.load(f)

        with open(os.path.join(model_dir, "label_encoder.pkl"), "rb") as f:
            self.label_encoder = pickle.load(f)
            
        self.models, self.tokenizers = [], []
        for idx, cfg in enumerate(self.model_cfgs):
            model = self._init_model(cfg)
            state_dict_path = os.path.join(model_dir, f"model_{idx}.pt")
            model.load_state_dict(torch.load(state_dict_path, map_location=self.device))
            model.eval().to(self.device)
            self.models.append(model)

            tok_path = os.path.join(model_dir, f"tokenizer_{idx}")
            self.tokenizers.append(AutoTokenizer.from_pretrained(tok_path))

    def _init_model(self, cfg: Dict):
        t = cfg.get("type", "basic")
        if t == "improved_simple":
            return ImprovedEnhancedBertClassifier(cfg["model_name"], len(self.label_encoder.classes_), classifier_type="simple")
        if t == "improved_moderate":
            return ImprovedEnhancedBertClassifier(cfg["model_name"], len(self.label_encoder.classes_), classifier_type="moderate")
        if t == "improved_complex":
            return ImprovedEnhancedBertClassifier(cfg["model_name"], len(self.label_encoder.classes_), classifier_type="complex")
        if t == "adaptive":
            return AdaptiveBertClassifier(cfg["model_name"], len(self.label_encoder.classes_), dataset_size=cfg.get("dataset_size", 0))
        if t == "enhanced":
            return EnhancedBertClassifier(cfg["model_name"], len(self.label_encoder.classes_))
        return BertClassifier(cfg["model_name"], len(self.label_encoder.classes_))

    @torch.inference_mode()
    def _predict_single(self, text: str, model, tokenizer):
        encoded = tokenizer(text, truncation=True, padding="max_length",
                            max_length=512, return_tensors="pt")
        logits = model(encoded["input_ids"].to(self.device),
                       encoded["attention_mask"].to(self.device))
        probs = torch.softmax(logits, dim=1)
        pred_cls = probs.argmax(dim=1).item()
        conf = probs.max(dim=1).values.item()
        return pred_cls, conf

    def predict(self, text: str) -> Dict:
        preds, confs = [], []
        for m, tok in zip(self.models, self.tokenizers):
            p, c = self._predict_single(text, m, tok)
            preds.append(p); confs.append(c)

        score = {}
        for p, c in zip(preds, confs):
            score[p] = score.get(p, 0) + c
        final_cls = max(score, key=score.get)

        return {
            "keyword": self.label_encoder.inverse_transform([final_cls])[0],
            "confidence": float(np.mean(confs)),
            "individual": [
                {
                    "model": cfg["name"],
                    "prediction": self.label_encoder.inverse_transform([p])[0],
                    "conf": float(c)
                }
                for cfg, p, c in zip(self.model_cfgs, preds, confs)
            ]
        }
