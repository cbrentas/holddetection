import time
from ultralytics import YOLO
from app.core.settings import settings


def run_inference(model_weights_path: str, image_path: str):
    model = YOLO(model_weights_path)

    start = time.time()

    results = model.predict(
        source=image_path,
        imgsz=settings.YOLO_IMAGE_SIZE,
        conf=settings.YOLO_CONF,
        save=False,
        verbose=False
    )

    elapsed = time.time() - start

    result = results[0]

    boxes = []
    confidences = []

    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])

        boxes.append((x1, y1, x2, y2))
        confidences.append(conf)

    annotated_image = result.plot()

    return boxes, confidences, annotated_image, elapsed