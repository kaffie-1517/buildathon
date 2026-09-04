"""
DisputeForge — Model Training Script

Run this to train the XGBoost dispute prediction models on the synthetic dataset.

Usage:
    python model/train.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.predictor import train_model


def main():
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "transactions.csv"
    )

    if not os.path.exists(data_path):
        print("❌ Dataset not found. Generate it first:")
        print("   python3 data/generate_dataset.py")
        sys.exit(1)

    print("🛡️  DisputeForge — Model Training")
    print("=" * 50)

    metrics = train_model(data_path)

    print("\n" + "=" * 50)
    print("✅ Training complete!")
    print(f"   Binary model: precision={metrics['binary_classifier']['precision']}, "
          f"recall={metrics['binary_classifier']['recall']}, "
          f"F1={metrics['binary_classifier']['f1_score']}")

    if metrics.get("reason_classifier"):
        print(f"   Reason model: accuracy={metrics['reason_classifier']['accuracy']}")

    print(f"\n   Models saved to: model/")
    print(f"   Metrics saved to: model/metrics.json")


if __name__ == "__main__":
    main()
