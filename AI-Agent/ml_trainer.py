
import os
import pickle
import random
from datetime import datetime

import numpy as np
import pandas as pd

from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


# ============================================================
# ML TRAINER CLASS
# ============================================================

class VeriFinMLTrainer:
    """
    ML training and prediction system for VeriFin invoice
    anomaly detection.
    """

    # --------------------------------------------------------
    # MODEL CONFIGURATION
    # --------------------------------------------------------

    FEATURE_COUNT = 15

    FEATURE_SCHEMA = [
        "amount",
        "amount_mod_1000",
        "amount_digit_count",
        "day_of_week",
        "day_of_month",
        "month",
        "ocr_confidence",
        "raw_text_length",
        "gst_number_count",
        "vendor_present",
        "invoice_number_present",
        "invoice_date_present",
        "total_amount_present",
        "reserved_feature_1",
        "reserved_feature_2"
    ]

    # --------------------------------------------------------
    # INITIALIZATION
    # --------------------------------------------------------

    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.is_trained = False

    # ========================================================
    # TYPE CONVERSION / SERIALIZATION SAFETY
    # ========================================================

    @staticmethod
    def _to_python_type(value):
        """
        Recursively convert NumPy/Pandas types into native
        Python types.

        This prevents errors such as:

            bson.errors.InvalidDocument:
            cannot encode object ... numpy.bool_

        Supported conversions:
            numpy.bool_  -> bool
            numpy.integer -> int
            numpy.floating -> float
            numpy.ndarray -> list
            numpy.str_ -> str
            numpy scalar -> Python scalar
            dict -> recursively converted dict
            list/tuple -> recursively converted list
        """

        # ----------------------------------------------------
        # None
        # ----------------------------------------------------

        if value is None:
            return None

        # ----------------------------------------------------
        # NumPy boolean
        # ----------------------------------------------------

        if isinstance(value, np.bool_):
            return bool(value)

        # ----------------------------------------------------
        # NumPy integer
        # ----------------------------------------------------

        if isinstance(value, np.integer):
            return int(value)

        # ----------------------------------------------------
        # NumPy floating point
        # ----------------------------------------------------

        if isinstance(value, np.floating):
            return float(value)

        # ----------------------------------------------------
        # NumPy string
        # ----------------------------------------------------

        if isinstance(value, np.str_):
            return str(value)

        # ----------------------------------------------------
        # NumPy array
        # ----------------------------------------------------

        if isinstance(value, np.ndarray):
            return [
                VeriFinMLTrainer._to_python_type(item)
                for item in value.tolist()
            ]

        # ----------------------------------------------------
        # Dictionary
        # ----------------------------------------------------

        if isinstance(value, dict):
            return {
                str(key): VeriFinMLTrainer._to_python_type(val)
                for key, val in value.items()
            }

        # ----------------------------------------------------
        # List
        # ----------------------------------------------------

        if isinstance(value, list):
            return [
                VeriFinMLTrainer._to_python_type(item)
                for item in value
            ]

        # ----------------------------------------------------
        # Tuple
        # ----------------------------------------------------

        if isinstance(value, tuple):
            return [
                VeriFinMLTrainer._to_python_type(item)
                for item in value
            ]

        # ----------------------------------------------------
        # Normal Python value
        # ----------------------------------------------------

        return value

    # ========================================================
    # SYNTHETIC DATA GENERATION
    # ========================================================

    def generate_training_data(self, num_samples=2000):
        """
        Generate synthetic invoice data.

        In the future, this can be replaced with real
        historical invoice data without changing the
        prediction pipeline.
        """

        print(
            f"🔄 Generating {num_samples} synthetic invoices "
            "for training..."
        )

        training_data = []
        labels = []

        for _ in range(num_samples):

            # ------------------------------------------------
            # 80% NORMAL / 20% ANOMALOUS
            # ------------------------------------------------

            if random.random() < 0.8:
                invoice = self._generate_normal_invoice()
                labels.append(0)
            else:
                invoice = self._generate_anomalous_invoice()
                labels.append(1)

            training_data.append(invoice)

        # Explicitly use float for ML training data
        training_data = np.array(
            training_data,
            dtype=float
        )

        labels = np.array(
            labels,
            dtype=int
        )

        return training_data, labels

    # ========================================================
    # NORMAL INVOICE GENERATION
    # ========================================================

    def _generate_normal_invoice(self):
        """
        Generate a normal invoice.

        Returns exactly 15 features.
        """

        # ----------------------------------------------------
        # Amount
        # ----------------------------------------------------

        amount = random.uniform(5000, 50000)
        amount += random.uniform(-500, 500)
        amount = max(amount, 1000)

        # ----------------------------------------------------
        # Amount features
        # ----------------------------------------------------

        amount_mod_1000 = amount % 1000
        amount_digit_count = len(str(int(amount)))

        # ----------------------------------------------------
        # Date features
        # ----------------------------------------------------

        # Normal invoices mostly occur Monday-Friday
        day_of_week = random.randint(0, 4)
        day_of_month = random.randint(1, 28)
        month = random.randint(1, 12)

        # ----------------------------------------------------
        # OCR / document features
        # ----------------------------------------------------

        ocr_confidence = random.uniform(88, 99)
        raw_text_length = random.randint(500, 1800)

        # ----------------------------------------------------
        # Complete invoice information
        # ----------------------------------------------------

        gst_number_count = 1
        vendor_present = 1
        invoice_number_present = 1
        invoice_date_present = 1
        total_amount_present = 1

        # ----------------------------------------------------
        # Reserved features
        # ----------------------------------------------------

        reserved_feature_1 = 0
        reserved_feature_2 = 0

        # ----------------------------------------------------
        # Return 15 features
        # ----------------------------------------------------

        return [
            amount,
            amount_mod_1000,
            amount_digit_count,
            day_of_week,
            day_of_month,
            month,
            ocr_confidence,
            raw_text_length,
            gst_number_count,
            vendor_present,
            invoice_number_present,
            invoice_date_present,
            total_amount_present,
            reserved_feature_1,
            reserved_feature_2
        ]

    # ========================================================
    # ANOMALOUS INVOICE GENERATION
    # ========================================================

    def _generate_anomalous_invoice(self):
        """
        Generate different types of suspicious invoices.

        Returns exactly 15 features.
        """

        anomaly_type = random.choice([
            "very_high_amount",
            "very_low_ocr",
            "missing_information",
            "unusual_text",
            "weekend_invoice",
            "round_amount"
        ])

        # ----------------------------------------------------
        # Default values
        # ----------------------------------------------------

        amount = random.uniform(10000, 40000)

        day_of_week = random.randint(0, 4)
        day_of_month = random.randint(1, 28)
        month = random.randint(1, 12)

        ocr_confidence = random.uniform(88, 99)
        raw_text_length = random.randint(500, 1800)

        gst_number_count = 1
        vendor_present = 1
        invoice_number_present = 1
        invoice_date_present = 1
        total_amount_present = 1

        # ----------------------------------------------------
        # VERY HIGH INVOICE AMOUNT
        # ----------------------------------------------------

        if anomaly_type == "very_high_amount":

            amount = random.uniform(
                100000,
                500000
            )

        # ----------------------------------------------------
        # VERY POOR OCR
        # ----------------------------------------------------

        elif anomaly_type == "very_low_ocr":

            amount = random.uniform(
                5000,
                50000
            )

            ocr_confidence = random.uniform(
                30,
                65
            )

            raw_text_length = random.randint(
                50,
                250
            )

        # ----------------------------------------------------
        # MISSING INFORMATION
        # ----------------------------------------------------

        elif anomaly_type == "missing_information":

            amount = random.uniform(
                5000,
                50000
            )

            ocr_confidence = random.uniform(
                60,
                85
            )

            gst_number_count = random.choice([
                0,
                2,
                3
            ])

            vendor_present = random.choice([
                0,
                1
            ])

            invoice_number_present = random.choice([
                0,
                1
            ])

            invoice_date_present = random.choice([
                0,
                1
            ])

            total_amount_present = random.choice([
                0,
                1
            ])

        # ----------------------------------------------------
        # UNUSUAL DOCUMENT TEXT
        # ----------------------------------------------------

        elif anomaly_type == "unusual_text":

            amount = random.uniform(
                5000,
                50000
            )

            ocr_confidence = random.uniform(
                55,
                80
            )

            raw_text_length = random.choice([
                random.randint(20, 100),
                random.randint(5000, 10000)
            ])

        # ----------------------------------------------------
        # WEEKEND INVOICE
        # ----------------------------------------------------

        elif anomaly_type == "weekend_invoice":

            amount = random.uniform(
                10000,
                50000
            )

            day_of_week = random.choice([
                5,
                6
            ])

        # ----------------------------------------------------
        # SUSPICIOUS ROUND AMOUNT
        # ----------------------------------------------------

        elif anomaly_type == "round_amount":

            amount = random.choice([
                10000,
                15000,
                20000,
                25000,
                50000,
                75000,
                100000,
                250000
            ])

        # ----------------------------------------------------
        # Safety
        # ----------------------------------------------------

        amount = max(
            amount,
            100
        )

        # ----------------------------------------------------
        # Amount features
        # ----------------------------------------------------

        amount_mod_1000 = amount % 1000

        amount_digit_count = len(
            str(int(amount))
        )

        # ----------------------------------------------------
        # Reserved features
        # ----------------------------------------------------

        reserved_feature_1 = 0
        reserved_feature_2 = 0

        # ----------------------------------------------------
        # Return 15 features
        # ----------------------------------------------------

        return [
            amount,
            amount_mod_1000,
            amount_digit_count,
            day_of_week,
            day_of_month,
            month,
            ocr_confidence,
            raw_text_length,
            gst_number_count,
            vendor_present,
            invoice_number_present,
            invoice_date_present,
            total_amount_present,
            reserved_feature_1,
            reserved_feature_2
        ]

    # ========================================================
    # MODEL TRAINING
    # ========================================================

    def train_models(
        self,
        training_data,
        labels
    ):
        """
        Train Isolation Forest and DBSCAN.
        """

        print("🧠 Training ML models...")

        # ----------------------------------------------------
        # Safety check
        # ----------------------------------------------------

        if training_data.shape[1] != self.FEATURE_COUNT:

            raise ValueError(
                f"Expected {self.FEATURE_COUNT} features, "
                f"but received {training_data.shape[1]}"
            )

        # ----------------------------------------------------
        # Train/Test Split
        # ----------------------------------------------------

        X_train, X_test, y_train, y_test = (
            train_test_split(
                training_data,
                labels,
                test_size=0.20,
                random_state=42,
                stratify=labels
            )
        )

        # ----------------------------------------------------
        # Scale Features
        # ----------------------------------------------------

        print("  ⚖️ Scaling features...")

        X_train_scaled = self.scaler.fit_transform(
            X_train
        )

        X_test_scaled = self.scaler.transform(
            X_test
        )

        # ====================================================
        # ISOLATION FOREST
        # ====================================================

        print("  📊 Training Isolation Forest...")

        self.models["isolation_forest"] = (
            IsolationForest(
                contamination=0.20,
                random_state=42,
                n_estimators=200
            )
        )

        self.models["isolation_forest"].fit(
            X_train_scaled
        )

        # ====================================================
        # DBSCAN
        # ====================================================

        print("  🔍 Training DBSCAN...")

        self.models["dbscan"] = DBSCAN(
            eps=0.8,
            min_samples=5
        )

        self.models["dbscan"].fit(
            X_train_scaled
        )

        # ====================================================
        # EVALUATION
        # ====================================================

        self._evaluate_models(
            X_test_scaled,
            y_test
        )

        self.is_trained = True

        print(
            "✅ ML models trained successfully!"
        )

    # ========================================================
    # MODEL EVALUATION
    # ========================================================

    def _evaluate_models(
        self,
        X_test,
        y_test
    ):
        """
        Evaluate Isolation Forest against the synthetic
        labels.

        Isolation Forest is unsupervised, so these metrics
        are only a comparison against our synthetic ground
        truth.
        """

        print("\n📈 Model Evaluation:")

        # ----------------------------------------------------
        # Isolation Forest Prediction
        # ----------------------------------------------------
        #
        # Isolation Forest:
        #     -1 = anomaly
        #      1 = normal
        #
        # Convert to:
        #      1 = anomaly
        #      0 = normal
        # ----------------------------------------------------

        iso_pred = self.models[
            "isolation_forest"
        ].predict(
            X_test
        )

        iso_pred = np.where(
            iso_pred == -1,
            1,
            0
        )

        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------

        accuracy = accuracy_score(
            y_test,
            iso_pred
        )

        precision = precision_score(
            y_test,
            iso_pred,
            zero_division=0
        )

        recall = recall_score(
            y_test,
            iso_pred,
            zero_division=0
        )

        f1 = f1_score(
            y_test,
            iso_pred,
            zero_division=0
        )

        # ----------------------------------------------------
        # Counts
        # ----------------------------------------------------

        anomalies_detected = int(
            np.sum(iso_pred)
        )

        actual_anomalies = int(
            np.sum(y_test)
        )

        # ----------------------------------------------------
        # Print Results
        # ----------------------------------------------------

        print(
            f"  Isolation Forest Accuracy : "
            f"{accuracy:.2%}"
        )

        print(
            f"  Precision                 : "
            f"{precision:.2%}"
        )

        print(
            f"  Recall                    : "
            f"{recall:.2%}"
        )

        print(
            f"  F1 Score                  : "
            f"{f1:.2%}"
        )

        print(
            f"  Anomalies Detected        : "
            f"{anomalies_detected}/"
            f"{actual_anomalies}"
        )

    # ========================================================
    # ANOMALY PREDICTION
    # ========================================================

    def predict_anomaly(
        self,
        invoice_features
    ):
        """
        Predict whether an invoice is anomalous.

        invoice_features MUST contain exactly 15 values.
        """

        # ----------------------------------------------------
        # Check if model is trained
        # ----------------------------------------------------

        if not self.is_trained:

            return {
                "error": "Models not trained yet!"
            }

        # ----------------------------------------------------
        # Check feature count
        # ----------------------------------------------------

        if len(invoice_features) != self.FEATURE_COUNT:

            return {
                "error": (
                    f"Expected {self.FEATURE_COUNT} "
                    f"features, "
                    f"received "
                    f"{len(invoice_features)}"
                )
            }

        # ----------------------------------------------------
        # Convert input to normal numeric values
        # ----------------------------------------------------
        #
        # This ensures that NumPy/Pandas numeric values
        # cannot leak into the returned result.
        # ----------------------------------------------------

        invoice_features = [
            float(value)
            for value in invoice_features
        ]

        # ----------------------------------------------------
        # Apply SAME scaler used during training
        # ----------------------------------------------------

        features_scaled = self.scaler.transform(
            [invoice_features]
        )

        # ----------------------------------------------------
        # Isolation Forest Prediction
        # ----------------------------------------------------

        iso_pred = self.models[
            "isolation_forest"
        ].predict(
            features_scaled
        )[0]

        # ----------------------------------------------------
        # Anomaly Score
        # ----------------------------------------------------

        anomaly_score = self.models[
            "isolation_forest"
        ].decision_function(
            features_scaled
        )[0]

        # ----------------------------------------------------
        # Build Result
        # ----------------------------------------------------

        result = {
            # Explicit bool conversion prevents numpy.bool_
            "is_anomaly": bool(
                iso_pred == -1
            ),

            # Explicit float conversion prevents numpy.float_
            "anomaly_score": float(
                anomaly_score
            ),

            # Explicit float conversion
            "confidence": float(
                min(
                    abs(
                        float(anomaly_score)
                    ) * 100,
                    100
                )
            ),

            "method": (
                "trained_isolation_forest"
            ),

            # Explicit int conversion
            "feature_count": int(
                len(invoice_features)
            )
        }

        # ----------------------------------------------------
        # Final safety conversion
        # ----------------------------------------------------
        #
        # Recursively ensures every value is a native Python
        # type before the result is sent to the API/database.
        # ----------------------------------------------------

        return self._to_python_type(
            result
        )

    # ========================================================
    # SAVE MODELS
    # ========================================================

    def save_models(
        self,
        filepath="verifin_models.pkl"
    ):
        """
        Save trained models, scaler and feature schema.
        """

        model_data = {
            "models": self.models,

            "scaler": self.scaler,

            "is_trained": bool(
                self.is_trained
            ),

            "feature_count": int(
                self.FEATURE_COUNT
            ),

            "feature_schema": list(
                self.FEATURE_SCHEMA
            ),

            "trained_at": (
                datetime.now().isoformat()
            )
        }

        # ----------------------------------------------------
        # Save using pickle
        # ----------------------------------------------------

        with open(
            filepath,
            "wb"
        ) as f:

            pickle.dump(
                model_data,
                f
            )

        print(
            f"💾 Models saved to {filepath}"
        )

    # ========================================================
    # LOAD MODELS
    # ========================================================

    def load_models(
        self,
        filepath="verifin_models.pkl"
    ):
        """
        Load pre-trained models.
        """

        target_path = filepath

        # ----------------------------------------------------
        # Backward compatibility
        # ----------------------------------------------------

        if (
            not os.path.exists(target_path)
            and filepath == "verifin_models.pkl"
            and os.path.exists("fintel_models.pkl")
        ):

            target_path = "fintel_models.pkl"

        # ----------------------------------------------------
        # Load model
        # ----------------------------------------------------

        try:

            with open(
                target_path,
                "rb"
            ) as f:

                model_data = pickle.load(f)

            # ------------------------------------------------
            # Check feature count
            # ------------------------------------------------

            saved_feature_count = (
                model_data.get(
                    "feature_count",
                    None
                )
            )

            # ------------------------------------------------
            # Reject incompatible models
            # ------------------------------------------------

            if saved_feature_count is not None:

                if (
                    saved_feature_count
                    != self.FEATURE_COUNT
                ):

                    print(
                        f"❌ Model has "
                        f"{saved_feature_count} "
                        f"features, "
                        f"but current system expects "
                        f"{self.FEATURE_COUNT}."
                    )

                    return False

            # ------------------------------------------------
            # Restore model data
            # ------------------------------------------------

            self.models = model_data[
                "models"
            ]

            self.scaler = model_data[
                "scaler"
            ]

            self.is_trained = bool(
                model_data[
                    "is_trained"
                ]
            )

            # ------------------------------------------------
            # Success
            # ------------------------------------------------

            print(
                f"✅ Models loaded from "
                f"{target_path}"
            )

            print("Feature count: " f"{saved_feature_count if saved_feature_count is not None else 'legacy model'}")
            return True

        # ----------------------------------------------------
        # File not found
        # ----------------------------------------------------

        except FileNotFoundError:

            print(
                f"❌ Model file "
                f"{filepath} not found"
            )

            return False

        # ----------------------------------------------------
        # Other errors
        # ----------------------------------------------------

        except Exception as e:

            print(
                f"❌ Error loading models: "
                f"{e}"
            )

            return False


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

FintelMLTrainer = VeriFinMLTrainer


# ============================================================
# MAIN TRAINING PIPELINE
# ============================================================

def main():

    print(
        "🤖 VeriFin - Proper ML Training"
    )

    print(
        "=" * 45
    )

    # --------------------------------------------------------
    # Make synthetic training reproducible
    # --------------------------------------------------------

    random.seed(42)
    np.random.seed(42)

    # --------------------------------------------------------
    # Initialize trainer
    # --------------------------------------------------------

    trainer = VeriFinMLTrainer()

    # --------------------------------------------------------
    # Generate synthetic data
    # --------------------------------------------------------

    training_data, labels = (
        trainer.generate_training_data(
            2000
        )
    )

    # --------------------------------------------------------
    # Training Data Summary
    # --------------------------------------------------------

    print(
        "\n📊 Training Data Summary:"
    )

    print(
        f"  Total samples: "
        f"{len(training_data)}"
    )

    print(
        f"  Features per invoice: "
        f"{training_data.shape[1]}"
    )

    print(
        f"  Normal invoices: "
        f"{int(np.sum(labels == 0))}"
    )

    print(
        f"  Anomalous invoices: "
        f"{int(np.sum(labels == 1))}"
    )

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    if (
        training_data.shape[1]
        != VeriFinMLTrainer.FEATURE_COUNT
    ):

        raise RuntimeError(
            f"Training data contains "
            f"{training_data.shape[1]} "
            f"features instead of "
            f"{VeriFinMLTrainer.FEATURE_COUNT}."
        )

    # --------------------------------------------------------
    # Train models
    # --------------------------------------------------------

    trainer.train_models(
        training_data,
        labels
    )

    # ========================================================
    # TEST PREDICTIONS
    # ========================================================

    print(
        "\n🧪 Testing Prediction:"
    )

    # --------------------------------------------------------
    # Normal invoice
    # --------------------------------------------------------

    normal_invoice = [
        15000,
        0,
        5,
        2,
        15,
        10,
        97,
        1100,
        1,
        1,
        1,
        1,
        1,
        0,
        0
    ]

    result = trainer.predict_anomaly(
        normal_invoice
    )

    print(
        f"Normal invoice (₹15,000): "
        f"{result}"
    )

    # --------------------------------------------------------
    # Suspicious invoice
    # --------------------------------------------------------

    suspicious_invoice = [
        250000,
        0,
        6,
        6,
        29,
        10,
        45,
        80,
        0,
        0,
        1,
        0,
        1,
        0,
        0
    ]

    result = trainer.predict_anomaly(
        suspicious_invoice
    )

    print(
        f"Suspicious invoice (₹250,000): "
        f"{result}"
    )

    # ========================================================
    # SAVE TRAINED MODELS
    # ========================================================

    trainer.save_models()

    # --------------------------------------------------------
    # Completion
    # --------------------------------------------------------

    print(
        "\n🎉 Training Complete!"
    )

    print(
        "🔗 Trained model is ready for VeriFin."
    )

    print(
        "📦 Model: "
        "AI-Agent\\verifin_models.pkl"
    )

    print(
        "🧠 Features: 15"
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

