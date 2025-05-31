import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from transformers import (
    BertTokenizer, BertModel, BertForSequenceClassification,
    AutoTokenizer, AutoModel, AutoConfig, get_linear_schedule_with_warmup
)
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
from sklearn.ensemble import VotingClassifier
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional
import warnings
import os
import pickle
warnings.filterwarnings('ignore')


class KeywordDataset(Dataset):
    """
    關鍵詞預測資料集類別
    高效處理文本資料並進行tokenization
    """
    def __init__(self, questions: List[str], keywords: List[str], 
                 tokenizer, max_length: int = 512):
        self.questions = questions
        self.keywords = keywords
        self.tokenizer = tokenizer
        self.max_length = max_length
        
    def __len__(self) -> int:
        return len(self.questions)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        question = str(self.questions[idx])
        keyword = self.keywords[idx]
        
        # 使用tokenizer進行編碼
        encoding = self.tokenizer(
            question,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(keyword, dtype=torch.long)
        }


class BertClassifier(nn.Module):
    """
    BERT分類器基礎模型
    支援多種BERT架構的微調
    """
    def __init__(self, model_name: str, num_classes: int, dropout_rate: float = 0.3):
        super(BertClassifier, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_classes)
        
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output
        output = self.dropout(pooled_output)
        return self.classifier(output)


class EnhancedBertClassifier(nn.Module):
    """
    增強版BERT分類器
    添加額外的全連接層和注意力機制
    """
    def __init__(self, model_name: str, num_classes: int, dropout_rate: float = 0.3):
        super(EnhancedBertClassifier, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size
        
        # 多層分類頭
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_size // 2, hidden_size // 4),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_size // 4, num_classes)
        )
        
        # 自注意力層
        self.attention = nn.MultiheadAttention(hidden_size, num_heads=8, batch_first=True)
        
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        
        # 使用所有隱藏狀態而不只是pooler_output
        sequence_output = outputs.last_hidden_state
        
        # 應用自注意力
        attended_output, _ = self.attention(sequence_output, sequence_output, sequence_output)
        
        # 全域平均池化
        pooled_output = torch.mean(attended_output, dim=1)
        
        return self.classifier(pooled_output)


class ImprovedEnhancedBertClassifier(nn.Module):
    """
    改進版增強BERT分類器
    針對準確率低的問題進行多方面優化
    """
    def __init__(self, model_name: str, num_classes: int, 
                 dropout_rate: float = 0.2, classifier_type: str = 'simple'):
        super(ImprovedEnhancedBertClassifier, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size
        self.classifier_type = classifier_type
        
        # 凍結BERT前幾層參數，避免過度擬合
        self._freeze_bert_layers(freeze_layers=6)
        
        # 根據分類器類型選擇不同的結構
        if classifier_type == 'simple':
            # 簡化分類頭，減少過擬合風險
            self.classifier = nn.Sequential(
                nn.Dropout(dropout_rate),
                nn.Linear(hidden_size, num_classes)
            )
        elif classifier_type == 'moderate':
            # 中等複雜度分類頭
            self.classifier = nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.LayerNorm(hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(dropout_rate),
                nn.Linear(hidden_size // 2, num_classes)
            )
        else:  # 'complex'
            # 複雜分類頭（原版本的改進）
            self.classifier = nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.LayerNorm(hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(dropout_rate),
                nn.Linear(hidden_size // 2, hidden_size // 4),
                nn.LayerNorm(hidden_size // 4),
                nn.ReLU(),
                nn.Dropout(dropout_rate / 2),  # 較低的dropout
                nn.Linear(hidden_size // 4, num_classes)
            )
        
        # 改進的注意力機制（可選）
        self.use_attention = classifier_type != 'simple'
        if self.use_attention:
            self.attention = nn.MultiheadAttention(
                hidden_size, num_heads=4, dropout=dropout_rate, batch_first=True
            )
            # 注意力權重歸一化
            self.attention_norm = nn.LayerNorm(hidden_size)
        
        # 池化策略選擇
        self.pooling_strategy = 'cls_with_attention' if self.use_attention else 'cls'
        
    def _freeze_bert_layers(self, freeze_layers: int):
        """凍結BERT前幾層參數"""
        if freeze_layers > 0:
            for param in self.bert.embeddings.parameters():
                param.requires_grad = False
            
            for i in range(min(freeze_layers, len(self.bert.encoder.layer))):
                for param in self.bert.encoder.layer[i].parameters():
                    param.requires_grad = False
    
    def _pool_sequence_output(self, sequence_output: torch.Tensor, 
                             attention_mask: torch.Tensor) -> torch.Tensor:
        """多種池化策略"""
        if self.pooling_strategy == 'cls':
            return sequence_output[:, 0, :]  # CLS token
        
        elif self.pooling_strategy == 'mean':
            # 遮罩平均池化
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(sequence_output.size()).float()
            sum_embeddings = torch.sum(sequence_output * input_mask_expanded, 1)
            sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            return sum_embeddings / sum_mask
        
        elif self.pooling_strategy == 'max':
            # 最大池化
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(sequence_output.size()).float()
            sequence_output[input_mask_expanded == 0] = -1e9
            return torch.max(sequence_output, 1)[0]
        
        elif self.pooling_strategy == 'cls_with_attention':
            # CLS + 注意力加權
            cls_output = sequence_output[:, 0, :]
            if self.use_attention:
                attended_output, attention_weights = self.attention(
                    sequence_output, sequence_output, sequence_output,
                    key_padding_mask=~attention_mask.bool()
                )
                attended_output = self.attention_norm(attended_output + sequence_output)
                # 使用注意力權重對序列進行加權平均
                weighted_output = torch.sum(attended_output * attention_weights.mean(1).unsqueeze(-1), dim=1)
                return (cls_output + weighted_output) / 2
            else:
                return cls_output
        
        else:
            return sequence_output[:, 0, :]  # 預設使用CLS
    
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state
        
        # 使用選定的池化策略
        pooled_output = self._pool_sequence_output(sequence_output, attention_mask)
        
        return self.classifier(pooled_output)


class AdaptiveBertClassifier(nn.Module):
    """
    自適應BERT分類器
    根據資料集大小和複雜度自動調整結構
    """
    def __init__(self, model_name: str, num_classes: int, 
                 dataset_size: int, dropout_rate: float = 0.2):
        super(AdaptiveBertClassifier, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size
        
        # 根據資料集大小決定模型複雜度
        if dataset_size < 1000:
            # 小資料集：使用簡單結構
            freeze_layers = 8
            classifier_hidden = hidden_size // 4
            use_attention = False
        elif dataset_size < 5000:
            # 中等資料集：中等複雜度
            freeze_layers = 4
            classifier_hidden = hidden_size // 2
            use_attention = True
        else:
            # 大資料集：完整結構
            freeze_layers = 0
            classifier_hidden = hidden_size
            use_attention = True
        
        # 凍結部分層
        self._freeze_bert_layers(freeze_layers)
        
        # 建構分類器
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, classifier_hidden),
            nn.LayerNorm(classifier_hidden),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(classifier_hidden, num_classes)
        )
        
        # 條件性注意力
        self.use_attention = use_attention
        if use_attention:
            self.attention = nn.MultiheadAttention(
                hidden_size, num_heads=4, dropout=dropout_rate, batch_first=True
            )
    
    def _freeze_bert_layers(self, freeze_layers: int):
        """凍結BERT層"""
        if freeze_layers > 0:
            for param in self.bert.embeddings.parameters():
                param.requires_grad = False
            
            for i in range(min(freeze_layers, len(self.bert.encoder.layer))):
                for param in self.bert.encoder.layer[i].parameters():
                    param.requires_grad = False
    
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        
        if self.use_attention:
            sequence_output = outputs.last_hidden_state
            attended_output, _ = self.attention(sequence_output, sequence_output, sequence_output)
            pooled_output = torch.mean(attended_output, dim=1)
        else:
            pooled_output = outputs.pooler_output if hasattr(outputs, 'pooler_output') and outputs.pooler_output is not None else outputs.last_hidden_state[:, 0, :]
        
        return self.classifier(pooled_output)


class ImprovedTrainingStrategy:
    """
    改進的訓練策略類別
    """
    @staticmethod
    def get_optimizer_and_scheduler(model, train_loader, epochs: int, base_lr: float = 2e-5):
        """
        獲取優化器和學習率調度器
        """
        # 分層學習率：BERT層使用較小學習率，分類層使用較大學習率
        bert_params = []
        classifier_params = []
        
        for name, param in model.named_parameters():
            if 'bert' in name:
                bert_params.append(param)
            else:
                classifier_params.append(param)
        
        optimizer = AdamW([
            {'params': bert_params, 'lr': base_lr * 0.1},  # BERT層用較小學習率
            {'params': classifier_params, 'lr': base_lr}    # 分類層用標準學習率
        ], weight_decay=0.01)
        
        total_steps = len(train_loader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer, 
            num_warmup_steps=int(0.1 * total_steps),  # 10% warmup
            num_training_steps=total_steps
        )
        
        return optimizer, scheduler
    
    @staticmethod
    def early_stopping_check(val_accuracies: List[float], patience: int = 3) -> bool:
        """
        早停機制檢查
        """
        if len(val_accuracies) < patience + 1:
            return False
        
        recent_accuracies = val_accuracies[-patience:]
        best_recent = max(recent_accuracies)
        current = val_accuracies[-1]
        
        return current < best_recent and all(
            val_accuracies[-patience-1] >= acc for acc in recent_accuracies
        )


def get_improved_model_configs(dataset_size: int) -> List[Dict]:
    """
    根據資料集大小推薦模型配置
    """
    if dataset_size < 1000:
        # 小資料集配置
        return [
            {
                'name': 'BERT-Base-Chinese-Simple',
                'model_name': 'bert-base-chinese',
                'type': 'improved_simple',
                'learning_rate': 5e-5,  # 較高學習率
                'dropout_rate': 0.1,    # 較低dropout
                'classifier_type': 'simple'
            },
            {
                'name': 'BERT-Base-Chinese-Adaptive',
                'model_name': 'bert-base-chinese',
                'type': 'adaptive',
                'learning_rate': 3e-5,
                'dropout_rate': 0.2,
                'dataset_size': dataset_size
            }
        ]
    else:
        # 大資料集配置
        return [
            {
                'name': 'BERT-Base-Chinese-Moderate',
                'model_name': 'bert-base-chinese',
                'type': 'improved_moderate',
                'learning_rate': 2e-5,
                'dropout_rate': 0.2,
                'classifier_type': 'moderate'
            },
            {
                'name': 'BERT-Base-Chinese-Enhanced-v2',
                'model_name': 'bert-base-chinese',
                'type': 'improved_complex',
                'learning_rate': 1e-5,  # 較低學習率
                'dropout_rate': 0.3,
                'classifier_type': 'complex'
            },
            {
                'name': 'RoBERTa-Chinese-Improved',
                'model_name': 'hfl/chinese-roberta-wwm-ext',
                'type': 'improved_moderate',
                'learning_rate': 1.5e-5,
                'dropout_rate': 0.25,
                'classifier_type': 'moderate'
            }
        ]


class ImprovedEnsembleKeywordPredictor:
    """
    改進版集成學習關鍵詞預測器
    針對模型準確率低的問題進行全面優化
    """
    def __init__(self, model_configs: List[Dict], device: str = 'cuda'):
        self.device = device if torch.cuda.is_available() else 'cpu'
        self.model_configs = model_configs
        self.models = []
        self.tokenizers = []
        self.label_encoder = LabelEncoder()
        self.num_classes = 0
        self.dataset_size = 0
        self.class_weights = None
        
    def load_data(self, json_file_path: str) -> Tuple[List[str], List[str]]:
        """載入JSON格式的資料集"""
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = [item['question'] for item in data]
        keywords = [item['answer'] for item in data]
        self.dataset_size = len(questions)
        
        return questions, keywords
    
    def preprocess_data(self, questions: List[str], keywords: List[str]) -> Tuple[List[str], np.ndarray]:
        """資料預處理和標籤編碼"""
        # 編碼關鍵詞標籤
        encoded_keywords = self.label_encoder.fit_transform(keywords)
        self.num_classes = len(self.label_encoder.classes_)
        
        # 分析類別分佈
        unique, counts = np.unique(encoded_keywords, return_counts=True)
        class_distribution = dict(zip(self.label_encoder.classes_, counts))
        
        print(f"找到 {self.num_classes} 個唯一關鍵詞類別")
        print(f"資料集大小: {self.dataset_size}")
        print(f"類別分佈: {class_distribution}")
        
        # 檢查類別不平衡
        max_count = max(counts)
        min_count = min(counts)
        imbalance_ratio = max_count / min_count
        
        if imbalance_ratio > 5:
            print(f"⚠️  警告：類別不平衡嚴重 (比例: {imbalance_ratio:.2f})")
            print("建議使用類別權重或資料增強技術")
        
        return questions, encoded_keywords
    
    def create_balanced_data_loaders(self, questions: List[str], keywords: np.ndarray, 
                                   tokenizer, batch_size: int = 16, test_size: float = 0.2) -> Tuple:
        """
        創建平衡的資料載入器，處理類別不平衡問題
        """
        # 分層分割確保訓練和驗證集類別分佈一致
        train_questions, val_questions, train_keywords, val_keywords = train_test_split(
            questions, keywords, test_size=test_size, random_state=42, 
            stratify=keywords
        )
        
        # 計算類別權重
        class_weights = compute_class_weight(
            'balanced', classes=np.unique(train_keywords), y=train_keywords
        )
        self.class_weights = torch.FloatTensor(class_weights).to(self.device)
        
        # 創建資料集
        train_dataset = KeywordDataset(train_questions, train_keywords, tokenizer)
        val_dataset = KeywordDataset(val_questions, val_keywords, tokenizer)
        
        # 創建平衡的取樣器
        train_weights = [class_weights[label] for label in train_keywords]
        sampler = WeightedRandomSampler(
            weights=train_weights,
            num_samples=len(train_weights),
            replacement=True
        )
        
        # 創建資料載入器
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, sampler=sampler
        )
        val_loader = DataLoader(
            val_dataset, batch_size=batch_size, shuffle=False
        )
        
        return train_loader, val_loader
    
    def train_single_model_improved(self, model, train_loader, val_loader, 
                                  epochs: int = 5, learning_rate: float = 2e-5,
                                  patience: int = 3) -> Dict:
        """
        改進的單一模型訓練，包含早停、學習率調度等
        """
        model.to(self.device)
        
        # 使用改進的優化器和調度器
        optimizer, scheduler = ImprovedTrainingStrategy.get_optimizer_and_scheduler(
            model, train_loader, epochs, learning_rate
        )
        
        # 使用加權損失函數處理類別不平衡
        criterion = nn.CrossEntropyLoss(weight=self.class_weights)
        
        best_accuracy = 0
        best_model_state = None
        val_accuracies = []
        training_history = {
            'train_loss': [], 'val_loss': [], 'val_accuracy': [],
            'learning_rates': []
        }
        
        for epoch in range(epochs):
            # 訓練階段
            model.train()
            total_train_loss = 0
            train_correct = 0
            train_total = 0
            
            for batch in train_loader:
                optimizer.zero_grad()
                
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                loss = criterion(outputs, labels)
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                
                total_train_loss += loss.item()
                
                # 計算訓練準確率
                _, predicted = torch.max(outputs.data, 1)
                train_total += labels.size(0)
                train_correct += (predicted == labels).sum().item()
            
            # 驗證階段
            model.eval()
            total_val_loss = 0
            predictions = []
            true_labels = []
            
            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch['input_ids'].to(self.device)
                    attention_mask = batch['attention_mask'].to(self.device)
                    labels = batch['labels'].to(self.device)
                    
                    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                    loss = criterion(outputs, labels)
                    
                    total_val_loss += loss.item()
                    
                    preds = torch.argmax(outputs, dim=1)
                    predictions.extend(preds.cpu().numpy())
                    true_labels.extend(labels.cpu().numpy())
            
            # 計算指標
            train_accuracy = train_correct / train_total
            val_accuracy = accuracy_score(true_labels, predictions)
            avg_train_loss = total_train_loss / len(train_loader)
            avg_val_loss = total_val_loss / len(val_loader)
            current_lr = scheduler.get_last_lr()[0]
            
            # 記錄歷史
            training_history['train_loss'].append(avg_train_loss)
            training_history['val_loss'].append(avg_val_loss)
            training_history['val_accuracy'].append(val_accuracy)
            training_history['learning_rates'].append(current_lr)
            val_accuracies.append(val_accuracy)
            
            print(f'Epoch {epoch+1}/{epochs}:')
            print(f'  訓練損失: {avg_train_loss:.4f}, 訓練準確率: {train_accuracy:.4f}')
            print(f'  驗證損失: {avg_val_loss:.4f}, 驗證準確率: {val_accuracy:.4f}')
            print(f'  學習率: {current_lr:.2e}')
            
            # 保存最佳模型
            if val_accuracy > best_accuracy:
                best_accuracy = val_accuracy
                best_model_state = model.state_dict().copy()
                print(f'  ✓ 新的最佳模型 (準確率: {best_accuracy:.4f})')
            
            # 早停檢查
            if ImprovedTrainingStrategy.early_stopping_check(val_accuracies, patience):
                print(f'  早停於 epoch {epoch+1}')
                break
        
        # 載入最佳模型
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        training_history['best_accuracy'] = best_accuracy
        return training_history
    
    def initialize_model(self, config: Dict) -> nn.Module:
        """
        根據配置初始化模型
        """
        model_type = config.get('type', 'basic')
        
        if model_type == 'improved_simple':
            model = ImprovedEnhancedBertClassifier(
                config['model_name'], 
                self.num_classes,
                config.get('dropout_rate', 0.2),
                classifier_type='simple'
            )
        elif model_type == 'improved_moderate':
            model = ImprovedEnhancedBertClassifier(
                config['model_name'], 
                self.num_classes,
                config.get('dropout_rate', 0.2),
                classifier_type='moderate'
            )
        elif model_type == 'improved_complex':
            model = ImprovedEnhancedBertClassifier(
                config['model_name'], 
                self.num_classes,
                config.get('dropout_rate', 0.3),
                classifier_type='complex'
            )
        elif model_type == 'adaptive':
            model = AdaptiveBertClassifier(
                config['model_name'], 
                self.num_classes,
                config.get('dataset_size', self.dataset_size),
                config.get('dropout_rate', 0.2)
            )
        else:  # 'basic' or 'enhanced'
            if model_type == 'enhanced':
                model = EnhancedBertClassifier(
                    config['model_name'], 
                    self.num_classes, 
                    config.get('dropout_rate', 0.3)
                )
            else:
                model = BertClassifier(
                    config['model_name'], 
                    self.num_classes, 
                    config.get('dropout_rate', 0.3)
                )
        
        return model
    
    def train_ensemble_improved(self, questions: List[str], keywords: List[str], 
                              epochs: int = 5, batch_size: int = 16, 
                              patience: int = 3) -> None:
        """
        改進的集成模型訓練
        """
        # 預處理資料
        processed_questions, encoded_keywords = self.preprocess_data(questions, keywords)
        
        # 根據資料集大小調整模型配置
        if not hasattr(self, 'model_configs') or not self.model_configs:
            self.model_configs = get_improved_model_configs(self.dataset_size)
            print(f"使用推薦的模型配置 (資料集大小: {self.dataset_size})")
        
        training_results = []
        
        # 為每個模型配置訓練
        for i, config in enumerate(self.model_configs):
            print(f"\n{'='*50}")
            print(f"訓練模型 {i+1}/{len(self.model_configs)}: {config['name']}")
            print(f"{'='*50}")
            
            # 初始化tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(config['model_name'])
            model = self.initialize_model(config)
            
            # 創建平衡的資料載入器
            train_loader, val_loader = self.create_balanced_data_loaders(
                processed_questions, encoded_keywords, tokenizer, batch_size
            )
            
            # 訓練模型
            history = self.train_single_model_improved(
                model, train_loader, val_loader, epochs, 
                config.get('learning_rate', 2e-5), patience
            )
            
            # 保存結果
            training_results.append({
                'model_name': config['name'],
                'best_accuracy': history['best_accuracy'],
                'history': history
            })
            
            # 保存模型和tokenizer
            self.models.append(model)
            self.tokenizers.append(tokenizer)
            
            print(f"模型 {config['name']} 最佳準確率: {history['best_accuracy']:.4f}")
        
        # 顯示所有模型的結果摘要
        print(f"\n{'='*60}")
        print("所有模型訓練結果摘要:")
        print(f"{'='*60}")
        for result in training_results:
            print(f"{result['model_name']:30} 最佳準確率: {result['best_accuracy']:.4f}")
        
        # 排序並推薦最佳模型
        training_results.sort(key=lambda x: x['best_accuracy'], reverse=True)
        best_model = training_results[0]
        print(f"\n🏆 最佳模型: {best_model['model_name']} (準確率: {best_model['best_accuracy']:.4f})")
    
    def predict_single(self, question: str, model_idx: int) -> Tuple[int, float]:
        """使用單一模型進行預測"""
        model = self.models[model_idx]
        tokenizer = self.tokenizers[model_idx]
        
        model.eval()
        
        # 編碼輸入
        encoding = tokenizer(
            question,
            truncation=True,
            padding='max_length',
            max_length=512,
            return_tensors='pt'
        )
        
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            probabilities = F.softmax(outputs, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1).item()
            confidence = torch.max(probabilities, dim=1)[0].item()
        
        return predicted_class, confidence
    
    def predict_ensemble(self, question: str, method: str = 'weighted_voting') -> Dict:
        """
        使用集成方法進行預測
        支援投票法和平均法
        """
        predictions = []
        confidences = []
        
        # 獲取所有模型的預測
        for i in range(len(self.models)):
            pred_class, confidence = self.predict_single(question, i)
            predictions.append(pred_class)
            confidences.append(confidence)
        
        if method == 'voting':
            # 多數投票
            final_prediction = max(set(predictions), key=predictions.count)
        elif method == 'weighted_voting':
            # 加權投票（根據信心度）
            weighted_votes = {}
            for pred, conf in zip(predictions, confidences):
                if pred not in weighted_votes:
                    weighted_votes[pred] = 0
                weighted_votes[pred] += conf
            final_prediction = max(weighted_votes, key=weighted_votes.get)
        else:
            # 預設使用投票法
            final_prediction = max(set(predictions), key=predictions.count)
        
        # 解碼標籤
        predicted_keyword = self.label_encoder.inverse_transform([final_prediction])[0]
        avg_confidence = np.mean(confidences)
        
        return {
            'predicted_keyword': predicted_keyword,
            'confidence': avg_confidence,
            'individual_predictions': [
                {
                    'model_idx': i,
                    'model_name': self.model_configs[i]['name'] if i < len(self.model_configs) else f'Model_{i}',
                    'prediction': self.label_encoder.inverse_transform([pred])[0],
                    'confidence': conf
                }
                for i, (pred, conf) in enumerate(zip(predictions, confidences))
            ]
        }
    
    def evaluate_ensemble(self, test_questions: List[str], test_keywords: List[str]) -> Dict:
        """
        評估集成模型性能
        """
        predictions = []
        true_labels = []
        
        for question, true_keyword in zip(test_questions, test_keywords):
            result = self.predict_ensemble(question)
            predictions.append(result['predicted_keyword'])
            true_labels.append(true_keyword)
        
        accuracy = accuracy_score(true_labels, predictions)
        report = classification_report(true_labels, predictions, output_dict=True)
        
        return {
            'accuracy': accuracy,
            'classification_report': report,
            'predictions': predictions,
            'true_labels': true_labels
        }
    
    def save_models(self, save_dir: str):
        """
        保存所有訓練好的模型與 tokenizer 及 label_encoder
        """
        os.makedirs(save_dir, exist_ok=True)

        # 保存每個模型和 tokenizer
        for idx, (model, tokenizer) in enumerate(zip(self.models, self.tokenizers)):
            # 保存 model state_dict
            torch.save(model.state_dict(), f"{save_dir}/model_{idx}.pt")
            # 保存 tokenizer
            tokenizer.save_pretrained(f"{save_dir}/tokenizer_{idx}")

        # 保存 LabelEncoder
        with open(f"{save_dir}/label_encoder.pkl", "wb") as f:
            pickle.dump(self.label_encoder, f)

        # 保存 model config
        with open(f"{save_dir}/model_configs.json", "w", encoding="utf-8") as f:
            json.dump(self.model_configs, f, ensure_ascii=False, indent=2)
        
        print(f"所有模型已保存至 {save_dir}")


# 主要執行函數
def main():
    """
    主要執行函數 - 改進版
    """
    print("🚀 啟動改進版關鍵詞預測系統")
    print("="*60)
    
    # 初始化預測器 (先不指定配置，讓系統自動推薦)
    predictor = ImprovedEnsembleKeywordPredictor([])
    
    # 載入資料
    print("📁 載入資料...")
    questions, keywords = predictor.load_data('final_dataset.json')
    
    # 根據資料集大小自動獲取最適合的配置
    print("🔧 根據資料集大小選擇最佳模型配置...")
    model_configs = get_improved_model_configs(len(questions))
    predictor.model_configs = model_configs
    
    print(f"選擇的模型配置:")
    for i, config in enumerate(model_configs):
        print(f"  {i+1}. {config['name']} (學習率: {config['learning_rate']}, Dropout: {config['dropout_rate']})")
    
    # 改進的集成訓練
    print("\n🏋️‍♀️ 開始改進版集成訓練...")
    predictor.train_ensemble_improved(
        questions, keywords, 
        epochs=5,           # 可適當調整
        batch_size=8,       # 小batch size更穩定
        patience=3          # 早停機制
    )
    
    # 保存模型
    print("\n💾 保存訓練好的模型...")
    predictor.save_models("improved_models")
    
    # 預測範例
    print("\n🔮 進行預測測試...")
    test_questions = [
        "社會大眾對於男性請育嬰假分擔育兒責任的觀感與接受度，近年來是否有變化趨勢？",
        "政府在推動性別平等政策方面有哪些具體措施？",
        "職場性別歧視的現況如何？"
    ]
    
    for i, test_question in enumerate(test_questions):
        print(f"\n--- 測試 {i+1} ---")
        result = predictor.predict_ensemble(test_question, method='weighted_voting')
        
        print(f"問題: {test_question}")
        print(f"預測關鍵詞: {result['predicted_keyword']}")
        print(f"整體信心度: {result['confidence']:.4f}")
        print("各模型預測:")
        for pred in result['individual_predictions']:
            print(f"  {pred['model_name']}: {pred['prediction']} (信心度: {pred['confidence']:.4f})")
    
    print(f"\n🎉 改進版關鍵詞預測系統訓練完成！")
    print("模型已保存在 'improved_models' 資料夾中")


# 輔助函數：自定義配置訓練
def main_with_custom_config():
    """
    使用自定義配置的主函數
    """
    # 自定義模型配置（針對準確率低的問題特別優化）
    custom_configs = [
        {
            'name': 'BERT-Chinese-Conservative',
            'model_name': 'bert-base-chinese',
            'type': 'improved_simple',
            'learning_rate': 5e-5,      # 較高學習率
            'dropout_rate': 0.1,        # 較低dropout
            'classifier_type': 'simple' # 簡單結構
        },
        {
            'name': 'BERT-Chinese-Balanced',
            'model_name': 'bert-base-chinese',
            'type': 'improved_moderate',
            'learning_rate': 3e-5,
            'dropout_rate': 0.2,
            'classifier_type': 'moderate'
        },
        {
            'name': 'RoBERTa-Chinese-Optimized',
            'model_name': 'hfl/chinese-roberta-wwm-ext',
            'type': 'improved_moderate',
            'learning_rate': 2e-5,
            'dropout_rate': 0.15,
            'classifier_type': 'moderate'
        }
    ]
    
    # 使用自定義配置初始化
    predictor = ImprovedEnsembleKeywordPredictor(custom_configs)
    
    # 載入資料並訓練
    questions, keywords = predictor.load_data('final_dataset.json')
    predictor.train_ensemble_improved(
        questions, keywords,
        epochs=6,           # 稍微增加訓練輪數
        batch_size=8,
        patience=4          # 更耐心的早停
    )
    
    # 保存和測試
    predictor.save_models("custom_improved_models")
    
    # 測試預測
    test_question = "社會大眾對於男性請育嬰假分擔育兒責任的觀感與接受度，近年來是否有變化趨勢？"
    result = predictor.predict_ensemble(test_question, method='weighted_voting')
    print(f"自定義配置預測結果: {result['predicted_keyword']} (信心度: {result['confidence']:.4f})")


if __name__ == "__main__":
    # 執行主要訓練流程
    main()
    
    # 如果想要使用自定義配置，請取消下面的註解
    # print("\n" + "="*60)
    # print("執行自定義配置訓練...")
    # main_with_custom_config()