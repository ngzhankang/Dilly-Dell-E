def load_model(model_path: str):
    # Replace with your actual model loading logic.
    # ONNX example:    import onnxruntime as ort; return ort.InferenceSession(model_path)
    # PyTorch example: import torch; return torch.load(model_path, weights_only=True)
    return None


def run_inference(model, request):
    # Replace with your actual inference logic.
    # ONNX example: return model.run(None, {"input": [request.input]})[0]
    raise NotImplementedError("Replace with your model inference logic")
