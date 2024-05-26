import torch
import traceback

class YOLOV5Wrap:

    def __init__(self, path='models/yolov5m_Objects365.pt'):
        self.model = load_yolov5_model('objects365', path)

    def predict(self, source, imgsz=640, conf=0.5, classes=[0, 1, 2], max_det=None, verbose=False):
        self.model.conf = conf
        self.model.classes = [key for key in self.model.names if key in classes]
        self.model.max_det = max_det
        try:
            results = self.model(source, size=imgsz)
            objects = process_model_output(results, conf, classes, max_det)
            return objects
        except Exception as e:
            print(traceback.format_exc())
            return None
            
def load_yolov5_model(model_name='objects365', path='models/yolov5m_Objects365.pt'):
    if model_name == 'yolov5s':
        model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
    elif model_name == 'objects365':
        model = torch.hub.load('ultralytics/yolov5', 'custom', path=path, verbose=False)
    else:
        raise ValueError("Invalid model name. Supported models: 'yolov5s', 'objects365'")
    return model

def process_model_output(results, confidence, classes, max_det=None):
    
    # Extract detected objects' results
    objects = results.pred[0]

    # Extract relevant information from the detection results
    objects_list = []
    for pred in objects:
        class_idx = int(pred[5])
        class_name = results.names[class_idx]
        if class_idx in classes and pred[4] >= confidence:
            object_info = {
                "class_id": class_idx,
                "class_name": class_name,
                "confidence": pred[4].item(),
                "bbox": [int(c) for c in pred[:4].cpu().numpy().tolist()]
            }
            objects_list.append(object_info)

    if max_det is not None:
        objects_list = objects_list[:max_det]

    return objects_list

