"""On-device TFLite classifier for the 7 HAM10000 classes."""
import numpy as np
from PIL import Image

from paths import resolve

MODEL_REL = "model/model_quant_fp16.tflite"
LABELS_REL = "labels.txt"


def _interpreter_class():
    try:
        from ai_edge_litert.interpreter import Interpreter
        return Interpreter
    except ImportError:
        pass
    try:
        from tflite_runtime.interpreter import Interpreter
        return Interpreter
    except ImportError:
        pass
    try:
        import tensorflow as tf
        return tf.lite.Interpreter
    except ImportError:
        raise RuntimeError(
            "No TFLite runtime found. Install 'ai-edge-litert' (or tensorflow)."
        )


def _softmax(x):
    x = x - np.max(x)
    e = np.exp(x)
    return e / e.sum()


class Classifier:
    def __init__(self):
        labels_path = resolve(LABELS_REL)
        self.labels = [l.strip() for l in labels_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        model_path = resolve(MODEL_REL)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {MODEL_REL}\nPlace your model_quant_fp16.tflite in the 'model' folder."
            )
        self.interp = _interpreter_class()(model_path=str(model_path))
        self.interp.allocate_tensors()
        self.inp = self.interp.get_input_details()[0]
        self.out = self.interp.get_output_details()[0]

    def predict(self, img: Image.Image) -> dict:
        _, h, w, _ = self.inp["shape"]
        img = img.convert("RGB").resize((int(w), int(h)), Image.BILINEAR)
        arr = np.asarray(img, dtype=np.float32)
        arr = arr / 127.5 - 1.0  # preprocessing: (pixel/127.5) - 1
        arr = np.expand_dims(arr, 0)

        dtype = self.inp["dtype"]
        if dtype != np.float32:  # quantized input support
            scale, zero = self.inp["quantization"]
            if scale:
                arr = arr / scale + zero
            info = np.iinfo(dtype)
            arr = np.clip(np.round(arr), info.min, info.max)
        self.interp.set_tensor(self.inp["index"], arr.astype(dtype))
        self.interp.invoke()

        out = self.interp.get_tensor(self.out["index"]).astype(np.float32).flatten()
        if self.out["dtype"] != np.float32:
            scale, zero = self.out["quantization"]
            if scale:
                out = (out - zero) * scale
        if out.min() < 0 or out.max() > 1.0001 or abs(out.sum() - 1.0) > 0.05:
            out = _softmax(out)
        return {label: float(p) for label, p in zip(self.labels, out)}
