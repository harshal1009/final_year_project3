import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model
from pathlib import Path
import io

# Path to your model
MODEL_PATH = Path(__file__).parent / "skin_model(1).h5"

# Global model variable
_model = None

# Class labels for your skin model (adjust based on your model's classes)
CLASS_LABELS = [
    "Melanoma",
    "Nevus",
    "Basal Cell Carcinoma",
    "Actinic Keratosis",
    "Benign Keratosis",
    "Dermatofibroma",
    "Vascular Lesion"
]

def get_model():
    """Load model once"""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
        print(f"[PREDICTOR] Loading model from {MODEL_PATH}...")
        _model = load_model(str(MODEL_PATH), compile=False)
        print(f"[PREDICTOR] ✅ Model loaded! Input shape: {_model.input_shape}")
    return _model

def predict_from_image(image_data):
    """
    Accept image bytes or file path and return prediction label.
    
    Args:
        image_data: Either bytes (from file upload) or str (file path)
    
    Returns:
        str: Predicted class label
    """
    try:
        model = get_model()
        
        # Get model's expected input size
        input_shape = model.input_shape
        height = input_shape[1]
        width = input_shape[2]
        
        print(f"[PREDICTOR] Input shape: {width}x{height}")
        
        # Load image from bytes or path
        if isinstance(image_data, bytes):
            print(f"[PREDICTOR] Loading image from bytes ({len(image_data)} bytes)")
            img = Image.open(io.BytesIO(image_data))
        else:
            print(f"[PREDICTOR] Loading image from path: {image_data}")
            img = Image.open(image_data)
        
        # Preprocess image
        img = img.convert("RGB")
        print(f"[PREDICTOR] Original image size: {img.size}")
        
        img = img.resize((width, height))
        print(f"[PREDICTOR] Resized to: {img.size}")
        
        # Convert to array and normalize
        img_array = np.array(img, dtype=np.float32) / 255.0
        print(f"[PREDICTOR] Array shape before expand: {img_array.shape}")
        
        img_array = np.expand_dims(img_array, axis=0)
        print(f"[PREDICTOR] Array shape after expand: {img_array.shape}")
        
        # Get prediction
        print(f"[PREDICTOR] Running model prediction...")
        output = model.predict(img_array, verbose=0)
        print(f"[PREDICTOR] Raw output shape: {output.shape}")
        print(f"[PREDICTOR] Raw output: {output}")
        
        # Get the predicted class
        predicted_class_idx = np.argmax(output[0])
        confidence = float(output[0][predicted_class_idx])
        
        print(f"[PREDICTOR] Predicted class index: {predicted_class_idx}")
        print(f"[PREDICTOR] Confidence: {confidence:.4f}")
        
        # Get class label (handle if model has more/fewer classes than expected)
        if predicted_class_idx < len(CLASS_LABELS):
            predicted_label = CLASS_LABELS[predicted_class_idx]
        else:
            predicted_label = f"Class_{predicted_class_idx}"
        
        print(f"[PREDICTOR] Predicted label: {predicted_label}")
        
        result = f"{predicted_label} (confidence: {confidence:.2%})"
        print(f"[PREDICTOR] Final result: {result}")
        
        return result
        
    except FileNotFoundError as e:
        print(f"[PREDICTOR] ❌ File error: {e}")
        raise Exception(f"Model file not found: {str(e)}")
    except Exception as e:
        print(f"[PREDICTOR] ❌ Prediction error: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Prediction failed: {str(e)}")