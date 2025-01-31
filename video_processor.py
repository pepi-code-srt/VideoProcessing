import cv2
import base64
import numpy as np
from io import BytesIO
from PIL import Image
from ultralytics import YOLO
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from tracker import Tracker
import time
import threading

# Load YOLOv8 model
model = YOLO('yolov8x.pt')

# Class names from COCO dataset
COCO_INSTANCE_CATEGORY_NAMES = model.names

# Thread control flag
process_cancelled = threading.Event()

def numpy_to_base64(image):
    pil_image = Image.fromarray(image)
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return base64_str

def get_confidence_threshold(current_time, user_threshold=0.5):
    return user_threshold

def draw_boxes_and_labels(frame, results, tracker, confidence_threshold):
    for obj in results.boxes:
        cls = int(obj.cls[0])
        label = COCO_INSTANCE_CATEGORY_NAMES[cls]
        confidence = obj.conf[0]
        if confidence > confidence_threshold:
            x1, y1, x2, y2 = map(int, obj.xyxy[0])
            object_id = tracker.update((x1, y1, x2, y2), label)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            text = f"{label} {object_id}"
            cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    return frame

def process_frame(frame, frame_number, fps, tracker, confidence_threshold):
    results = model(frame)[0]
    frame_data = {
        "object_counts": defaultdict(int),
        "segmented_images": defaultdict(list),
        "unique_labels": [],
    }

    annotated_frame = draw_boxes_and_labels(frame.copy(), results, tracker, confidence_threshold)
    frame_data["frame"] = numpy_to_base64(annotated_frame)

    for obj in results.boxes:
        cls = int(obj.cls[0])
        label = COCO_INSTANCE_CATEGORY_NAMES[cls]
        confidence = obj.conf[0]
        if confidence > confidence_threshold:
            x1, y1, x2, y2 = map(int, obj.xyxy[0])
            object_id = tracker.update((x1, y1, x2, y2), label)
            if object_id not in frame_data["unique_labels"]:
                frame_data["unique_labels"].append(object_id)
                frame_data["object_counts"][label] += 1

                mask = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2RGB)
                frame_data["segmented_images"][label].append(numpy_to_base64(mask))

    return frame_data

def process_video(filepath, socketio, confidence_threshold):
    global process_cancelled
    process_cancelled.clear()

    cap = cv2.VideoCapture(filepath)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    if duration >= 40 and duration <= 60:
        step = fps * 4
    elif duration >= 30 and duration <= 39:
        step = fps * 3
    else:
        step = fps * 2

    object_counts = defaultdict(int)
    segmented_images = defaultdict(list)
    original_object_counts = defaultdict(int)

    tracker = Tracker()

    frame_number = 0
    start_time = time.time()

    with ThreadPoolExecutor() as executor:
        futures = []
        while frame_number < total_frames:
            if process_cancelled.is_set():
                cap.release()
                return {"error": "Video processing cancelled"}

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                break
            futures.append(executor.submit(process_frame, frame, frame_number, fps, tracker, confidence_threshold))
            frame_number += step

            frame_data = futures[-1].result()
            socketio.emit('frame', frame_data)

            elapsed_time = time.time() - start_time
            processed_frames = len(futures)
            remaining_frames = total_frames - frame_number
            estimated_time_remaining = ((elapsed_time / processed_frames) * remaining_frames) / 100
            socketio.emit('estimated_time', {'time_remaining': estimated_time_remaining})

        for future in as_completed(futures):
            frame_data = future.result()
            for label, count in frame_data["object_counts"].items():
                object_counts[label] += count
                original_object_counts[label] += 1

            for label, images in frame_data["segmented_images"].items():
                segmented_images[label].extend(images)

    cap.release()

    sorted_objects = sorted(original_object_counts.items(), key=lambda item: item[1], reverse=True)
    top_3_objects = sorted_objects[:3]

    return {
        'object_counts': dict(top_3_objects),
        'segmented_images': {label: images[0] for label, images in segmented_images.items() if label in dict(top_3_objects)},
        'total_frames': total_frames,
        'fps': fps,
        'duration': duration
    }