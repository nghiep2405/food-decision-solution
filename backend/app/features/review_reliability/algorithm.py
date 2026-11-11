import re
import pandas as pd
from typing import Any
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import IsolationForest
from pyvi import ViTokenizer

# --- CÁC HÀM TIỀN XỬ LÝ (PREPROCESSING) ---

def preprocess_vietnamese_text(text: str) -> str:
    """
    Tiền xử lý văn bản tiếng Việt: Chuyển chữ thường, xóa ký tự đặc biệt và tách từ.
    Sử dụng thư viện Pyvi theo yêu cầu kỹ thuật của dự án.
    """
    if not text:
        return ""
    # Chuyển thành chữ thường
    text = text.lower()
    # Xóa các ký tự đặc biệt, dấu câu (chỉ giữ lại chữ và số)
    text = re.sub(r'[^\w\s]', '', text)
    # Tách từ tiếng Việt bằng Pyvi (VD: "nhà hàng" -> "nhà_hàng")
    text = ViTokenizer.tokenize(text)
    return text

def calculate_text_rating_conflict(text: str, rating: float) -> int:
    """
    Phát hiện xung đột cơ bản giữa văn bản và điểm số (Text-Rating Conflict).
    Trả về 1 nếu có xung đột đáng ngờ, 0 nếu bình thường.
    """
    if not text or rating is None:
        return 0
        
    text_lower = text.lower()
    negative_words = ["tệ", "dở", "ghê", "thất vọng", "kém", "bẩn", "đắt", "chê"]
    positive_words = ["ngon", "tuyệt", "tốt", "khen", "đỉnh", "xuất sắc", "rẻ"]
    
    has_negative = any(word in text_lower for word in negative_words)
    has_positive = any(word in text_lower for word in positive_words)
    
    # Đánh giá 5 sao nhưng toàn từ chê bai, hoặc 1 sao nhưng toàn khen ngợi
    if rating >= 4.0 and has_negative and not has_positive:
        return 1
    if rating <= 2.0 and has_positive and not has_negative:
        return 1
        
    return 0

# --- THUẬT TOÁN 1: TEXT SIMILARITY ---

def detect_text_similarity(reviews: list[Any], threshold: float = 0.85) -> list[dict[str, Any]]:
    """
    Phân tích sự tương đồng văn bản bằng TF-IDF và Cosine Similarity.
    Tìm ra các nhóm đánh giá có nội dung giống nhau bất thường (Spam/Duplicate).
    """
    signals = []
    # Cần ít nhất 2 bài đánh giá để so sánh
    if len(reviews) < 2:
        return signals

    # Lọc các bài review có nội dung text
    valid_reviews = [r for r in reviews if r.text and len(r.text.strip()) > 10]
    if len(valid_reviews) < 2:
        return signals

    texts = [preprocess_vietnamese_text(r.text) for r in valid_reviews]
    
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    except ValueError:
        return signals

    # Duyệt ma trận để tìm các cặp review giống nhau vượt ngưỡng threshold
    for i in range(len(cosine_sim)):
        for j in range(i + 1, len(cosine_sim)):
            score = float(cosine_sim[i][j])
            if score > threshold:
                signals.append({
                    "key": "text_similarity",
                    "score": round(score, 3),
                    "detail": f"Nội dung đánh giá ID '{valid_reviews[i].id}' và ID '{valid_reviews[j].id}' giống nhau bất thường (mức độ {score*100:.1f}%)."
                })
                
    return signals

# --- THUẬT TOÁN 2: METADATA ANOMALIES ---

def detect_metadata_anomalies(reviews: list[Any]) -> list[dict[str, Any]]:
    """
    Sử dụng Isolation Forest để quét điểm bất thường dựa trên các siêu dữ liệu (Metadata):
    Thời gian đăng, rating cực đoan, độ dài văn bản và xung đột text-rating.
    """
    signals = []
    # Isolation Forest cần một lượng mẫu nhất định để học đặc trưng
    if len(reviews) < 4:
        return signals

    # Sắp xếp review theo thời gian để tính toán khoảng thời gian (burst)
    sorted_reviews = sorted([r for r in reviews if r.created_at], key=lambda x: x.created_at)
    if len(sorted_reviews) < 4:
        return signals

    # Trích xuất đặc trưng (Feature Engineering)
    features = []
    for i, r in enumerate(sorted_reviews):
        # Đặc trưng 1: Độ dài văn bản
        text_length = len(r.text.strip()) if r.text else 0
        
        # Đặc trưng 2: Điểm số rating (mặc định 3 nếu không có)
        rating_val = r.rating if r.rating is not None else 3.0
        
        # Đặc trưng 3: Text-rating conflict
        conflict = calculate_text_rating_conflict(r.text, r.rating)
        
        # Đặc trưng 4: Khoảng cách thời gian so với bài trước (tính bằng phút)
        # Giúp phát hiện burst (nhiều review đăng dồn dập cùng lúc)
        time_diff_minutes = 0.0
        if i > 0:
            diff = sorted_reviews[i].created_at - sorted_reviews[i-1].created_at
            time_diff_minutes = diff.total_seconds() / 60.0

        features.append({
            "length": text_length,
            "rating": rating_val,
            "conflict": conflict,
            "time_diff": time_diff_minutes
        })

    # Chuyển đổi thành DataFrame để đưa vào mô hình học máy
    df = pd.DataFrame(features)
    
    # Cấu hình Isolation Forest (contamination = tỷ lệ nhiễu dự kiến)
    model = IsolationForest(contamination=0.15, random_state=42)
    # Kết quả trả về mảng gồm 1 (bình thường) và -1 (bất thường)
    predictions = model.fit_predict(df)

    # Phân tích kết quả và tạo tín hiệu
    for i, pred in enumerate(predictions):
        if pred == -1:
            r = sorted_reviews[i]
            feat = features[i]
            
            reasons = []
            if feat["conflict"] == 1:
                reasons.append(f"có mâu thuẫn giữa nội dung và điểm số ({feat['rating']} sao)")
            if feat["time_diff"] < 5 and i > 0:
                reasons.append("thời gian đăng quá sát với các đánh giá khác")
            if feat["rating"] in [1.0, 5.0]:
                reasons.append(f"điểm số cực đoan ({feat['rating']} sao)")
                
            reason_str = ", ".join(reasons) if reasons else "mang đặc trưng siêu dữ liệu khác biệt với số đông"
            
            signals.append({
                "key": "metadata_anomaly",
                "score": 1.0,
                "detail": f"Đánh giá ID '{r.id}' {reason_str}."
            })

    return signals